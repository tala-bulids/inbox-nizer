"""Server-owned capability boundary; full/local remains the default."""
import os
from fastapi import HTTPException


def runtime_profile():
    return os.getenv('INBOX_RUNTIME_PROFILE', 'full').strip().lower()


def require_retrieval():
    if runtime_profile() == 'render-free':
        raise HTTPException(403, detail={
            'code': 'runtime_disabled',
            'message': 'Search and Ask are unavailable in this runtime.',
        })
