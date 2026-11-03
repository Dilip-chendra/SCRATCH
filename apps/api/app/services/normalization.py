import re
import urllib.parse
from typing import Optional, Tuple
import tldextract

# Initialize offline TLDExtract instance using the bundled Mozilla Public Suffix List
# Setting suffix_list_urls=None ensures strict offline execution with zero network dependencies
_tld_extractor = tldextract.TLDExtract(suffix_list_urls=None)

# Comprehensive list of consumer/free webmail domains
# Used to prevent personal email addresses from falsely generating company accounts
CONSUMER_WEBMAIL_DOMAINS = {
    # Google
    "gmail.com", "googlemail.com",
    # Microsoft
    "hotmail.com", "hotmail.co.uk", "hotmail.fr", "hotmail.de", "hotmail.es", "hotmail.it",
    "outlook.com", "outlook.co.uk", "outlook.fr", "outlook.de", "outlook.es",
    "live.com", "live.co.uk", "live.fr", "msn.com",
    # Yahoo
    "yahoo.com", "yahoo.co.uk", "yahoo.ca", "yahoo.com.au", "yahoo.co.jp",
    "yahoo.fr", "yahoo.de", "yahoo.es", "yahoo.it", "yahoo.com.br", "yahoo.in",
    "ymail.com", "rocketmail.com",
    # Apple
    "icloud.com", "me.com", "mac.com",
    # AOL
    "aol.com", "aim.com",
    # Proton
    "proton.me", "protonmail.com", "protonmail.ch", "pm.me",
    # Zoho Personal
    "zoho.com", "zohomail.com",
    # Mail.com & GMX
    "mail.com", "email.com", "gmx.com", "gmx.de", "gmx.net", "gmx.at", "web.de",
    # Yandex & Mail.ru
    "yandex.com", "yandex.ru", "mail.ru", "inbox.ru", "bk.ru", "list.ru",
    # Tuta
    "tutanota.com", "tuta.io", "tuta.com",
    # Fastmail
    "fastmail.com", "fastmail.fm",
    # Major ISP / Telecom Consumer Domains
    "comcast.net", "sbcglobal.net", "att.net", "verizon.net", "bellsouth.net",
    "charter.net", "cox.net", "earthlink.net", "shaw.ca", "rogers.com",
    "btinternet.com", "virginmedia.com", "sky.com", "orange.fr", "wanadoo.fr",
    "free.fr", "t-online.de",
}

EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
)


def normalize_domain(raw_input: Optional[str]) -> str:
    """
    Extracts the canonical registrable host domain from an arbitrary URL, hostname, or email
    using the maintained Mozilla Public Suffix List (PSL).

    Handles:
    - Whitespace and casing: '  HTTPS://WWW.Acme.COM/path  ' -> 'acme.com'
    - Scheme stripping: 'http://', 'https://', 'ftp://', '//'
    - Port, path, query strings, and fragments: 'acme.com:8080/index.html?ref=123#frag' -> 'acme.com'
    - Userinfo credentials: 'user:pass@acme.com' -> 'acme.com'
    - Country-code second-level domains (ccSLD):
      'company.co.id' -> 'company.co.id'
      'firm.com.pk' -> 'firm.com.pk'
      'portal.sub.acme.co.uk' -> 'acme.co.uk'
      'news.bbc.co.uk' -> 'bbc.co.uk'
      'canberra.gov.au' -> 'canberra.gov.au'
    - Common subdomains: 'www.acme.com' -> 'acme.com', 'blog.acme.io' -> 'acme.io'
    - IDN / Punycode: 'münchen.de' -> 'xn--mnchen-3ya.de'
    - Malformed or invalid inputs: IP addresses, localhost, or bare public suffixes
      ('co.uk', 'com') return ''

    Returns:
        Canonical lowercase domain string (e.g. 'stripe.com'), or empty string if invalid.
    """
    if not raw_input:
        return ""

    raw = raw_input.strip()
    if not raw:
        return ""

    # If an email address is passed, extract domain part
    if "@" in raw and not (raw.startswith("http://") or raw.startswith("https://")):
        parts = raw.split("@")
        raw = parts[-1].strip()

    # Handle protocol-relative URL '//domain.com'
    if raw.startswith("//"):
        raw = "http:" + raw
    elif not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", raw):
        raw = "http://" + raw

    try:
        parsed = urllib.parse.urlparse(raw)
        host = parsed.hostname or ""
    except Exception:
        return ""

    host = host.strip().lower().rstrip(".")

    # Handle Punycode conversion if non-ASCII characters exist
    try:
        host = host.encode("idna").decode("ascii")
    except Exception:
        pass

    if not host or "." not in host:
        return ""

    # Reject IPv4 / IPv6 addresses as corporate domains
    if re.match(r"^(\d{1,3}\.){3}\d{1,3}$", host) or ":" in host:
        return ""

    # Extract registrable domain using Public Suffix List
    ext = _tld_extractor(host)

    # If domain or public suffix is missing, it is a bare suffix or invalid (e.g. 'co.uk', 'com')
    if not ext.domain or not ext.suffix:
        return ""

    return f"{ext.domain}.{ext.suffix}"


def is_consumer_webmail_domain(raw_input: Optional[str]) -> bool:
    """
    Checks if a domain or email address belongs to a consumer/free webmail provider
    (e.g. Gmail, Yahoo, Hotmail, Outlook, iCloud, Proton).
    """
    if not raw_input:
        return False

    raw = raw_input.strip().lower()
    if "@" in raw and not (raw.startswith("http://") or raw.startswith("https://")):
        raw = raw.split("@")[-1].strip()

    # Check both direct match and normalized domain match
    if raw in CONSUMER_WEBMAIL_DOMAINS:
        return True

    dom = normalize_domain(raw)
    return dom in CONSUMER_WEBMAIL_DOMAINS


def normalize_email(raw_email: Optional[str]) -> str:
    """
    Normalizes and validates an email address.

    Returns:
        Lowercase trimmed email string, or empty string if invalid.
    """
    if not raw_email:
        return ""

    cleaned = raw_email.strip().lower()
    if not cleaned or not EMAIL_REGEX.match(cleaned):
        return ""

    return cleaned


def split_full_name(full_name: Optional[str]) -> Tuple[str, str]:
    """
    Splits a full name into (first_name, last_name).
    Handles single-word names, multi-word surnames, and titles.
    """
    if not full_name:
        return ("", "")

    cleaned = " ".join(full_name.strip().split())
    if not cleaned:
        return ("", "")

    # Remove common prefix honorifics
    honorifics = {"mr.", "mr", "ms.", "ms", "mrs.", "mrs", "dr.", "dr", "prof.", "prof"}
    tokens = cleaned.split(" ")
    if len(tokens) > 1 and tokens[0].lower() in honorifics:
        tokens = tokens[1:]

    if not tokens:
        return ("", "")
    if len(tokens) == 1:
        return (tokens[0], "")

    first_name = tokens[0]
    last_name = " ".join(tokens[1:])
    return (first_name, last_name)
