from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.message import EmailMessage
import base64


# Gmail permission for reading/searching emails

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
]

BASE_DIR = Path(__file__).resolve().parent.parent

CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "gmail_token.json"


def get_gmail_service():
    """
    Authenticate the user and return a Gmail API service.
    """

    credentials = None

    # -----------------------------------------------------
    # 1. Load previously saved OAuth token
    # -----------------------------------------------------

    if TOKEN_FILE.exists():

        credentials = Credentials.from_authorized_user_file(
            str(TOKEN_FILE),
            SCOPES
        )

    # -----------------------------------------------------
    # 2. Refresh expired token if possible
    # -----------------------------------------------------

    if credentials and credentials.expired:

        if credentials.refresh_token:

            credentials.refresh(
                Request()
            )

    # -----------------------------------------------------
    # 3. Start OAuth flow if no valid credentials
    # -----------------------------------------------------

    if not credentials or not credentials.valid:

        if not CREDENTIALS_FILE.exists():

            raise FileNotFoundError(
                "credentials.json not found in backend folder."
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            str(CREDENTIALS_FILE),
            SCOPES
        )

        credentials = flow.run_local_server(
            port=0
        )

        # Save token for future requests
        TOKEN_FILE.write_text(
            credentials.to_json()
        )

    # -----------------------------------------------------
    # 4. Create Gmail API service
    # -----------------------------------------------------

    service = build(
        "gmail",
        "v1",
        credentials=credentials
    )

    return service

def search_emails(query: str, max_results: int = 10):
    """
    Search Gmail messages using a Gmail search query.
    """

    service = get_gmail_service()

    response = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=max_results
    ).execute()

    messages = response.get("messages", [])

    results = []

    for message in messages:

        message_data = service.users().messages().get(
            userId="me",
            id=message["id"],
            format="metadata",
            metadataHeaders=[
                "From",
                "To",
                "Subject",
                "Date"
            ]
        ).execute()

        headers = message_data.get(
            "payload",
            {}
        ).get(
            "headers",
            []
        )

        email_data = {}

        for header in headers:

            name = header["name"]
            value = header["value"]

            if name in [
                "From",
                "To",
                "Subject",
                "Date"
            ]:
                email_data[name.lower()] = value

        email_data["id"] = message["id"]

        results.append(email_data)

    return results

def read_email(message_id: str):
    service = get_gmail_service()

    message_data = service.users().messages().get(
        userId="me",
        id=message_id,
        format="full"
    ).execute()

    payload = message_data.get("payload", {})

    headers = payload.get("headers", [])

    email_data = {
        "id": message_id,
        "from": "",
        "to": "",
        "subject": "",
        "date": "",
        "body": ""
    }

    for header in headers:

        name = header["name"].lower()

        if name == "from":
            email_data["from"] = header["value"]

        elif name == "to":
            email_data["to"] = header["value"]

        elif name == "subject":
            email_data["subject"] = header["value"]

        elif name == "date":
            email_data["date"] = header["value"]

    parts = payload.get("parts", [])

    for part in parts:

        if part.get("mimeType") == "text/plain":

            body_data = part.get(
                "body",
                {}
            ).get(
                "data"
            )

            if body_data:
                import base64

                email_data["body"] = (
                    base64.urlsafe_b64decode(
                        body_data
                    )
                    .decode(
                        "utf-8",
                        errors="ignore"
                    )
                )

                break

    return email_data

def create_draft(
    to: str,
    subject: str,
    body: str
):
    """
    Create a Gmail draft.
    """

    service = get_gmail_service()

    message = EmailMessage()

    message["To"] = to
    message["Subject"] = subject

    message.set_content(body)

    encoded_message = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode()

    draft_body = {
        "message": {
            "raw": encoded_message
        }
    }

    draft = (
        service.users()
        .drafts()
        .create(
            userId="me",
            body=draft_body
        )
        .execute()
    )

    return {
        "draft_id": draft["id"],
        "message_id": draft["message"]["id"]
    }

def send_email(
    to: str,
    subject: str,
    body: str
):
    """
    Send an email through Gmail.
    """

    service = get_gmail_service()

    message = EmailMessage()

    message["To"] = to
    message["Subject"] = subject

    message.set_content(body)

    encoded_message = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode()

    send_body = {
        "raw": encoded_message
    }

    sent_message = (
        service.users()
        .messages()
        .send(
            userId="me",
            body=send_body
        )
        .execute()
    )

    return {
        "message_id": sent_message["id"]
    }

# ============================================================
# GMAIL REPLY
# ============================================================

from email.mime.text import MIMEText



def reply_to_email(
    message_id: str,
    body: str
):
    service = get_gmail_service()

    # --------------------------------------------------------
    # Get original email metadata
    # --------------------------------------------------------

    original = (
        service.users()
        .messages()
        .get(
            userId="me",
            id=message_id,
            format="metadata",
            metadataHeaders=[
                "From",
                "To",
                "Subject",
                "Message-ID",
                "References"
            ]
        )
        .execute()
    )

    headers = original.get(
        "payload",
        {}
    ).get(
        "headers",
        []
    )

    header_map = {
        header["name"].lower(): header["value"]
        for header in headers
    }

    original_from = header_map.get(
        "from",
        ""
    )

    original_subject = header_map.get(
        "subject",
        ""
    )

    original_message_id = header_map.get(
        "message-id",
        ""
    )

    original_references = header_map.get(
        "references",
        ""
    )

    # --------------------------------------------------------
    # Create reply subject
    # --------------------------------------------------------

    if original_subject.lower().startswith("re:"):
        reply_subject = original_subject
    else:
        reply_subject = f"Re: {original_subject}"

    # --------------------------------------------------------
    # Create MIME reply
    # --------------------------------------------------------

    message = MIMEText(
        body,
        "plain",
        "utf-8"
    )

    message["To"] = original_from
    message["Subject"] = reply_subject

    if original_message_id:
        message["In-Reply-To"] = original_message_id

    if original_references:
        message["References"] = (
            f"{original_references} "
            f"{original_message_id}"
        ).strip()
    elif original_message_id:
        message["References"] = original_message_id

    # --------------------------------------------------------
    # Encode message
    # --------------------------------------------------------

    raw_message = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode()

    # --------------------------------------------------------
    # Send reply in same Gmail thread
    # --------------------------------------------------------

    sent_message = (
        service.users()
        .messages()
        .send(
            userId="me",
            body={
                "raw": raw_message,
                "threadId": original.get(
                    "threadId"
                )
            }
        )
        .execute()
    )

    return {
        "message_id": sent_message.get(
            "id"
        ),

        "thread_id": sent_message.get(
            "threadId"
        ),

        "to": original_from,

        "subject": reply_subject
    }

# ============================================================
# GMAIL FORWARD
# ============================================================

def forward_email(
    message_id: str,
    to: str,
    body: str = ""
):
    """
    Forward an existing Gmail email to another recipient.
    """

    service = get_gmail_service()

    # --------------------------------------------------------
    # Get original email
    # --------------------------------------------------------

    original = (
        service.users()
        .messages()
        .get(
            userId="me",
            id=message_id,
            format="full"
        )
        .execute()
    )

    payload = original.get("payload", {})
    headers = payload.get("headers", [])

    header_map = {
        header["name"].lower(): header["value"]
        for header in headers
    }

    original_subject = header_map.get("subject", "")
    original_from = header_map.get("from", "")
    original_date = header_map.get("date", "")

    # --------------------------------------------------------
    # Get original body
    # --------------------------------------------------------

    original_body = ""

    parts = payload.get("parts", [])

    for part in parts:
        if part.get("mimeType") == "text/plain":
            body_data = (
                part.get("body", {})
                .get("data")
            )

            if body_data:
                original_body = (
                    base64.urlsafe_b64decode(
                        body_data
                    )
                    .decode(
                        "utf-8",
                        errors="ignore"
                    )
                )
                break

    # --------------------------------------------------------
    # Create forwarded message
    # --------------------------------------------------------

    message = MIMEText(
        f"{body}\n\n"
        f"---------- Forwarded message ----------\n"
        f"From: {original_from}\n"
        f"Date: {original_date}\n"
        f"Subject: {original_subject}\n\n"
        f"{original_body}",
        "plain",
        "utf-8"
    )

    message["To"] = to

    if original_subject.lower().startswith("fwd:"):
        forward_subject = original_subject
    else:
        forward_subject = f"Fwd: {original_subject}"

    message["Subject"] = forward_subject

    # --------------------------------------------------------
    # Encode message
    # --------------------------------------------------------

    raw_message = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode()

    # --------------------------------------------------------
    # Send forwarded email
    # --------------------------------------------------------

    sent_message = (
        service.users()
        .messages()
        .send(
            userId="me",
            body={
                "raw": raw_message
            }
        )
        .execute()
    )

    return {
        "message_id": sent_message.get("id"),
        "to": to,
        "subject": forward_subject
    }