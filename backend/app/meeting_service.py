from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .calendar_service import get_calendar_service


# ============================================================
# CONFIGURATION
# ============================================================

APP_TIMEZONE = ZoneInfo("Asia/Kolkata")
CALENDAR_ID = "primary"


# ============================================================
# DATETIME HELPERS
# ============================================================

def _parse_datetime(value: str) -> datetime:
    """
    Parse an ISO datetime and normalize it to Asia/Kolkata.
    """

    value = value.strip()

    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            "Invalid datetime format. Use ISO 8601 format."
        ) from exc

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=APP_TIMEZONE)

    return dt.astimezone(APP_TIMEZONE)


def _event_start(event):
    start = event.get("start", {})

    value = (
        start.get("dateTime")
        or start.get("date")
    )

    if not value:
        return None

    if "T" not in value:
        return datetime.fromisoformat(
            value
        ).replace(
            tzinfo=APP_TIMEZONE
        )

    return _parse_datetime(value)


def _event_end(event):
    end = event.get("end", {})

    value = (
        end.get("dateTime")
        or end.get("date")
    )

    if not value:
        return None

    if "T" not in value:
        return datetime.fromisoformat(
            value
        ).replace(
            tzinfo=APP_TIMEZONE
        )

    return _parse_datetime(value)


# ============================================================
# ADMIN CALENDAR
# ============================================================

def _get_admin_events(
    start_datetime: datetime,
    end_datetime: datetime,
):
    """
    Get Admin calendar events.

    Private event information is used internally only.
    It is never returned to normal users.
    """

    service = get_calendar_service()

    response = (
        service.events()
        .list(
            calendarId=CALENDAR_ID,
            timeMin=start_datetime.isoformat(),
            timeMax=end_datetime.isoformat(),
            singleEvents=True,
            orderBy="startTime",
            maxResults=100,
        )
        .execute()
    )

    return response.get("items", [])


def _is_slot_available(
    slot_start: datetime,
    slot_end: datetime,
    events,
):
    """
    Check whether a time slot overlaps any Admin event.
    """

    for event in events:

        if event.get("status") == "cancelled":
            continue

        event_start = _event_start(event)
        event_end = _event_end(event)

        if not event_start or not event_end:
            continue

        # Overlap detection
        if (
            slot_start < event_end
            and slot_end > event_start
        ):
            return False

    return True


# ============================================================
# FIND AVAILABLE SLOT
# ============================================================

def find_available_slot(
    requested_start,
    duration_minutes=30,
    search_minutes=480,
    interval_minutes=30,
):
    """
    Find the first available Admin slot.

    The search starts at requested_start and moves forward
    in interval_minutes increments.
    """

    if duration_minutes <= 0:
        raise ValueError(
            "Meeting duration must be greater than 0."
        )

    if duration_minutes > 480:
        raise ValueError(
            "Meeting duration cannot exceed 8 hours."
        )

    requested_start = requested_start.astimezone(
        APP_TIMEZONE
    )

    requested_end = (
        requested_start
        + timedelta(minutes=duration_minutes)
    )

    search_end = (
        requested_start
        + timedelta(minutes=search_minutes)
    )

    events = _get_admin_events(
        requested_start,
        search_end,
    )

    candidate_start = requested_start

    while candidate_start < search_end:

        candidate_end = (
            candidate_start
            + timedelta(minutes=duration_minutes)
        )

        if candidate_end > search_end:
            break

        if _is_slot_available(
            candidate_start,
            candidate_end,
            events,
        ):
            return {
                "start": candidate_start,
                "end": candidate_end,
            }

        candidate_start += timedelta(
            minutes=interval_minutes
        )

    return None


# ============================================================
# CHECK ADMIN AVAILABILITY
# ============================================================

def check_admin_availability(
    requested_datetime,
    duration_minutes=30,
):
    """
    Check the requested Admin meeting time.

    Only availability information is returned.
    Admin event titles/details are never exposed.
    """

    requested_start = _parse_datetime(
        requested_datetime
    )

    slot = find_available_slot(
        requested_start=requested_start,
        duration_minutes=duration_minutes,
    )

    if not slot:

        return {
            "available": False,
            "requested_time": requested_start.isoformat(),
            "slot": None,
            "message": (
                "No available Admin slot was found "
                "within the requested search period."
            ),
        }

    is_requested_time = (
        slot["start"] == requested_start
    )

    if is_requested_time:

        message = (
            "Admin is available at the requested time."
        )

    else:

        message = (
            "The requested time is unavailable. "
            "This is the next available Admin slot."
        )

    return {
        "available": is_requested_time,
        "requested_time": requested_start.isoformat(),
        "slot": {
            "start": slot["start"].isoformat(),
            "end": slot["end"].isoformat(),
        },
        "message": message,
    }


# ============================================================
# CREATE USER MEETING
# ============================================================

def create_user_meeting(
    user_id: int,
    user_name: str,
    user_email: str,
    start_datetime: str,
    duration_minutes: int = 30,
):
    """
    Create a meeting between the normal user and Admin.

    The meeting is stored on the Admin's Google Calendar.

    A private extended property identifies the requesting user.
    """

    requested_start = _parse_datetime(
        start_datetime
    )

    requested_end = (
        requested_start
        + timedelta(minutes=duration_minutes)
    )

    # --------------------------------------------------------
    # IMPORTANT:
    # Check availability again immediately before creation.
    # This prevents two users from booking the same slot
    # between availability check and actual booking.
    # --------------------------------------------------------

    events = _get_admin_events(
        requested_start,
        requested_end,
    )

    if not _is_slot_available(
        requested_start,
        requested_end,
        events,
    ):
        return {
            "success": False,
            "message": (
                "This meeting slot is no longer available."
            ),
            "event": None,
        }

    service = get_calendar_service()


    event_body = {
        "summary": f"Meeting with {user_name}",
        "description": (
            f"User Name: {user_name}\n"
            f"User Email: {user_email}\n"
            f"Booked through Personal AI Assistant."
        ),
        "start": {
            "dateTime": requested_start.isoformat(),
            "timeZone": "Asia/Kolkata",
        },
        "end": {
            "dateTime": requested_end.isoformat(),
            "timeZone": "Asia/Kolkata",
        },
        "attendees": [
            {
                "email": user_email,
            }
        ],
        "extendedProperties": {
            "private": {
                "assistant_meeting": "true",
                "assistant_user_id": str(user_id),
                "assistant_user_email": user_email,
            }
        },
    }

    
    created_event = (
        service.events()
        .insert(
            calendarId=CALENDAR_ID,
            body=event_body,
            sendUpdates="none",
        )
        .execute()
    )

    return {
        "success": True,
        "message": "Meeting scheduled successfully.",
        "event": {
            "id": created_event.get("id"),
            "start": requested_start.isoformat(),
            "end": requested_end.isoformat(),
        },
    }


# ============================================================
# GET USER'S MEETINGS
# ============================================================

def get_user_meetings(
    user_id: int,
    max_results: int = 20,
):
    """
    Return only meetings belonging to the current user.

    Admin's other private calendar events are never returned.
    """

    service = get_calendar_service()

    response = (
        service.events()
        .list(
            calendarId=CALENDAR_ID,
            privateExtendedProperty=(
                f"assistant_user_id={user_id}"
            ),
            singleEvents=True,
            orderBy="startTime",
            maxResults=max_results,
        )
        .execute()
    )

    meetings = []

    for event in response.get("items", []):

        if event.get("status") == "cancelled":
            continue

        start = _event_start(event)
        end = _event_end(event)

        if not start or not end:
            continue

        meetings.append(
            {
                "id": event.get("id"),
                "title": event.get(
                    "summary",
                    "Meeting with Admin",
                ),
                "start": start.isoformat(),
                "end": end.isoformat(),
                "status": "scheduled",
            }
        )

    return meetings

