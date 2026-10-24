from google_auth_oauthlib.flow import Flow
import os
from backend_config import redirect_uri


SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly"
]

REDIRECT_URI = "http://localhost:8000/auth/google/callback"


def create_google_flow(state=None, code_verifier=None):
    flow = Flow.from_client_secrets_file(
        os.getenv('GOOGLE_CLIENT_FILE', 'credentials.json'),
        scopes=SCOPES,
        state=state,
        code_verifier=code_verifier,
        redirect_uri=redirect_uri()
    )

    return flow
