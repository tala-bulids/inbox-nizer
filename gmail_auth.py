from google_auth_oauthlib.flow import Flow


SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly"
]

REDIRECT_URI = "http://localhost:8000/auth/google/callback"


def create_google_flow(state=None, code_verifier=None):
    flow = Flow.from_client_secrets_file(
        "credentials.json",
        scopes=SCOPES,
        state=state,
        code_verifier=code_verifier,
        redirect_uri=REDIRECT_URI
    )

    return flow