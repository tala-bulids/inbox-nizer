import base64
import html
import re
import unicodedata
from email.message import Message

from bs4 import BeautifulSoup


_HTML_TAG = re.compile(r'</?(?:html|body|head|div|p|br|a|img|span|table|tbody|tr|td|ul|li|script|style|section|footer|h[1-6])\b[^>]*>', re.I)
_SIGNATURE = re.compile(r'(?:best regards|kind regards|regards|sincerely|مع التحية|مع تحياتي|تحياتي)[,،.! ]*$', re.I)
_LEGAL = re.compile(
    r'^(?:if you are not the intended recipient\b|'
    r'this (?:email|e-mail|message)(?: communication)? (?:and .{0,80} )?is (?:strictly )?confidential\b|'
    r'هذه الرسالة سرية(?:\s|[.،])|اذا لم تكن المستلم المقصود(?:\s|[.،]))', re.I
)
_LEGAL_HEADING = re.compile(r'(?:confidential(?:ity notice)?|legal disclaimer|اشعار(?:ات)? السرية|تنبيه السرية|اخلاء المسؤولية)[:.! ]*$', re.I)
_LEGAL_DETAIL = re.compile(r'intended (?:only |solely )?(?:for|recipient)|disclos|distribut|delete|privileged|المستلم المقصود|افشاء|توزيع|احذف', re.I)
_FOOTER_START = re.compile(
    r'^(?:if you (?:would like to|no longer wish to) unsubscribe\b|click here to unsubscribe\b|'
    r'you are receiving (?:this|these|our) (?:email|emails|message|messages)\b|'
    r'(?:this email was (?:sent|intended)).*(?:because|subscribed|opted in)|'
    r'(?:copyright\s+\d{4}|©\s*\d{4})|all rights reserved[.! ]*$|'
    r'جميع الحقوق محفوظة[.! ]*$|لالغاء الاشتراك(?:\s|$)|'
    r'(?:unsubscribe|الغاء الاشتراك)(?:\s*[|:].*)?$)', re.I
)
_UNSUBSCRIBE_CTA = re.compile(r'^unsubscribe from .+(?:offers|emails|newsletters|mailing list)[.! ]*$', re.I)
_NAVIGATION = re.compile(
    r'(?:privacy policy|terms (?:and|&) conditions|unsubscribe|manage (?:your )?preferences|follow us|contact us|'
    r'if you are having trouble reading this email.*|'
    r'stay up to date with our latest offers on social media|'
    r'view (?:this email )?in (?:a |your )?browser|download our app|'
    r'facebook|instagram|youtube|telegram|linkedin|website|x|'
    r'سياسة الخصوصية|الشروط والاحكام|الغاء الاشتراك|ادارة التفضيلات|تابعونا|تواصل معنا|حمل التطبيق|'
    r'women|men|girls|boys|baby|home|beauty|sports|kids)', re.I
)
_CONTACT = re.compile(r'(?:(?:https?://|www\.)\S+|[\w.+-]+@[\w.-]+\.[a-z]{2,}|\+?\d[\d ()-]{6,})', re.I)
_REQUEST = re.compile(r'\b(?:please|must|submit|send|pay|reply|attend|review)\b|(?:يرجى|يجب|ارسل|ادفع|راجع|مطلوب)', re.I)
_NOTICE_OPENING = re.compile(
    r'^(?:this (?:e-?mail|message)(?: communication)?(?: and (?:any |its |all )?attachments)?\b|'
    r'(?:هذه )?الرسالة(?: ومرفقاتها)?\b|(?:هذه )?الرسالة الالكترونية\b)', re.I
)
_NOTICE_SIGNALS = [
    re.compile(pattern, re.I) for pattern in (
        r'confidential|privileged|معلومات سرية|الرسالة سرية',
        r'intended (?:only |solely )?(?:recipient|for)|المستلم المقصود',
        r'unauthori[sz]ed (?:use|disclosure|distribution)|disclosure.{0,35}prohibited|يحظر.{0,25}(?:افشاء|توزيع)',
        r'delete (?:this|the) (?:e-?mail|message)|احذف (?:هذه )?الرسالة',
        r'(?:accepts? no|not accept|disclaims? any|no) liability|without (?:any )?warrant(?:y|ies)|لا تتحمل.{0,30}مسؤولية',
    )
]
_USEFUL_CONTACT = re.compile(r'\b(?:support|direct|phone|mobile|email|contact)\b|(?:هاتف|للتواصل|الدعم)', re.I)
_LEGAL_REVIEW = re.compile(
    r'(?:review|revise|draft|discuss|update).{0,60}(?:notice|disclaimer|policy|terms)|'
    r'(?:مراجعة|تعديل|ناقش).{0,50}(?:اشعار السرية|اخلاء المسؤولية|سياسة الخصوصية|الشروط)', re.I
)
_POLICY_UPDATE = re.compile(r'\b(?:updated|revised|takes effect|effective from|clause \d)\b|(?:تم تحديث|تم تعديل|تسري|اعتبارا من)', re.I)


def _legal_strength(text):
    """Count distinct disclaimer signals, not repetitions of a single word."""
    normalized = _match_text(text)
    return sum(bool(pattern.search(normalized)) for pattern in _NOTICE_SIGNALS)


def _match_text(text):
    text = re.sub(r'[\u064b-\u065f\u0670\u0640]', '', text.casefold())
    return text.translate(str.maketrans('أإآ', 'ااا'))


def _mailto(text):
    text = re.sub(r'&lt;\s*mailto:.*?&gt;', lambda match: html.unescape(match.group()), text, flags=re.I)
    def replace(match):
        address = match.group(1).split('?', 1)[0]
        return '' if text[:match.start()].rstrip().endswith(address) else address
    text = re.sub(r'<\s*mailto:([^<>\s]+)\s*>', replace, text, flags=re.I)
    return re.sub(r'\bmailto:([^\s<>?]+)(?:\?[^\s<>]*)?', r'\1', text, flags=re.I)


def _html_to_text(text):
    text = _mailto(text)
    text = re.sub(r'<(https?://[^<>\s]+)>', r'\1', text, flags=re.I)
    soup = BeautifulSoup(text, 'html.parser')
    for tag in soup(['script', 'style', 'head', 'template', 'noscript']):
        tag.decompose()
    for tag in list(soup.find_all(True)):
        if tag.attrs is None:
            continue
        style = re.sub(r'\s+', '', tag.get('style', '')).lower()
        if tag.has_attr('hidden') or re.search(r'display:none|visibility:hidden|mso-hide:all', style):
            tag.decompose()
    for image in soup.find_all('img'):
        alt = image.get('alt', '').strip()
        image.replace_with(' ' + alt + ' ' if len(alt.split()) >= 2 and 'logo' not in alt.lower() else '')
    for link in soup.find_all('a'):
        target = link.get('href', '').strip()
        if re.match(r'^(?:https?://|mailto:)', target, re.I):
            target = _mailto(target)
            label = link.get_text(' ', strip=True)
            if target not in label:
                link.append(' (' + target + ')')
    for tag in soup.find_all(['p', 'div', 'br', 'li', 'tr', 'section', 'footer', 'h1', 'h2', 'h3']):
        tag.insert_before('\n')
        tag.insert_after('\n')
    for tag in soup.find_all(['td', 'th']):
        tag.insert_after(' ')
    return _HTML_TAG.sub(' ', soup.get_text())


def _navigation(line):
    # Match complete labels, including an optional link, not prose about privacy.
    labels = re.split(r'\s*[|•]\s*', _match_text(line).strip('" .'))
    return bool(labels) and all(_NAVIGATION.fullmatch(
        re.sub(r'\s*\((?:https?://[^\s]+|[\w.+-]+@[\w.-]+)\)\s*$', '', label)
    ) for label in labels)


def _corrupted(line):
    """Drop only dense encoding noise; ordinary Arabic and emoji are untouched."""
    compact = re.sub(r'\s', '', line)
    if not compact:
        return False
    replacements = compact.count('\ufffd')
    if replacements >= 3 and replacements / len(compact) >= 0.4:
        return True
    if compact.count('?') >= 8 and compact.count('?') / len(compact) >= 0.8:
        return True
    # UTF-8 Arabic decoded as Windows-1256 creates repeated ط/ظ pairs.
    markers = re.findall(r'[طظ][\u00a0-\u00bf\u0600-\u06ff\u2010-\u203a]', compact)
    unusual = re.search(r'[\u00a0-\u00bf\u2010-\u203a]', compact)
    return bool(unusual and len(markers) >= 3 and len(markers) * 2 / len(compact) >= 0.6)


def _footer_start(line, following):
    normalized = _match_text(line)
    if _FOOTER_START.match(normalized) or _UNSUBSCRIBE_CTA.fullmatch(normalized):
        return True
    nearby = ' '.join([line] + following[:3])
    if _NOTICE_OPENING.match(normalized) and _legal_strength(line) >= 1 and _legal_strength(nearby) >= 2:
        return True
    if _LEGAL_HEADING.fullmatch(normalized) and _legal_strength(' '.join(following[:3])) >= 2:
        return True
    if _LEGAL.match(normalized) and _LEGAL_DETAIL.search(_match_text(' '.join([line] + following[:2]))):
        return True
    return bool(_LEGAL_HEADING.fullmatch(normalized) and _LEGAL_DETAIL.search(_match_text(' '.join(following[:3]))) and any(
        _LEGAL.match(_match_text(item)) for item in following[:3]
    ))


def _navigation_tail(lines):
    for line in lines:
        if _footer_start(line, []):
            return True
        if not (_navigation(line) or _CONTACT.fullmatch(line)):
            return False
    return True


def _signature_tail(lines):
    for index, line in enumerate(lines):
        if _footer_start(line, lines[index + 1:]) or _navigation(line):
            return True
        if _CONTACT.fullmatch(line):
            continue
        if len(line) > 80 or len(line.split()) > 8 or _REQUEST.search(_match_text(line)) or line.endswith(('.', '?', '؟')):
            return False
    return len(lines) <= 8


def _useful_signature(lines):
    contacts = []
    footer = False
    for index, line in enumerate(lines):
        if _footer_start(line, lines[index + 1:]) or _navigation(line):
            footer = True
            break
        contacts.append(line)
    # Keep short personal contact blocks when there is no footer evidence.
    has_contact = any(_CONTACT.search(line) for line in contacts)
    return has_contact and (any(_USEFUL_CONTACT.search(_match_text(line)) for line in contacts)
                            or (not footer and len(contacts) <= 8))


def _legal_navigation_section(line, following, has_message):
    if not has_message or not re.fullmatch(r'terms (?:and|&) conditions|privacy policy|الشروط والاحكام|سياسة الخصوصية', _match_text(line), re.I):
        return False
    # A heading followed by dense legal text AND footer navigation is a footer.
    return (_legal_strength(' '.join(following[:4])) >= 2
            and not _POLICY_UPDATE.search(_match_text(' '.join(following[:4])))
            and any(_navigation(item) or _FOOTER_START.match(_match_text(item)) for item in following[1:]))


_LEGAL_TOPIC = re.compile(r'\b(?:privacy|terms|legal|confidential(?:ity)?)\b|(?:الخصوصية|الشروط|اشعار قانوني|السرية)', re.I)
_LEGAL_TITLE = re.compile(r'^(?:terms (?:and|&) conditions|privacy policy|الشروط والاحكام|سياسة الخصوصية)(?:\s*[:：]|$)', re.I)
_BLOCK_IMPORTANT = re.compile(r'\b(?:please|must|submit|pay|reply|upload|request|application|received|created|review|booking|flight|invoice|payment|deadline)\b|(?:يرجى|يجب|ارسل|ادفع|الطلب|طلبك|استلام|انشاء|مراجعة|الحجز|فاتورة|قبل|بحلول)', re.I)
_PREFERENCES = re.compile(r'^(?:unsubscribe|manage (?:your )?preferences|الغاء الاشتراك|ادارة التفضيلات)(?:\s*\([^)]*\))?[.! ]*$', re.I)
_POWERED = re.compile(r'^(?:powered by|مدعوم من|بدعم من)\s+.{1,70}$', re.I)


def _legal_purpose(text, subject=''):
    return bool(_LEGAL_TOPIC.search(_match_text(subject)) or
                _LEGAL_REVIEW.search(_match_text(text)) or
                _POLICY_UPDATE.search(_match_text(' '.join(text.splitlines()[:4]))))


_TAIL_LEGAL_SIGNALS = [re.compile(pattern, re.I) for pattern in (
    r'\bterms (?:and|&) conditions\b|\bterms of (?:service|use|sale)\b|الشروط والاحكام|شروط الاستخدام',
    r'\bcontract(?:ual|s)?\b|\blegally binding\b|عقد|التزام قانوني',
    r'\b(?:website|site).{0,50}(?:owned|operated)\b|الموقع.{0,40}(?:مملوك|تديره)',
    r'\bregistered (?:office|address|company)\b|المكتب المسجل|المقر المسجل',
    r'\b(?:governed by|jurisdiction|liability)\b|القانون المعمول|المسؤولية',
    r'\b(?:offers? subject to|subject to availability|discounts? cannot be combined|offers? depend on availability|availability varies)\b|العروض تخضع|حسب التوفر',
)]
_SUBSCRIPTION_TAIL = re.compile(
    r'^(?:(?:to |please |you (?:can|may) )?(?:unsubscribe|manage your (?:email )?preferences)\b'
    r'|(?:if you (?:no longer|would rather not|wish to stop)|to stop receiving)'
    r'(?=.{0,250}(?:unsubscribe|preferences)).{0,100}(?:receive|receiving|newsletter|emails)'
    r'|(?:this newsletter|you are receiving this newsletter).{0,250}(?:unsubscribe|preferences)'
    r'|(?:لالغاء الاشتراك|يمكنك الغاء الاشتراك)'
    r'|اذا كنت لا ترغب.{0,150}(?:الغاء الاشتراك|تفضيلات))', re.I)
_SUBSCRIPTION_REASON = re.compile(
    r'^you (?:have received|received|are receiving) (?:this|these|our) (?:e-?mails?|newsletters?)'
    r'\s+because you (?:subscribed|signed up|opted in)\b'
    r'|^(?:لقد )?تلقيت هذه الرسالة لانك (?:اشتركت|سجلت)', re.I)
_STOP_SUBSCRIPTION = re.compile(
    r'^(?:if you (?:want|wish|would like) to |to )?stop receiving '
    r'(?:them|(?:these |our |the )?(?:e-?mails?|newsletters?))\b'
    r'.{0,160}(?:click here|unsubscribe|manage.{0,20}preferences)'
    r'|^اذا كنت (?:تريد|ترغب في) (?:ايقاف|التوقف عن) (?:استلام|تلقي).{0,100}(?:اضغط هنا|الغاء الاشتراك)', re.I)


_CONTENT_URL = re.compile(r'(?:https?://|www\.)[^\s<>()\[\]]+', re.I)
_CONTENT_NAVIGATION = re.compile(r'(?:read more|learn more|view more|click here|اقرا المزيد|تعرف على المزيد|اضغط هنا)[.! ]*', re.I)
_NOTIFICATION_TOPIC = re.compile(r'\b(?:digests?|newsletters?|notifications?|emails?)\b|النشرة|الرسائل|الاشعارات', re.I)
_NOTIFICATION_STOP = re.compile(r"(?:don['’]t want|do not want|no longer want).{0,100}(?:turn.{0,15}off|disable|stop receiving)|لا ترغب.{0,80}(?:اوقف|ايقاف|الغاء)", re.I)


def _without_urls(text):
    """Readable text for selection/scoring; stored links stay unchanged."""
    text = _CONTENT_URL.sub('', text)
    return re.sub(r'\(\s*\)|\[\s*\]|<\s*>', '', text).strip()


def _subscription_notice(value):
    return bool(_SUBSCRIPTION_TAIL.search(value) or _SUBSCRIPTION_REASON.search(value)
                or (_NOTIFICATION_TOPIC.search(value) and _NOTIFICATION_STOP.search(value))
                or _PREFERENCES.fullmatch(value))


def _select_footer_tail(blocks, subject):
    """Extend only a supported terminal footer; stop at uncertain content."""
    active = [i for i, block in enumerate(blocks) if block['text']]
    values = [_match_text(_without_urls(blocks[i]['text'])) for i in active]
    evidence = [sum(bool(pattern.search(value)) for pattern in _TAIL_LEGAL_SIGNALS)
                for value in values]
    # Policy subjects or a legal introduction protect genuine legal messages.
    opening = ' '.join(values[:2])
    legal_message = bool(_LEGAL_TOPIC.search(_match_text(subject)) or
                         (_LEGAL_TOPIC.search(opening) and
                          (_LEGAL_REVIEW.search(opening) or _POLICY_UPDATE.search(opening))))
    anchored = False
    for position in range(len(active) - 1, -1, -1):
        block = blocks[active[position]]
        value = values[position]
        previous_footer = position > 0 and (
            _subscription_notice(values[position - 1]) or
            blocks[active[position - 1]]['role'] in {'legal/footer', 'unsubscribe/preferences'})
        # "Them" needs the adjacent subscription notice to explain its meaning.
        subscription_continuation = (position > 0 and _subscription_notice(values[position - 1])
                                     and _STOP_SUBSCRIPTION.search(value))
        if _subscription_notice(value) or subscription_continuation:
            block['role'] = 'unsubscribe/preferences'
            anchored = True
        elif block['role'] in {'navigation/social', 'signature/contact', 'decorative/header', 'legal/footer'}:
            anchored = True
        elif previous_footer and (re.match(r'^(?:office address|registered office|عنوان المكتب|المقر المسجل)\b', value)
                                  or (not legal_message and re.match(r'^privacy policy\b', value)
                                      and len(value.split()) <= 6)):
            block['role'] = 'legal/footer'
            anchored = True
        elif not legal_message and position > 0 and (
            (anchored and (evidence[position] >= 2 or
                           (evidence[position] >= 1 and len(value.split()) >= 12) or
                           _LEGAL_TITLE.fullmatch(value))) or
            (position >= len(active) // 2 and evidence[position] >= 3 and len(value.split()) >= 30
             and any(len(item.split()) <= 10 for item in values[:position]))
        ):
            block['role'] = 'legal/footer'
            anchored = True
        else:
            break
    return blocks


def _segment_blocks(text, subject='', *, main_content=False):
    """Line/paragraph roles are internal hints; only clear footer blocks are removed."""
    lines = [line.strip() for line in text.splitlines()]
    normalized = [_match_text(_without_urls(line) if main_content else line) for line in lines]
    counts = {line: normalized.count(line) for line in set(normalized) if line}
    substantive = any(_BLOCK_IMPORTANT.search(line) for line in normalized)
    legal_purpose = _legal_purpose(text, subject)
    blocks = []
    legal_tail = False
    signature = False
    nonempty = [i for i, line in enumerate(lines) if line]
    for index, line in enumerate(lines):
        value = normalized[index]
        following = [item for item in lines[index + 1:] if item]
        role, remove = 'main_content', False
        if not line:
            blocks.append({'text': line, 'role': role, 'remove': remove})
            continue
        # A legal heading plus a later subscription/navigation anchor marks a tail.
        if (not main_content and _LEGAL_TITLE.match(value) and index > 0 and any(lines[:index]) and not legal_purpose
                and any(_PREFERENCES.fullmatch(_match_text(item)) or _FOOTER_START.match(_match_text(item))
                        for item in following)):
            legal_tail = True
        if legal_tail or (_footer_start(line, following) and not legal_purpose):
            role, remove = 'legal/footer', True
        elif _PREFERENCES.fullmatch(value):
            role, remove = 'unsubscribe/preferences', True
        elif _navigation(line) and not (_LEGAL_TITLE.match(value) and legal_purpose):
            role = 'navigation/social'
        elif _SIGNATURE.fullmatch(value):
            role, signature = 'signature/contact', True
        elif (_CONTACT.fullmatch(line) or (signature and len(line.split()) <= 8)) and not _BLOCK_IMPORTANT.search(value):
            role = 'signature/contact'
        elif _POWERED.fullmatch(value) and substantive and not _BLOCK_IMPORTANT.search(value):
            role = 'decorative/header'
        elif (substantive and len(line.split()) <= 7 and len(line) <= 70 and not re.search(r'\d|[.!?؟]$', line)
              and not _BLOCK_IMPORTANT.search(value) and not _LEGAL_TOPIC.search(value)
              and not (main_content and counts.get(value, 0) == 1 and following and len(following[0].split()) <= 7
                       and not re.search(r'[.!?؟]$', following[0])
                       and not _BLOCK_IMPORTANT.search(_match_text(following[0])))
              and (counts.get(value, 0) > 1 or index == nonempty[0])):
            role = 'decorative/header'
        if main_content:
            previous = next((block for block in reversed(blocks) if block['text']), None)
            if not re.search(r'\w', value):
                # Keep a bare link when it belongs to a concrete instruction.
                linked_action = (previous and _REQUEST.search(_match_text(_without_urls(previous['text'])))
                                 and _CONTENT_URL.search(line))
                role = 'main_content' if linked_action else 'navigation/social'
            elif _CONTENT_NAVIGATION.fullmatch(value.strip(' ()[]')):
                role = 'navigation/social'
            elif _subscription_notice(value):
                role = 'unsubscribe/preferences'
            elif (previous and previous['role'] == 'unsubscribe/preferences'
                  and _CONTENT_URL.search(line) and len(value.split()) <= 12
                  and re.match(r'^(?:start|create|build) your own\b|^انشئ .{0,30}الخاص', value)):
                role = 'navigation/social'
        blocks.append({'text': line, 'role': role, 'remove': remove})
    return _select_footer_tail(blocks, subject) if main_content else blocks


def _trim_sections(text, subject=''):
    lines = [line.strip() for line in text.splitlines()]
    blocks = _segment_blocks(text, subject)
    legal_purpose = _legal_purpose(text, subject)
    kept = []
    for index, line in enumerate(lines):
        if blocks[index]['remove']:
            # A footer is a section, not a bag of individual legal words.
            if blocks[index]['role'] == 'legal/footer' or _FOOTER_START.match(_match_text(line)):
                break
            continue
        following = [item for item in lines[index + 1:] if item]
        discussing_legal = legal_purpose or _LEGAL_REVIEW.search(_match_text(' '.join(kept[-4:])))
        if ((_footer_start(line, following) or _legal_navigation_section(line, following, any(kept)))
                and not (discussing_legal and not _FOOTER_START.match(_match_text(line)))):
            break
        if (_SIGNATURE.fullmatch(_match_text(line)) and any(kept)
                and _signature_tail(following) and not _useful_signature(following)):
            break
        if _navigation(line):
            if legal_purpose and _LEGAL_TITLE.match(_match_text(line)):
                kept.append(line)
                continue
            # A trailing cluster of footer labels/contact lines is one section.
            if _navigation_tail(following):
                break
            if re.match(r'^(?:privacy policy|terms (?:and|&) conditions|سياسة الخصوصية|الشروط والاحكام)$', _match_text(line), re.I):
                kept.append(line)
            continue
        if _corrupted(line) or re.fullmatch(r'[-_=]{3,}', line):
            continue
        kept.append(line)
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(kept)).strip()


def _clean_text(text, is_html=False, subject='', *, trim_sections=True):
    if not text:
        return ''
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    if not _HTML_TAG.search(text) and _HTML_TAG.search(html.unescape(text)):
        text = html.unescape(text)
    text = _mailto(text)
    # Broken tracking placeholders are not readable links.
    text = re.sub(r'<(https?://[^<>\s]+)>', r'\1', text, flags=re.I)
    text = re.sub(r'<[^<>"\n]*(?:[?&](?:utm_\w+|elq\w*|eventSeriesCode)=)[^<>]*>', ' ', text, flags=re.I)
    if is_html or _HTML_TAG.search(text):
        text = _html_to_text(text)
    text = unicodedata.normalize('NFKC', html.unescape(text))
    text = _mailto(text)
    text = re.sub(r'[\u034f\u200b\ufeff\u00ad\u2060]', '', text)
    text = re.sub(r'(?<!\w)[\u200c]+|[\u200c]+(?!\w)', '', text)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    text = re.sub(r'[^\S\n]+', ' ', text)
    return _trim_sections(text, subject) if trim_sections else text.strip()


def extract_main_content(subject: str, text: str) -> str:
    """Select useful blocks for summaries/search, without changing stored body."""
    # Keep the full structure until selection; display cleaning can trim tails.
    cleaned = _clean_text(text, subject=subject, trim_sections=False)
    blocks = _segment_blocks(cleaned, subject, main_content=True)
    return '\n'.join(block['text'] for block in blocks
                     if block['role'] == 'main_content').strip()


def clean_email_text(text: str, *, subject: str = '') -> str:
    """Clean message content for Gmail ingestion or stored-email maintenance."""
    return _clean_text(text, subject=subject)


def clean_email_body(body: str | None, *, is_html: bool | None = None) -> str:
    """Keep compatibility with existing callers."""
    return _clean_text(body, is_html=bool(is_html))


def extract_email_body(payload: dict, *, subject: str = '') -> str:
    headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
    subject = headers.get('subject', subject)
    content_type = Message()
    content_type["Content-Type"] = headers.get("content-type", "text/plain")
    disposition = headers.get("content-disposition", "").lower()

    # Skip attachments.
    if payload.get("filename") or disposition.startswith("attachment"):
        return ""

    mime_type = payload.get("mimeType", "").lower()
    parts = payload.get("parts", [])
    if parts:
        # Prefer plain text over HTML.
        if mime_type == "multipart/alternative":
            parts = sorted(parts, key=lambda part: part.get("mimeType") != "text/plain")
            for part in parts:
                text = extract_email_body(part, subject=subject)
                if text:
                    return text
            return ""
        return clean_email_text("\n\n".join(filter(None, (extract_email_body(part, subject=subject) for part in parts))), subject=subject)

    data = payload.get("body", {}).get("data")
    if not data or mime_type not in {"text/plain", "text/html"}:
        return ""

    decoded = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))
    charset = content_type.get_content_charset() or "utf-8"
    try:
        text = decoded.decode(charset, errors="replace")
    except LookupError:
        text = decoded.decode("utf-8", errors="replace")
    return clean_email_text(_html_to_text(text) if mime_type == "text/html" else text, subject=subject)
