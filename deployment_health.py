"""Small, read-only operational probes; never expose configuration or mailbox data."""
import json
import os
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from backend_config import browser_origin, cipher, redirect_uri, ConfigurationError
from database import engine
from google_login import callback_uri

router = APIRouter()


@lru_cache(maxsize=1)
def expected_schema_revision():
    config = Config()
    config.set_main_option('script_location', str(Path(__file__).parent / 'alembic'))
    return ScriptDirectory.from_config(config).get_current_head()


def validate_production_configuration():
    if os.getenv('APP_ENV', 'development') == 'development':
        return
    origin = urlsplit(browser_origin())
    for callback in (redirect_uri(), callback_uri()):
        parsed = urlsplit(callback)
        if (parsed.scheme, parsed.netloc) != (origin.scheme, origin.netloc):
            raise ConfigurationError('OAuth callbacks must share the browser origin')
    if os.getenv('OAUTHLIB_INSECURE_TRANSPORT'):
        raise ConfigurationError('Insecure OAuth transport is not allowed in production')
    cipher()
    path = Path(os.getenv('GOOGLE_CLIENT_FILE', 'credentials.json'))
    with path.open(encoding='utf-8') as source:
        client = json.load(source).get('web', {})
    if not all(client.get(key) for key in ('client_id', 'client_secret', 'auth_uri', 'token_uri')):
        raise ConfigurationError('Configure a Google web OAuth client')


def database_is_ready():
    # Conservatively reject owner/admin membership even with NOINHERIT.
    # The engine bounds connection and pool waits. No mutations, model loads,
    # provider calls, syncs or mailbox reads belong in this probe.
    with engine.connect() as connection:
        revision = connection.scalar(text('SELECT version_num FROM alembic_version'))
        role = connection.execute(text('''
            SELECT rolsuper, rolcreatedb, rolcreaterole, rolbypassrls,
                   pg_has_role(current_user, datdba, 'MEMBER') AS owns_database,
                   EXISTS (SELECT 1 FROM pg_tables WHERE schemaname='public'
                           AND pg_has_role(current_user, tableowner, 'MEMBER')) AS owns_tables,
                   has_database_privilege(current_user, current_database(), 'CREATE') AS creates_schemas,
                   has_schema_privilege(current_user, 'public', 'CREATE') AS creates_objects,
                   EXISTS (SELECT 1 FROM pg_roles privileged
                           WHERE (privileged.rolsuper OR privileged.rolcreatedb
                                  OR privileged.rolcreaterole OR privileged.rolbypassrls)
                           AND pg_has_role(current_user, privileged.oid, 'MEMBER')) AS admin_member,
                   EXISTS (SELECT 1 FROM pg_namespace WHERE nspname='public'
                           AND pg_has_role(current_user, nspowner, 'MEMBER')) AS owns_schema
            FROM pg_roles JOIN pg_database ON datname=current_database()
            WHERE rolname=current_user
        ''')).one()
        return revision == expected_schema_revision() and not any(role)


@router.get('/health/live', include_in_schema=False)
def live():
    return {'status': 'alive'}


@router.get('/health/ready', include_in_schema=False)
def ready():
    try:
        validate_production_configuration()
        if database_is_ready():
            return {'status': 'ready'}
    except Exception:
        pass
    return JSONResponse(status_code=503, content={'status': 'unavailable'})
