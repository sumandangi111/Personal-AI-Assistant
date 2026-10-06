from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import logging

logger = logging.getLogger(__name__)

# ============================================================
# GOOGLE CALENDAR CONFIGURATION
# ============================================================

SCOPES = [
    "https://www.googleapis.com/auth/calendar"
]

BASE_DIR = Path(__file__).resolve().parent.parent

CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token.json"

INDIA_TIMEZONE = "Asia/Kolkata"

INDIA_ZONE = ZoneInfo(
    INDIA_TIMEZONE
)


# ============================================================
# DATETIME HELPER
# ============================================================

def convert_to_ist(
    datetime_string: str | None
):
    """
    Convert a datetime returned by Google Calendar
    into Asia/Kolkata timezone.
    """

    if not datetime_string:
        return datetime_string

    try:
        dt = datetime.fromisoformat(
            datetime_string.replace(
                "Z",
                "+00:00"
            )
        )

        # If Google returns a datetime without timezone,
        # assume it is already in IST.
        if dt.tzinfo is None:
            dt = dt.replace(
                tzinfo=INDIA_ZONE
            )

        dt = dt.astimezone(
            INDIA_ZONE
        )

        return dt.isoformat()

    except Exception:
        return datetime_string


# ============================================================
# GOOGLE CALENDAR SERVICE
# ============================================================

def get_calendar_service():
    credentials = None

    if TOKEN_FILE.exists():
        try:
            credentials = Credentials.from_authorized_user_file(
                str(TOKEN_FILE),
                SCOPES
            )
        except Exception:
            logger.exception("Failed to load Google Calendar token.")
            credentials = None

    if credentials and credentials.expired:
        if credentials.refresh_token:
            try:
                credentials.refresh(Request())
            except Exception:
                logger.exception(
                    "Failed to refresh Google Calendar credentials."
                )
                credentials = None

    if not credentials or not credentials.valid:

        if not CREDENTIALS_FILE.exists():
            raise FileNotFoundError(
                "Google Calendar credentials are not configured."
            )

        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE),
                SCOPES
            )

            credentials = flow.run_local_server(
                port=0
            )

            TOKEN_FILE.write_text(
                credentials.to_json()
            )

        except Exception:
            logger.exception(
                "Google Calendar OAuth authentication failed."
            )
            raise

    service = build(
        "calendar",
        "v3",
        credentials=credentials
    )

    return service
# ============================================================
# LIST UPCOMING EVENTS
# ============================================================

def list_events(
    max_results: int = 10
):
    service = get_calendar_service()

    now = datetime.now(
        INDIA_ZONE
    )

    events_result = (
        service.events()
        .list(
            calendarId="primary",
            maxResults=max_results,
            timeMin=now.isoformat(),
            singleEvents=True,
            orderBy="startTime"
        )
        .execute()
    )

    events = events_result.get(
        "items",
        []
    )

    results = []

    for event in events:

        start = event.get(
            "start",
            {}
        )

        end = event.get(
            "end",
            {}
        )

        start_datetime = (
            start.get("dateTime")
            or start.get("date")
        )

        end_datetime = (
            end.get("dateTime")
            or end.get("date")
        )

        results.append({
            "id": event.get("id"),

            "summary": event.get(
                "summary",
                ""
            ),

            "description": event.get(
                "description",
                ""
            ),

            "start": (
                {
                    "dateTime": convert_to_ist(
                        start.get("dateTime")
                    )
                }
                if start.get("dateTime")
                else {
                    "date": start.get("date")
                }
            ),

            "end": (
                {
                    "dateTime": convert_to_ist(
                        end.get("dateTime")
                    )
                }
                if end.get("dateTime")
                else {
                    "date": end.get("date")
                }
            ),

            "location": event.get(
                "location",
                ""
            ),

            "status": event.get(
                "status",
                ""
            )
        })
    return results


# ============================================================
# CREATE EVENT
# ============================================================

def create_event(
    summary: str,
    start_datetime: str,
    end_datetime: str,
    description: str = "",
    location: str = ""
):
    service = get_calendar_service()

    event_body = {
        "summary": summary,

        "description": description,

        "location": location,

        "start": {
            "dateTime": start_datetime,
            "timeZone": INDIA_TIMEZONE
        },

        "end": {
            "dateTime": end_datetime,
            "timeZone": INDIA_TIMEZONE
        }
    }

    event = (
        service.events()
        .insert(
            calendarId="primary",
            body=event_body
        )
        .execute()
    )

    return {
        "event_id": event.get(
            "id"
        ),

        "summary": event.get(
            "summary"
        ),

        "start": convert_to_ist(
            event.get(
                "start",
                {}
            ).get(
                "dateTime"
            )
        ),

        "end": convert_to_ist(
            event.get(
                "end",
                {}
            ).get(
                "dateTime"
            )
        ),

        "html_link": event.get(
            "htmlLink"
        )
    }


# ============================================================
# UPDATE / RESCHEDULE EVENT
# ============================================================

def update_event(
    event_id: str,
    summary: str | None = None,
    start_datetime: str | None = None,
    end_datetime: str | None = None,
    description: str | None = None,
    location: str | None = None
):
    service = get_calendar_service()

    existing_event = (
        service.events()
        .get(
            calendarId="primary",
            eventId=event_id
        )
        .execute()
    )

    # --------------------------------------------------------
    # UPDATE TITLE
    # --------------------------------------------------------

    if summary is not None:
        existing_event["summary"] = summary

    # --------------------------------------------------------
    # UPDATE DESCRIPTION
    # --------------------------------------------------------

    if description is not None:
        existing_event["description"] = description

    # --------------------------------------------------------
    # UPDATE LOCATION
    # --------------------------------------------------------

    if location is not None:
        existing_event["location"] = location

    # --------------------------------------------------------
    # UPDATE START TIME
    # --------------------------------------------------------

    if start_datetime is not None:
        existing_event["start"] = {
            "dateTime": start_datetime,
            "timeZone": INDIA_TIMEZONE
        }

    # --------------------------------------------------------
    # UPDATE END TIME
    # --------------------------------------------------------

    if end_datetime is not None:
        existing_event["end"] = {
            "dateTime": end_datetime,
            "timeZone": INDIA_TIMEZONE
        }

    updated_event = (
        service.events()
        .update(
            calendarId="primary",
            eventId=event_id,
            body=existing_event
        )
        .execute()
    )

    return {
        "event_id": updated_event.get(
            "id"
        ),

        "summary": updated_event.get(
            "summary"
        ),

        "start": convert_to_ist(
            updated_event.get(
                "start",
                {}
            ).get(
                "dateTime"
            )
        ),

        "end": convert_to_ist(
            updated_event.get(
                "end",
                {}
            ).get(
                "dateTime"
            )
        ),

        "description": updated_event.get(
            "description",
            ""
        ),

        "location": updated_event.get(
            "location",
            ""
        ),

        "html_link": updated_event.get(
            "htmlLink"
        )
    }


# ============================================================
# DELETE EVENT
# ============================================================

def delete_event(
    event_id: str
):
    service = get_calendar_service()

    service.events().delete(
        calendarId="primary",
        eventId=event_id
    ).execute()

    return {
        "message": (
            "Calendar event deleted successfully."
        ),

        "event_id": event_id
    }
