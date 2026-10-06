from .calendar_service import (
    list_events,
    create_event,
    delete_event,
    update_event
)

from .gmail_service import (
    search_emails,
    create_draft,
    send_email,
    reply_to_email,
)

from .meeting_service import (
    check_admin_availability,
    get_user_meetings,
)

from .models import MeetingRequest

# ============================================================
# GMAIL DRAFT
# ============================================================

def gmail_draft_tool(
    to: str,
    subject: str,
    body: str
):
    # Convert escaped newline characters into real line breaks
    body = body.replace("\\n", "\n")

    draft = create_draft(
        to=to,
        subject=subject,
        body=body
    )

    return {
        "tool": "gmail_draft",
        "message": "Draft created successfully.",
        "to": to,
        "subject": subject,
        "draft_id": draft["draft_id"],
        "message_id": draft["message_id"]
    }


GMAIL_DRAFT_TOOL = {
    "name": "gmail_draft",
    "description": (
        "Create a Gmail draft. "
        "Use this tool when the user explicitly asks "
        "to draft or prepare an email. "
        "Do not send the email."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "to": {
                "type": "string",
                "description": "Recipient email address."
            },
            "subject": {
                "type": "string",
                "description": "Email subject."
            },
            "body": {
                "type": "string",
                "description": "Email body."
            }
        },
        "required": [
            "to",
            "subject",
            "body"
        ]
    }
}


# ============================================================
# GMAIL SEARCH
# ============================================================

def gmail_search_tool(
    query: str,
    max_results: int = 5
):
    results = search_emails(
        query=query,
        max_results=max_results
    )

    return {
        "tool": "gmail_search",
        "query": query,
        "results": results
    }


def build_gmail_query(user_message: str):
    message = user_message.lower().strip()

    if "from google" in message:
        return "from:google"

    if "from chatgpt" in message:
        return "from:chatgpt"

    if "unread" in message:
        return "is:unread"

    if "today" in message:
        return "newer_than:1d"

    if "yesterday" in message:
        return "older_than:1d newer_than:2d"

    return "in:inbox"


GMAIL_TOOL = {
    "name": "gmail_search",
    "description": (
        "Search the user's Gmail inbox. "
        "Use this tool when the user asks about emails, "
        "messages, Gmail, inbox messages, unread emails, "
        "emails from a person or organization, or emails "
        "matching a specific topic."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "A Gmail search query. "
                    "Examples: 'from:google', "
                    "'is:unread', "
                    "'newer_than:1d', "
                    "'from:google security'"
                )
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of emails to return.",
                "default": 5
            }
        },
        "required": [
            "query"
        ]
    }
}


# ============================================================
# GMAIL READ
# ============================================================

GMAIL_READ_TOOL = {
    "name": "gmail_read",
    "description": (
        "Read the full contents of a specific Gmail email. "
        "Use this tool when the user asks to read, open, "
        "summarize, or inspect a specific email."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "message_id": {
                "type": "string",
                "description": (
                    "The Gmail message ID of the email to read."
                )
            }
        },
        "required": [
            "message_id"
        ]
    }
}


def gmail_read_tool(
    message_id: str
):
    from .gmail_service import read_email

    email = read_email(
        message_id=message_id
    )

    return {
        "tool": "gmail_read",
        "email": email
    }


# ============================================================
# GMAIL SEND
# ============================================================

def gmail_send_tool(
    to: str,
    subject: str,
    body: str
):
    result = send_email(
        to=to,
        subject=subject,
        body=body
    )

    return {
        "tool": "gmail_send",
        "message": "Email sent successfully.",
        "to": to,
        "subject": subject,
        "message_id": result["message_id"]
    }


GMAIL_SEND_TOOL = {
    "name": "gmail_send",
    "description": (
        "Send an email through Gmail. "
        "This action must only be executed after "
        "the user has explicitly confirmed that "
        "the email should be sent."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "to": {
                "type": "string",
                "description": "Recipient email address."
            },
            "subject": {
                "type": "string",
                "description": "Email subject."
            },
            "body": {
                "type": "string",
                "description": "Email body."
            }
        },
        "required": [
            "to",
            "subject",
            "body"
        ]
    }
}

# ============================================================
# GMAIL REPLY PREPARE
# ============================================================

GMAIL_REPLY_PREPARE_TOOL = {
    "name": "gmail_reply_prepare",
    "description": (
        "Prepare a reply to a specific Gmail email. "
        "Do not send the reply immediately. "
        "This tool should be used when the user wants "
        "to reply to an existing email. "
        "The user must explicitly confirm before the "
        "reply is actually sent."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "message_id": {
                "type": "string",
                "description": (
                    "The Gmail message ID of the email "
                    "being replied to."
                )
            },
            "body": {
                "type": "string",
                "description": (
                    "The reply message that will be sent."
                )
            }
        },
        "required": [
            "message_id",
            "body"
        ]
    }
}

# ============================================================
# GMAIL FORWARD PREPARE
# ============================================================

GMAIL_FORWARD_PREPARE_TOOL = {
    "name": "gmail_forward_prepare",
    "description": (
        "Prepare an existing Gmail email to be forwarded "
        "to another recipient. "
        "Do not send the forwarded email immediately. "
        "This tool should be used when the user wants "
        "to forward an existing email. "
        "The user must explicitly confirm before the "
        "forwarded email is actually sent."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "message_id": {
                "type": "string",
                "description": (
                    "The Gmail message ID of the email "
                    "being forwarded."
                )
            },
            "to": {
                "type": "string",
                "description": (
                    "The email address of the person "
                    "who should receive the forwarded email."
                )
            },
            "body": {
                "type": "string",
                "description": (
                    "Optional message to include before "
                    "the forwarded email."
                )
            }
        },
        "required": [
            "message_id",
            "to"
        ]
    }
}

# ============================================================
# GOOGLE CALENDAR - LIST
# ============================================================

CALENDAR_LIST_TOOL = {
    "name": "calendar_list_events",
    "description": (
        "List upcoming events from the user's Google Calendar."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "max_results": {
                "type": "integer",
                "description": "Maximum number of events to return."
            }
        },
        "required": []
    }
}


def calendar_list_tool(
    max_results: int = 10
):
    events = list_events(
        max_results=max_results
    )

    return {
        "tool": "calendar_list_events",
        "events": events
    }


# ============================================================
# GOOGLE CALENDAR - CREATE
# ============================================================

CALENDAR_CREATE_TOOL = {
    "name": "calendar_create_event",
    "description": (
        "Create an event in the user's Google Calendar."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "Event title."
            },
            "start_datetime": {
                "type": "string",
                "description": (
                    "Event start datetime in ISO 8601 format, "
                    "including timezone."
                )
            },
            "end_datetime": {
                "type": "string",
                "description": (
                    "Event end datetime in ISO 8601 format, "
                    "including timezone."
                )
            },
            "description": {
                "type": "string",
                "description": "Optional event description."
            },
            "location": {
                "type": "string",
                "description": "Optional event location."
            }
        },
        "required": [
            "summary",
            "start_datetime",
            "end_datetime"
        ]
    }
}


def calendar_create_tool(
    summary: str,
    start_datetime: str,
    end_datetime: str,
    description: str = "",
    location: str = ""
):
    event = create_event(
        summary=summary,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        description=description,
        location=location
    )

    return {
        "tool": "calendar_create_event",
        "message": "Calendar event created successfully.",
        "event": event
    }


# ============================================================
# GOOGLE CALENDAR - UPDATE / RESCHEDULE
# ============================================================

CALENDAR_UPDATE_TOOL = {
    "name": "calendar_update_event",
    "description": (
        "Update or reschedule an existing Google Calendar event. "
        "Use this when the user wants to change the event date, "
        "time, title, description, or location."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "event_id": {
                "type": "string",
                "description": "Google Calendar event ID."
            },
            "summary": {
                "type": "string",
                "description": "New event title."
            },
            "start_datetime": {
                "type": "string",
                "description": (
                    "New start datetime in ISO 8601 format "
                    "including timezone."
                )
            },
            "end_datetime": {
                "type": "string",
                "description": (
                    "New end datetime in ISO 8601 format "
                    "including timezone."
                )
            },
            "description": {
                "type": "string",
                "description": "New event description."
            },
            "location": {
                "type": "string",
                "description": "New event location."
            }
        },
        "required": [
            "event_id"
        ]
    }
}


def calendar_update_tool(
    event_id: str,
    summary: str | None = None,
    start_datetime: str | None = None,
    end_datetime: str | None = None,
    description: str | None = None,
    location: str | None = None
):
    event = update_event(
        event_id=event_id,
        summary=summary,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        description=description,
        location=location
    )

    return {
        "tool": "calendar_update_event",
        "message": "Calendar event updated successfully.",
        "event": event
    }


# ============================================================
# GOOGLE CALENDAR - DELETE
# ============================================================

def calendar_delete_tool(
    event_id: str
):
    result = delete_event(
        event_id=event_id
    )

    return {
        "tool": "calendar_delete_event",
        "message": "Calendar event deleted successfully.",
        "event_id": event_id
    }


CALENDAR_DELETE_TOOL = {
    "name": "calendar_delete_event",
    "description": (
        "Delete an event from the user's Google Calendar. "
        "Use this only when the user explicitly asks "
        "to delete or cancel a calendar event."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "event_id": {
                "type": "string",
                "description": "Google Calendar event ID."
            }
        },
        "required": [
            "event_id"
        ]
    }
}

# ============================================================
# MEET WITH ADMIN - CHECK AVAILABILITY
# ============================================================

MEETING_CHECK_AVAILABILITY_TOOL = {
    "name": "meeting_check_availability",
    "description": (
        "Check whether the user and Admin are available "
        "for a requested meeting time. "
        "Use this when the user asks whether they can meet "
        "Admin at a specific date and time. "
        "Do not create a meeting request with this tool."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "start_datetime": {
                "type": "string",
                "description": (
                    "Requested meeting start datetime "
                    "in ISO 8601 format including timezone."
                )
            },
            "duration": {
                "type": "integer",
                "description": "Meeting duration in minutes.",
                "default": 30
            }
        },
        "required": [
            "start_datetime"
        ]
    }
}


def meeting_check_availability_tool(
    db,
    user_id: int,
    start_datetime: str,
    duration: int = 30
):
    """
    Check whether Admin is available for a meeting.

    Availability is checked using:
    1. Admin Personal Memory
    2. Admin existing meetings
    3. Admin Google Calendar
    """
    # --------------------------------------------------------
    # 0. CHECK IF REQUESTED TIME IS IN THE PAST
    # --------------------------------------------------------

    from datetime import datetime
    from zoneinfo import ZoneInfo

    APP_TIMEZONE = ZoneInfo("Asia/Kolkata")

    try:
        requested_start = datetime.fromisoformat(
            start_datetime.replace("Z", "+00:00")
        )

        if requested_start.tzinfo is None:
            requested_start = requested_start.replace(
                tzinfo=APP_TIMEZONE
            )

        requested_start = requested_start.astimezone(
            APP_TIMEZONE
        )

    except (ValueError, TypeError):

        return {
            "tool": "meeting_check_availability",
            "success": False,
            "available": False,
            "message": "Invalid meeting date or time."
        }

    now = datetime.now(APP_TIMEZONE)

    if requested_start <= now:

        return {
            "tool": "meeting_check_availability",
            "success": True,
            "available": False,
            "admin_personal_available": None,
            "admin_calendar_available": None,
            "message": (
                "The requested meeting time has already passed. "
                "Please choose a future time."
            )
        }

    from .ai_service import (
        check_admin_personal_availability
    )

    # --------------------------------------------------------
    # 1. Check Admin Personal Memory
    # --------------------------------------------------------

    admin_personal_result = (
        check_admin_personal_availability(
            db=db,
            requested_start_datetime=start_datetime,
            duration_minutes=duration
        )
    )

    print(
        "DEBUG ADMIN PERSONAL RESULT:",
        admin_personal_result
    )

    if not admin_personal_result.get("available"):

        return {
            "tool": "meeting_check_availability",
            "success": True,
            "available": False,
            "admin_personal_available": False,
            "admin_calendar_available": None,

            # IMPORTANT:
            # Return Admin's personal availability memory
            # so the AI can answer general availability questions.
            "admin_memory": admin_personal_result.get(
                "admin_memory"
            ),

            "message": admin_personal_result.get(
                "message",
                "Admin is not available at that time."
            )
        }
   
    # --------------------------------------------------------
    # 2. Check Admin Google Calendar
    # --------------------------------------------------------

    admin_result = check_admin_availability(
        requested_datetime=start_datetime,
        duration_minutes=duration
    )

    print(
        "DEBUG ADMIN CALENDAR RESULT:",
        admin_result
    )

    return {
        "tool": "meeting_check_availability",
        "success": True,
        "available": bool(
            admin_result.get("available")
        ),
        "admin_personal_available": True,
        "admin_calendar_available": bool(
            admin_result.get("available")
        ),
        "slot": admin_result.get("slot"),
        "message": (
            "Admin is available."
            if admin_result.get("available")
            else
            "Admin is not available at that time."
        )
    }

# ============================================================
# MEET WITH ADMIN - REQUEST MEETING
# ============================================================

MEETING_REQUEST_TOOL = {
    "name": "meeting_request",
    "description": (
        "Create a pending meeting request with Admin. "
        "Use this only after the user explicitly confirms "
        "that they want to request the meeting. "
        "This does NOT directly create the Google Calendar "
        "event. Admin must approve the request first."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "start_datetime": {
                "type": "string",
                "description": (
                    "Meeting start datetime in ISO 8601 "
                    "format including timezone."
                )
            },
            "duration": {
                "type": "integer",
                "description": "Meeting duration in minutes.",
                "default": 30
            }
        },
        "required": [
            "start_datetime"
        ]
    }
}


def meeting_request_tool(
    db,
    user_id: int,
    user_name: str,
    user_email: str,
    start_datetime: str,
    duration: int = 30
):
    from datetime import datetime, timedelta
    from .ai_service import check_personal_availability

    # --------------------------------------------------------
    # CHECK USER PERSONAL AVAILABILITY
    # --------------------------------------------------------

    personal_result = check_personal_availability(
        db=db,
        user_id=user_id,
        requested_start_datetime=start_datetime,
        duration_minutes=duration
    )

    if not personal_result.get("available"):
        return {
            "tool": "meeting_request",
            "success": False,
            "status": None,
            "message": (
                "The requested time does not match "
                "your personal availability."
            )
        }

    # --------------------------------------------------------
    # CHECK ADMIN AVAILABILITY AGAIN
    # --------------------------------------------------------

    # admin_result = check_admin_availability(
    #     requested_datetime=start_datetime,
    #     duration_minutes=duration
    # )

    # if not admin_result.get("available"):
    #     return {
    #         "tool": "meeting_request",
    #         "success": False,
    #         "status": None,
    #         "message": (
    #             "The Admin is no longer available "
    #             "at that time."
    #         )
    #     }

    
    from .ai_service import check_admin_personal_availability

    admin_personal_result = check_admin_personal_availability(
        db=db,
        requested_start_datetime=start_datetime,
        duration_minutes=duration
    )

    if not admin_personal_result.get("available"):
        return {
            "tool": "meeting_request",
            "success": False,
            "status": None,
            "message": (
                "The Admin is no longer personally available "
                "at that time."
            )
        }


    # CHECK ADMIN GOOGLE CALENDAR AGAIN
    admin_result = check_admin_availability(
        requested_datetime=start_datetime,
        duration_minutes=duration
    )

    if not admin_result.get("available"):
        return {
            "tool": "meeting_request",
            "success": False,
            "status": None,
            "message": (
                "The Admin is no longer available "
                "at that time."
            )
        }

    # --------------------------------------------------------
    # CALCULATE END DATETIME
    # --------------------------------------------------------

    requested_start = datetime.fromisoformat(
        start_datetime
    )

    requested_end = (
        requested_start
        + timedelta(minutes=duration)
    )

    # --------------------------------------------------------
    # CREATE PENDING DATABASE REQUEST
    # --------------------------------------------------------

    meeting_request = MeetingRequest(
        user_id=user_id,
        user_name=user_name,
        user_email=user_email,
        start_datetime=start_datetime,
        end_datetime=requested_end.isoformat(),
        duration=duration,
        status="pending",
        admin_message=None,
        google_event_id=None,
    )

    db.add(meeting_request)
    db.commit()
    db.refresh(meeting_request)

    # --------------------------------------------------------
    # RETURN PENDING REQUEST
    # --------------------------------------------------------

    return {
        "tool": "meeting_request",
        "success": True,
        "status": "pending",

        "request": {
            "id": meeting_request.id,
            "user_name": meeting_request.user_name,
            "user_email": meeting_request.user_email,
            "start_datetime": meeting_request.start_datetime,
            "end_datetime": meeting_request.end_datetime,
            "duration": meeting_request.duration,
            "status": meeting_request.status,
        },

        "message": (
            "Meeting request sent successfully. "
            "It is now pending Admin approval."
        )
    }

# ============================================================
# MEET WITH ADMIN - MY MEETINGS
# ============================================================

MEETING_MY_MEETINGS_TOOL = {
    "name": "meeting_my_meetings",
    "description": (
        "Retrieve the user's meetings with Admin. "
        "Use this when the user asks about their Admin "
        "meetings, meeting requests, booking status, "
        "or whether a meeting has been approved."
    ),
    "parameters": {
        "type": "object",
        "properties": {},
        "required": []
    }
}


def meeting_my_meetings_tool(
    db,
    user_id: int
):
    requests = (
        db.query(MeetingRequest)
        .filter(
            MeetingRequest.user_id == user_id
        )
        .order_by(
            MeetingRequest.start_datetime.asc()
        )
        .all()
    )

    meetings = []

    for item in requests:
        meetings.append({
            "id": item.id,
            "title": "Meeting with Admin",
            "user_name": item.user_name,
            "user_email": item.user_email,
            "start_datetime": item.start_datetime,
            "end_datetime": item.end_datetime,
            "duration": item.duration,
            "status": item.status,
            "admin_message": item.admin_message,
            "google_event_id": item.google_event_id,
        })

    return {
        "tool": "meeting_my_meetings",
        "success": True,
        "meetings": meetings
    }