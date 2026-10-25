"""Security-sensitive configuration; no secret values in validation errors."""
import os
from urllib.parse import urlsplit
from cryptography.fernet import Fernet, MultiFernet, InvalidToken


class ConfigurationError(RuntimeError):
    pass


def redirect_uri():
    value = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:8000/auth/google/callback')
    parsed = urlsplit(value)
    local = parsed.hostname in ('localhost', '127.0.0.1', '::1')
    if (parsed.scheme not in ('https', 'http') or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in ('/auth/google/callback', '/api/auth/google/callback')
            or parsed.scheme == 'http' and (not local or os.getenv('APP_ENV', 'development') != 'development')):
        raise ConfigurationError('GOOGLE_REDIRECT_URI must be an HTTPS callback (loopback HTTP in development only)')
    return value


def cipher():
    try:
        keys = os.environ['OAUTH_TOKEN_KEYS'].split(',')
        return MultiFernet([Fernet(key.strip().encode('ascii')) for key in keys])
    except (KeyError, ValueError, UnicodeError) as error:
        raise ConfigurationError('Configure OAUTH_TOKEN_KEYS with Fernet keys; newest key first') from error


def encrypt(value):
    return 'v1:' + cipher().encrypt(value.encode('utf-8')).decode('ascii')


def decrypt(value):
    if not value.startswith('v1:'):
        raise ConfigurationError('Unsupported encrypted credential version')
    try:
        return cipher().decrypt(value[3:].encode('ascii')).decode('utf-8')
    except (InvalidToken, ValueError, UnicodeError) as error:
        raise ConfigurationError('Credential decryption failed; check key configuration') from error


def browser_origin():
    value = os.getenv('BROWSER_ORIGIN', 'http://localhost:5173' if os.getenv('APP_ENV', 'development') == 'development' else '')
    parsed = urlsplit(value)
    if (not parsed.hostname or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment
            or parsed.scheme not in ('https', 'http')
            or parsed.scheme == 'http' and (parsed.hostname not in ('localhost', '127.0.0.1', '::1')
                                           or os.getenv('APP_ENV', 'development') != 'development')):
        raise ConfigurationError('Configure BROWSER_ORIGIN as an exact HTTPS origin')
    return value
