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
_LEGAL_HEADING = re.compile(r'(?:confidential(?:ity notice)?|legal disclaimer|اشعار السرية|تنبيه السرية)[:.! ]*$', re.I)
_LEGAL_DETAIL = re.compile(r'intended (?:only |solely )?(?:for|recipient)|disclos|distribut|delete|privileged|المستلم المقصود|افشاء|توزيع|احذف', re.I)
_FOOTER_START = re.compile(
    r'^(?:if you (?:would like to|no longer wish to) unsubscribe\b|click here to unsubscribe\b|'
    r'you are receiving (?:this|these|our) (?:email|emails|message|messages)\b|'
    r'(?:this email was (?:sent|intended)).*(?:because|subscribed|opted in)|'
    r'(?:copyright\s+\d{4}|©\s*\d{4})|all rights reserved[.! ]*$|'
    r'جميع الحقوق محفوظة[.! ]*$|لالغاء الاشتراك(?:\s|$)|'
    r'(?:unsubscribe|الغاء الاشتراك)(?:\s*[|:].*)?$)', re.I
)
_NAVIGATION = re.compile(
    r'(?:privacy policy|terms (?:and|&) conditions|unsubscribe|follow us|contact us|'
    r'if you are having trouble reading this email.*|'
    r'stay up to date with our latest offers on social media|'
    r'view (?:this email )?in (?:a |your )?browser|download our app|'
    r'facebook|instagram|youtube|telegram|linkedin|website|x|'
    r'سياسة الخصوصية|الشروط والاحكام|الغاء الاشتراك|تابعونا|تواصل معنا|حمل التطبيق|'
    r'women|men|girls|boys|baby|home|beauty|sports|kids)', re.I
)
_CONTACT = re.compile(r'(?:(?:https?://|www\.)\S+|[\w.+-]+@[\w.-]+\.[a-z]{2,}|\+?\d[\d ()-]{6,})', re.I)
_REQUEST = re.compile(r'\b(?:please|must|submit|send|pay|reply|attend|review)\b|(?:يرجى|يجب|ارسل|ادفع|راجع|مطلوب)', re.I)


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
    if _FOOTER_START.match(normalized):
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


def _trim_sections(text):
    lines = [line.strip() for line in text.splitlines()]
    kept = []
    for index, line in enumerate(lines):
        following = [item for item in lines[index + 1:] if item]
        if _footer_start(line, following):
            break
        if _SIGNATURE.fullmatch(_match_text(line)) and any(kept) and _signature_tail(following):
            break
        if _navigation(line):
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


def _clean_text(text, is_html=False):
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
    return _trim_sections(text)


def clean_email_text(text: str) -> str:
    """Clean message content for Gmail ingestion or stored-email maintenance."""
    return _clean_text(text)


def clean_email_body(body: str | None, *, is_html: bool | None = None) -> str:
    """Keep compatibility with existing callers."""
    return _clean_text(body, is_html=bool(is_html))


def extract_email_body(payload: dict) -> str:
    headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
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
                text = extract_email_body(part)
                if text:
                    return text
            return ""
        return clean_email_text("\n\n".join(filter(None, (extract_email_body(part) for part in parts))))

    data = payload.get("body", {}).get("data")
    if not data or mime_type not in {"text/plain", "text/html"}:
        return ""

    decoded = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))
    charset = content_type.get_content_charset() or "utf-8"
    try:
        text = decoded.decode(charset, errors="replace")
    except LookupError:
        text = decoded.decode("utf-8", errors="replace")
    return clean_email_text(_html_to_text(text) if mime_type == "text/html" else text)
