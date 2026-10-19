"""Shared local artifact paths for inbox-nizer training and inference."""
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / '.env')
DEFAULT_MODEL_DIR = PROJECT_ROOT / 'results' / 'email-classifier'


def model_path(value=None):
    """Resolve explicit/env model paths against the project, never the shell CWD."""
    path = Path(value or os.getenv('EMAIL_MODEL_PATH') or DEFAULT_MODEL_DIR).expanduser()
    return path.resolve() if path.is_absolute() else (PROJECT_ROOT / path).resolve()
