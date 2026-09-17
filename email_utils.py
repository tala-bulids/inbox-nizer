import base64
import html
import re
import unicodedata
from email.message import Message

from bs4 import BeautifulSoup


HTML_TAG = re.compile(r'</?(?:html|body|head|div|p|br|a|img|span|table|tbody|tr|td|ul|li|script|style|h[1-6])\b[^>]*>', re.I)
TRACKING = re.compile(r'<\s*(?:https?://|www\.)[^<>]*>|<[^<>"\n]*(?:[?&](?:utm_\w+|elq\w*|eventSeriesCode)=)[^<>]*>', re.I)
FOOTER = re.compile(
    r'^(?:(?:"[^"\n]{1,60}"\s*)?this email was (?:intended|sent)|you are receiving .+ emails|'
    r'if you (?:would like to|no longer wish to) unsubscribe|'
    r'if you would like to unsubscribe|click here to unsubscribe|unsubscribe\s*(?::|\|.*)?$|copyright\b|©)', re.I
)
BOILERPLATE = re.compile(
    r'^(?:download our app|view in browser|view (?:this email )?in (?:a |your )?browser|'
    r'if you are having trouble reading this email.*|'
    r'stay up to date with our latest offers on social media|'
    r'terms (?:&|and) conditions|privacy policy|'
    r'(?:women|men|girls|boys|baby|home|beauty|sports|kids)(?:\s*\|\s*(?:women|men|girls|boys|baby|home|beauty|sports|kids))*|'
    r'(?:facebook|instagram|youtube|telegram|website|x)(?:[\s"|]+(?:facebook|instagram|youtube|telegram|website|linkedin|x))*|'
    r'[-_=]{3,})$', re.I
)


def clean_email_body(body: str | None, *, is_html: bool | None = None) -> str:
    if not body:
        return ''
    text = body.replace('\r\n', '\n').replace('\r', '\n')
    if not HTML_TAG.search(text) and HTML_TAG.search(html.unescape(text)):
        text = html.unescape(text)
    # Remove complete tracking links first.
    text = TRACKING.sub(' ', text)
    # Some plain-text emails contain HTML too.
    if is_html or HTML_TAG.search(text):
        soup = BeautifulSoup(text, 'html.parser')
        for tag in soup(['script', 'style', 'head', 'template', 'noscript']):
            tag.decompose()
        for tag in list(soup.find_all(True)):
            if tag.attrs is None:
                continue
            style = re.sub(r'\s+', '', tag.get('style', '')).lower()
            if tag.has_attr('hidden') or re.search(r'(?:display:none|visibility:hidden|mso-hide:all)', style):
                tag.decompose()
        # Keep useful text from images.
        for image in soup.find_all('img'):
            alt = image.get('alt', '').strip()
            image.replace_with(' ' + alt + ' ' if len(alt.split()) >= 2 and 'logo' not in alt.lower() else '')
        for tag in soup.find_all(['p', 'div', 'br', 'li', 'tr', 'section', 'h1', 'h2', 'h3']):
            tag.insert_before('\n')
            tag.insert_after('\n')
        for tag in soup.find_all(['td', 'th']):
            tag.insert_after(' ')
        text = soup.get_text()
        # Remove broken tags left by malformed email HTML.
        text = HTML_TAG.sub(' ', text)

    text = unicodedata.normalize('NFKC', html.unescape(text))
    text = re.sub(r'[\u034f\u200b\ufeff\u00ad\u2060]', '', text)
    # Keep joiners inside words and emoji, remove padding.
    text = re.sub(r'(?<!\w)[\u200c]+|[\u200c]+(?!\w)', '', text)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    text = re.sub(r'\[\s*(?:https?://|www\.)[^\]]*\]|\b(?:https?://|www\.)[^\s<>]+', ' ', text, flags=re.I)
    text = re.sub(r'\btel:\+?[\d()-]+', '', text, flags=re.I)
    text = re.sub(r'[^\S\n]+', ' ', text)

    lines = []
    for line in text.splitlines():
        line = line.strip()
        if FOOTER.match(line):
            break
        if BOILERPLATE.fullmatch(line.strip('" ')):
            continue
        lines.append(line)
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip()


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
        return "\n\n".join(filter(None, (extract_email_body(part) for part in parts)))

    data = payload.get("body", {}).get("data")
    if not data or mime_type not in {"text/plain", "text/html"}:
        return ""

    decoded = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))
    charset = content_type.get_content_charset() or "utf-8"
    try:
        text = decoded.decode(charset, errors="replace")
    except LookupError:
        text = decoded.decode("utf-8", errors="replace")
    return clean_email_body(text, is_html=mime_type == "text/html")
