from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly"
]


def get_gmail_service():
    credentials = Credentials.from_authorized_user_file(
        "token.json",
        SCOPES
    )

    service = build(
        "gmail",
        "v1",
        credentials=credentials
    )

    return service