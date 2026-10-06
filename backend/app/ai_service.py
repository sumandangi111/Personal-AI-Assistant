import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from google import genai
from google.genai import types

from .agent_tools import (
    GMAIL_TOOL,
    GMAIL_READ_TOOL,
    GMAIL_DRAFT_TOOL,
    GMAIL_REPLY_PREPARE_TOOL,
    GMAIL_FORWARD_PREPARE_TOOL,
    CALENDAR_LIST_TOOL,
    CALENDAR_CREATE_TOOL,
    CALENDAR_DELETE_TOOL,
    CALENDAR_UPDATE_TOOL,
    MEETING_CHECK_AVAILABILITY_TOOL,
    MEETING_REQUEST_TOOL,
    MEETING_MY_MEETINGS_TOOL,
    gmail_search_tool,
    gmail_read_tool,
    gmail_draft_tool,
    calendar_delete_tool,
    calendar_update_tool,
    meeting_check_availability_tool,
    meeting_request_tool,
    meeting_my_meetings_tool,
)

from .calendar_service import (
    list_events,
    create_event,
)

from .models import PendingAction, User

def get_current_datetime_context():
    now = datetime.now(ZoneInfo("Asia/Kolkata"))

    return (
        f"Current date: {now.strftime('%A, %d %B %Y')}\n"
        f"Current time: {now.strftime('%I:%M %p')}\n"
        f"Timezone: Asia/Kolkata"
    )

# ============================================================
# GEMINI CONFIGURATION
# ============================================================

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.5-flash-lite"
)

client = genai.Client(
    api_key=GEMINI_API_KEY
)


# ============================================================
# PERSONAL MEETING AVAILABILITY
# ============================================================

def check_personal_availability(
    db,
    user_id: int,
    requested_start_datetime: str,
    duration_minutes: int = 30,
    exclude_request_id: int = None
):
    """
    Check whether the user already has a conflicting
    pending or approved meeting.
    """

    from datetime import timedelta
    from .models import MeetingRequest

    try:
        requested_start = datetime.fromisoformat(
            requested_start_datetime
        )

        requested_end = (
            requested_start
            + timedelta(minutes=duration_minutes)
        )

    except (ValueError, TypeError):
        return {
            "available": False,
            "message": "Invalid meeting date or time."
        }

    existing_requests = (
        db.query(MeetingRequest)
        .filter(
            MeetingRequest.user_id == user_id,
            MeetingRequest.status.in_([
                "pending",
                "approved"
            ])
        )
        .all()
    )

    for existing in existing_requests:
        if (
            exclude_request_id is not None
            and existing.id == exclude_request_id
        ):
            continue

        try:
            existing_start = datetime.fromisoformat(
                existing.start_datetime
            )

            existing_end = datetime.fromisoformat(
                existing.end_datetime
            )

        except (ValueError, TypeError):
            continue

        # Check for overlapping meetings
        if (
            requested_start < existing_end
            and requested_end > existing_start
        ):
            return {
                "available": False,
                "message": (
                    "You already have a meeting during "
                    "the requested time."
                )
            }

    return {
        "available": True,
        "message": "You are personally available."
    }
# ============================================================
# ADMIN PERSONAL AVAILABILITY
# ============================================================

def check_admin_personal_availability(
    db,
    requested_start_datetime: str,
    duration_minutes: int = 30
):
    """
    Check Admin's personal availability from stored memory.

    IMPORTANT:
    This check happens BEFORE Google Calendar.

    The Admin's availability is stored in the Memory table.
    """

    from datetime import timedelta
    from .models import User, Memory

    ADMIN_TIMEZONE = ZoneInfo("Asia/Kolkata")

    # --------------------------------------------------------
    # Parse requested datetime
    # --------------------------------------------------------

    try:
        requested_start = datetime.fromisoformat(
            requested_start_datetime
        )

        if requested_start.tzinfo is None:
            requested_start = requested_start.replace(
                tzinfo=ADMIN_TIMEZONE
            )

        requested_start = requested_start.astimezone(
            ADMIN_TIMEZONE
        )

        requested_end = (
            requested_start
            + timedelta(minutes=duration_minutes)
        )

    except (ValueError, TypeError):

        return {
            "available": False,
            "message": "Invalid meeting date or time."
        }

    # --------------------------------------------------------
    # Find Admin
    # --------------------------------------------------------

    admin_user = (
        db.query(User)
        .filter(User.role == "admin")
        .first()
    )

    if admin_user is None:

        return {
            "available": False,
            "message": "Admin account was not found."
        }

    # --------------------------------------------------------
    # Get Admin memories
    # --------------------------------------------------------

    memories = (
        db.query(Memory)
        .filter(
            Memory.user_id == admin_user.id
        )
        .all()
    )

    # --------------------------------------------------------
    # Find availability memory
    # --------------------------------------------------------

    availability_memory = None

    for memory in memories:

        key = str(memory.key or "").lower().strip()

        if key in [
            "availability",
            "admin_availability",
            "personal_availability",
            "working_hours",
            "work_hours"
        ]:

            availability_memory = memory
            break

    # --------------------------------------------------------
    # No availability memory
    # --------------------------------------------------------

    if availability_memory is None:

        return {
            "available": False,
            "message": (
                "Admin personal availability is not configured "
                "in memory."
            )
        }

    availability_value = str(
        availability_memory.value or ""
    ).strip()

    if not availability_value:

        return {
            "available": False,
            "message": (
                "Admin personal availability is empty."
            )
        }

    # --------------------------------------------------------
    # Ask Gemini to interpret the stored availability
    # --------------------------------------------------------

    prompt = f"""
Determine whether the Admin is personally available
for the requested meeting time.

Admin availability from personal memory:
{availability_value}

Requested start:
{requested_start.isoformat()}

Requested end:
{requested_end.isoformat()}

Timezone:
Asia/Kolkata

Return ONLY valid JSON.

Format:

{{
    "available": true,
    "message": "Admin is personally available."
}}

or:

{{
    "available": false,
    "message": "Admin is not personally available at this time."
}}

Rules:

- Use ONLY the Admin availability provided above.
- Do not use Google Calendar.
- Do not invent availability.
- Do not assume availability if the memory is unclear.
- Consider the requested start and end time.
"""

    try:

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )

        text = response.text.strip()

        # Remove markdown JSON fences if Gemini adds them
        if text.startswith("```"):

            lines = text.splitlines()

            if lines:
                lines = lines[1:]

            if (
                lines
                and lines[-1].strip() == "```"
            ):
                lines = lines[:-1]

            text = "\n".join(lines)

        result = json.loads(text)

        available = bool(
            result.get("available", False)
        )

        message = result.get(
            "message",
            (
                "Admin is personally available."
                if available
                else
                "Admin is not personally available."
            )
        )

        return {
            "available": available,
            "message": message,
            "admin_memory": availability_value
        }

    except Exception as e:

        print(
            "ADMIN PERSONAL AVAILABILITY ERROR:",
            str(e)
        )

        return {
            "available": False,
            "message": (
                "Unable to determine Admin's personal "
                "availability from memory."
            )
        }
# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are a helpful Personal AI Assistant.

Your job is to behave like a natural, general-purpose personal
assistant.

You can help with:
- General questions
- Explanations
- Writing
- Planning
- Conversations
- Personal context and memory
- Gmail
- Google Calendar
- Other tasks supported by the available tools

IMPORTANT:

Do not unnecessarily mention Gmail, Google Calendar, tools,
APIs, or internal implementation details.

Only use or mention a specific service when it is relevant
to the user's request.

For normal conversation, behave like a normal AI assistant.

For example, if the user says:

"Hello"

Respond naturally, such as:

"Hello! How can I help you today?"

Do NOT respond with:

"How can I help you with your Gmail or Google Calendar today?"

unless the user is specifically asking about Gmail or Calendar.

------------------------------------------------------------
GENERAL BEHAVIOR
------------------------------------------------------------

Be natural, concise, friendly, and helpful.

Understand the user's intent before deciding whether a tool
is necessary.

Do not call a tool when a normal conversational response
is sufficient.

Do not expose internal tool names or implementation details
unless the user specifically asks.

Never pretend that an action was completed if the required
tool did not successfully complete it.

When a tool fails, clearly explain that the requested action
could not be completed.

------------------------------------------------------------
CURRENT DATE AND TIME
------------------------------------------------------------

The current date and time will be provided dynamically.

Use this information when interpreting:

- today
- tomorrow
- yesterday
- next week
- next Monday
- this Friday
- relative dates
- relative times

For Google Calendar, use:

Asia/Kolkata

------------------------------------------------------------
GMAIL
------------------------------------------------------------

Use Gmail tools only when the user asks about email.

Use `gmail_search` when the user asks about:

- emails
- inbox
- unread emails
- emails from someone
- emails from an organization
- emails about a specific topic
- latest email
- recent email

Use `gmail_read` when the user asks to:

- read an email
- open an email
- inspect an email
- summarize an email

Use `gmail_draft` when the user explicitly asks to:

- draft an email
- prepare an email
- write an email draft

Do NOT send an email when the user only asks for a draft.

Use `gmail_send_prepare` when the user explicitly wants
to send an email.

The actual sending action requires explicit user confirmation.

Use `gmail_reply_prepare` when the user explicitly wants
to reply to an existing email.

Before replying:

1. Identify the correct email.
2. Obtain its Gmail message ID.
3. Prepare the reply using `gmail_reply_prepare`.
4. Do not send the reply immediately.
5. Wait for explicit user confirmation.

The actual reply requires explicit confirmation.

Use `gmail_forward_prepare` when the user explicitly wants
to forward an existing email.

Before forwarding:

1. Identify the correct email.
2. Obtain its Gmail message ID.
3. Determine the recipient email address.
4. Prepare the forward using `gmail_forward_prepare`.
5. Do not send the forward immediately.
6. Wait for explicit user confirmation.

The actual forward requires explicit confirmation.

Never claim that an email was sent unless the send action
actually succeeded.

Never claim that a reply was sent unless the reply action
actually succeeded.

Never claim that an email was forwarded unless the forward
action actually succeeded.

------------------------------------------------------------
GOOGLE CALENDAR
------------------------------------------------------------

Use Calendar tools only when the user asks about their
calendar, schedule, meetings, appointments, or events.

Use `calendar_list_events` when the user asks about:

- upcoming events
- meetings
- appointments
- schedule
- calendar events
- events on a specific date

Use `calendar_create_event` when the user explicitly asks to:

- create an event
- schedule a meeting
- add an appointment
- add something to the calendar

Before creating an event:

- Determine the correct date.
- Determine the correct start time.
- Determine the correct end time.
- Use Asia/Kolkata for Indian time.
- Use the current date/time context when interpreting
  relative dates such as "tomorrow".

Never claim an event was created unless the tool succeeds.

------------------------------------------------------------
CALENDAR UPDATE / RESCHEDULE
------------------------------------------------------------

Use `calendar_update_event` when the user explicitly asks to:

- update an event
- change an event title
- reschedule an event
- change an event date
- change an event time
- change an event location
- change an event description

Before updating an event:

1. Identify the correct event.
2. Obtain its Google Calendar event ID.
3. Call `calendar_update_event` using that ID.

If the user gives only an event name, first use
`calendar_list_events` to find the matching event and
obtain its event ID.

For rescheduling:

- Determine the correct new date.
- Determine the correct new start time.
- Determine the correct new end time.
- Use Asia/Kolkata timezone.
- Use the current date/time context when interpreting
  relative dates such as "tomorrow" or "next Monday".

Never claim an event was updated unless the update
tool successfully completes.

------------------------------------------------------------
CALENDAR DELETE
------------------------------------------------------------

Use `calendar_delete_event` when the user explicitly asks to:

- delete an event
- cancel an event
- remove an event from the calendar

Before deleting an event:

1. Identify the correct event.
2. Obtain the Google Calendar event ID.
3. Call `calendar_delete_event` using that ID.

If the user gives only an event name, first use
`calendar_list_events` to find the matching event and
obtain its event ID.

Never claim an event was deleted unless the delete tool
successfully completes.

------------------------------------------------------------
MEET WITH ADMIN - AI CONVERSATIONAL WORKFLOW
------------------------------------------------------------

The application provides a conversational workflow for
scheduling meetings with Admin.

A meeting with Admin is NOT the same as creating a normal
Google Calendar event.

Use ONLY these tools for meetings with Admin:

- meeting_check_availability
- meeting_request
- meeting_my_meetings

------------------------------------------------------------
MEETING INTENT
------------------------------------------------------------

Recognize natural meeting requests such as:

- "Can I meet Admin tomorrow at 7 PM?"
- "I want to talk to Admin tomorrow evening."
- "Is Admin free at 5 PM on Monday?"
- "Can I schedule a meeting with Admin?"
- "Book me a meeting with Admin."
- "When can I meet Admin tomorrow?"
- "I need a 1 hour meeting with Admin."
- "Is Admin available tomorrow at 6:30 PM?"

Do not require the user to use a specific sentence format.

Understand natural language and conversational follow-up
messages.

------------------------------------------------------------
MEETING INFORMATION
------------------------------------------------------------

A meeting normally requires:

1. Date
2. Start time
3. Duration

Default duration:

30 minutes

If the user provides a duration, use it.

Examples:

"for 1 hour" → 60 minutes

"for 45 minutes" → 45 minutes

"for 90 minutes" → 90 minutes

If the user does not provide a duration, use 30 minutes.

------------------------------------------------------------
RELATIVE DATE AND TIME
------------------------------------------------------------

Use the dynamically provided current date and time.

Interpret natural expressions such as:

- today
- tomorrow
- tonight
- tomorrow morning
- tomorrow afternoon
- tomorrow evening
- Monday
- next Monday
- this Friday
- next week

Use Asia/Kolkata timezone.

Convert the interpreted date/time into an ISO 8601
datetime including the timezone before calling the meeting
availability tool.

Do NOT invent a date.

------------------------------------------------------------
MISSING INFORMATION
------------------------------------------------------------

If the user wants to meet Admin but has not provided a date:

Ask for the date.

Example:

User:
"I want to meet Admin."

Assistant:
"Sure. What day would you like to meet Admin?"

If the date is known but the time is missing:

Ask for the time.

Example:

User:
"Tomorrow."

Assistant:
"What time would you prefer tomorrow?"

If the user provides a date and approximate period but no
specific time:

Example:

User:
"Tomorrow evening."

Assistant:
"What time tomorrow evening would you prefer?"

Do not call the availability tool until the required
meeting date and start time are known.

------------------------------------------------------------
CHECK AVAILABILITY
------------------------------------------------------------

Once the required date and time are known:

1. Determine the meeting duration.
2. Convert the requested datetime to Asia/Kolkata ISO format.
3. Call meeting_check_availability.

NEVER claim that Admin is available without actually calling
meeting_check_availability.

NEVER assume that a time is available.

The backend result is the source of truth.

------------------------------------------------------------
AVAILABLE SLOT
------------------------------------------------------------

If meeting_check_availability returns available=true:

Tell the user that the requested slot is available.

Then ask for explicit confirmation.

Example:

"Yes, Admin is available tomorrow from 7:00 PM to
7:30 PM. Would you like me to send the meeting request?"

Do NOT call meeting_request yet.

Wait for the user's confirmation.

------------------------------------------------------------
USER CONFIRMATION
------------------------------------------------------------

The user must explicitly confirm before creating a meeting
request.

Valid confirmations include natural expressions such as:

- yes
- yes please
- sure
- okay
- okay, book it
- book it
- schedule it
- go ahead
- please schedule it
- that works
- that time works
- confirm
- confirmed

If the user clearly confirms the previously discussed
meeting slot:

Call meeting_request using the previously confirmed
start datetime and duration.

Do NOT ask the user to repeat information that is already
known from the conversation.

------------------------------------------------------------
IMPORTANT CONFIRMATION RULE
------------------------------------------------------------

Do NOT interpret every "yes" as permission to create a
meeting.

Only interpret "yes" as confirmation when the immediately
preceding assistant message was asking for confirmation of
a specific meeting request.

Example:

Assistant:
"Admin is available tomorrow at 7 PM for 30 minutes.
Would you like me to send the request?"

User:
"Yes."

→ Call meeting_request.

But:

User:
"Hello"

Assistant:
"Hello! How can I help?"

User:
"Yes"

→ Do NOT create a meeting.

------------------------------------------------------------
UNAVAILABLE SLOT
------------------------------------------------------------

UNAVAILABLE SLOT:
- If the meeting_check_availability tool returns available=false, explain that the requested time is unavailable.
- If the tool result contains an alternative slot, tell the user about that alternative.
- If the tool result contains admin_memory, use it to explain Admin's personal availability/working hours.
- If the user asks general questions such as:
  "When is Admin available?"
  "What time can I meet Admin?"
  "When can I schedule a meeting with Admin?"
  and admin_memory is already available from the tool result or conversation context, answer directly from that information.
- Do NOT call meeting_check_availability repeatedly just to answer a general availability question.
- Only call meeting_check_availability again when the user provides a specific date and time that needs to be checked.
- Never invent Admin's availability.
------------------------------------------------------------
PERSONAL AVAILABILITY
------------------------------------------------------------

The meeting availability tool checks both:

- the user's existing meeting availability
- Admin's availability

If the user already has a conflicting meeting:

Explain that the user has a conflict.

Do not create a meeting request for an overlapping slot.

------------------------------------------------------------
CREATE MEETING REQUEST
------------------------------------------------------------

Only call meeting_request after explicit user confirmation.

The meeting_request tool creates a PENDING request.

It does NOT immediately create a Google Calendar event.

After successful meeting_request:

Say something similar to:

"Your meeting request has been sent to Admin. It is
currently pending approval."

Do NOT say:

"Your meeting is confirmed."

Do NOT say:

"Your meeting has been scheduled."

unless the actual meeting status returned by the system is
approved.

------------------------------------------------------------
ADMIN APPROVAL
------------------------------------------------------------

The workflow is:

User requests meeting
        ↓
AI checks availability
        ↓
AI asks for confirmation
        ↓
User confirms
        ↓
meeting_request
        ↓
PENDING
        ↓
Admin reviews request
        ↓
Admin approves or rejects
        ↓
If approved:
Google Calendar event is created

Therefore:

pending ≠ approved

approved = confirmed

rejected = not approved

------------------------------------------------------------
FOLLOW-UP CONVERSATION
------------------------------------------------------------

Maintain context across messages.

Example:

User:
"I want to meet Admin tomorrow."

Assistant:
"Sure. What time would you prefer?"

User:
"7 PM."

Assistant:
"Let me check Admin's availability."

→ meeting_check_availability

Assistant:
"7:00 PM–7:30 PM is available. Would you like me to
send the request?"

User:
"Yes."

→ meeting_request

Assistant:
"Your meeting request has been sent to Admin. It is
currently pending approval."

Do not ask the user to repeat "tomorrow" or "7 PM" when
that information already exists in the conversation.

------------------------------------------------------------
MY MEETINGS
------------------------------------------------------------

Use meeting_my_meetings when the user asks:

- What meetings do I have?
- Show my meetings
- Show my bookings
- My Admin meetings
- Is my meeting approved?
- What is the status of my meeting?
- Did Admin approve my meeting?
- Do I have a meeting with Admin?
- What meetings are pending?
- What meetings were rejected?

Use the actual data returned by meeting_my_meetings.

Never invent meeting information.

------------------------------------------------------------
IMPORTANT SAFETY RULE
------------------------------------------------------------

Never:

- invent Admin availability
- invent a meeting
- create a meeting without confirmation
- claim a pending request is approved
- create a Google Calendar event directly for an Admin
  meeting
- bypass the meeting_request workflow
- bypass Admin approval

The meeting tools and backend are the source of truth.
------------------------------------------------------------
MY MEETINGS
------------------------------------------------------------

Use meeting_my_meetings when the user asks:

- What meetings do I have?
- Show my meetings
- My Admin meetings
- Is my meeting approved?
- What is the status of my meeting?
- Do I have a meeting with Admin?

Use the actual meeting status returned by the tool.

Possible statuses:

- pending
- approved
- rejected

Never invent meeting information.

------------------------------------------------------------
TOOL EXECUTION
------------------------------------------------------------

After receiving a tool result, continue processing the
conversation if another tool is needed.

Do not stop after the first tool call when the user's
request requires multiple steps.

For example:

User:
"Delete my AI Agent Development event."

Possible workflow:

1. calendar_list_events
2. Find "AI Agent Development"
3. Get event ID
4. calendar_delete_event
5. Return final response

For an update request:

User:
"Move my Team Meeting to 2 PM."

Possible workflow:

1. calendar_list_events
2. Find "Team Meeting"
3. Get event ID
4. calendar_update_event
5. Return final response

For a Gmail reply:

User:
"Reply to my Google email saying I'll check it tomorrow."

Possible workflow:

1. gmail_search
2. Identify the correct email
3. gmail_read if necessary
4. Get the Gmail message ID
5. gmail_reply_prepare
6. Wait for user confirmation

Only provide the final answer after all required tools
have completed or the action is waiting for confirmation.
"""


# ============================================================
# BASIC GEMINI RESPONSE
# ============================================================

def generate_ai_response(messages):
    """
    Generate a normal Gemini response without tools.
    """

    current_datetime = get_current_datetime_context()

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=messages,
        config={
            "system_instruction": (
                SYSTEM_PROMPT
                + "\n\n"
                + current_datetime
            )
        }
    )

    return response.text


# ============================================================
# GMAIL SEND PREPARE TOOL
# ============================================================

GMAIL_SEND_PREPARE_TOOL = {
    "name": "gmail_send_prepare",
    "description": (
        "Prepare an email to be sent through Gmail. "
        "Use this tool only when the user explicitly "
        "asks to send an email. "
        "The email must still require explicit user "
        "confirmation before the actual send action."
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
# GMAIL SEND PREPARE
# ============================================================

def gmail_send_prepare(
    to: str,
    subject: str,
    body: str,
    db=None,
    user_id=None
):
    """
    Create a pending Gmail send action.

    The actual email is not sent here.
    """

    if db is None or user_id is None:
        return {
            "tool": "gmail_send_prepare",
            "error": (
                "Database session and user ID are required "
                "for email confirmation."
            )
        }

    pending_action = PendingAction(
        user_id=user_id,
        action_type="gmail_send",
        action_data=json.dumps({
            "to": to,
            "subject": subject,
            "body": body
        }),
        status="pending"
    )

    db.add(pending_action)
    db.commit()
    db.refresh(pending_action)

    return {
        "tool": "gmail_send_prepare",
        "message": (
            "Email prepared successfully. "
            "User confirmation is required before sending."
        ),
        "action_id": pending_action.id,
        "to": to,
        "subject": subject
    }


# ============================================================
# GMAIL REPLY PREPARE
# ============================================================

def gmail_reply_prepare(
    message_id: str,
    body: str,
    db=None,
    user_id=None
):
    """
    Create a pending Gmail reply action.

    The actual reply is NOT sent here.
    It will be sent only after explicit confirmation.
    """

    if db is None or user_id is None:
        return {
            "tool": "gmail_reply_prepare",
            "error": (
                "Database session and user ID are required "
                "for email confirmation."
            )
        }

    pending_action = PendingAction(
        user_id=user_id,
        action_type="gmail_reply",
        action_data=json.dumps({
            "message_id": message_id,
            "body": body
        }),
        status="pending"
    )

    db.add(pending_action)
    db.commit()
    db.refresh(pending_action)

    return {
        "tool": "gmail_reply_prepare",
        "message": (
            "Reply prepared successfully. "
            "User confirmation is required before sending."
        ),
        "action_id": pending_action.id,
        "message_id": message_id
    }


# ============================================================
# GMAIL FORWARD PREPARE
# ============================================================

def gmail_forward_prepare(
    message_id: str,
    to: str,
    body: str = "",
    db=None,
    user_id=None
):
    """
    Create a pending Gmail forward action.

    The actual forward is NOT sent here.
    It will be sent only after explicit confirmation.
    """

    if db is None or user_id is None:
        return {
            "tool": "gmail_forward_prepare",
            "error": (
                "Database session and user ID are required "
                "for email confirmation."
            )
        }

    pending_action = PendingAction(
        user_id=user_id,
        action_type="gmail_forward",
        action_data=json.dumps({
            "message_id": message_id,
            "to": to,
            "body": body
        }),
        status="pending"
    )

    db.add(pending_action)
    db.commit()
    db.refresh(pending_action)

    return {
        "tool": "gmail_forward_prepare",
        "message": (
            "Email forward prepared successfully. "
            "User confirmation is required before sending."
        ),
        "action_id": pending_action.id,
        "message_id": message_id,
        "to": to
    }


# ============================================================
# GEMINI TOOL CALLING
# ============================================================

def generate_ai_response_with_tools(
    messages,
    db=None,
    user_id=None,
    memories=None,
    conversation_summary=None,
    max_tool_calls=5
):
    """
    Generate a Gemini response with Gmail and Calendar tools.
    """

    tool_config = [
        {
            "function_declarations": [
                GMAIL_TOOL,
                GMAIL_READ_TOOL,
                GMAIL_DRAFT_TOOL,
                GMAIL_SEND_PREPARE_TOOL,
                GMAIL_REPLY_PREPARE_TOOL,
                GMAIL_FORWARD_PREPARE_TOOL,

                CALENDAR_LIST_TOOL,
                CALENDAR_CREATE_TOOL,
                CALENDAR_UPDATE_TOOL,
                CALENDAR_DELETE_TOOL,

                MEETING_CHECK_AVAILABILITY_TOOL,
                MEETING_REQUEST_TOOL,
                MEETING_MY_MEETINGS_TOOL
            ]
        }
    ]

    current_messages = list(messages)

    current_datetime = get_current_datetime_context()

    # ========================================================
    # PERSONAL MEMORY CONTEXT
    # ========================================================

    memory_context = ""

    if memories:
        memory_lines = []

        for memory in memories:
            if isinstance(memory, dict):
                key = memory.get("key")
                value = memory.get("value")

                if key and value is not None:
                    memory_lines.append(
                        f"- {key}: {value}"
                    )

        if memory_lines:
            memory_context = (
                "\n\nKNOWN USER MEMORY:\n"
                + "\n".join(memory_lines)
                + "\n\n"
                "MEMORY RULES:\n"
                "- Use known user memory when it directly answers the user's question.\n"
                "- Prefer known user memory over guessing.\n"
                "- Do not call Gmail, Calendar, or meeting tools just to answer information already present in memory.\n"
                "- Do not say that memory is unavailable when relevant memory is provided above.\n"
                "- Treat the memory as information about the current user.\n"
            )

    # ========================================================
    # CONVERSATION SUMMARY CONTEXT
    # ========================================================

    summary_context = ""

    if conversation_summary:
        summary_context = (
            "\n\nCONVERSATION SUMMARY:\n"
            + conversation_summary
        )

    system_instruction = (
        SYSTEM_PROMPT
        + "\n\n"
        + current_datetime
        + memory_context
        + summary_context
    )

    for _ in range(max_tool_calls):

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=current_messages,
            config={
                "system_instruction": system_instruction,
                "tools": tool_config
            }
        )

        # ----------------------------------------------------
        # Find a function call
        # ----------------------------------------------------

        function_call = None

        if response.candidates:

            candidate = response.candidates[0]

            if candidate.content:

                for part in candidate.content.parts:

                    if getattr(
                        part,
                        "function_call",
                        None
                    ):

                        function_call = (
                            part.function_call
                        )

                        break

        # ----------------------------------------------------
        # No tool call = final response
        # ----------------------------------------------------

        if function_call is None:

            return response.text

        # ----------------------------------------------------
        # Extract tool information
        # ----------------------------------------------------

        tool_name = function_call.name

        tool_args = dict(
            function_call.args or {}
        )

        # ----------------------------------------------------
        # Execute tool
        # ----------------------------------------------------

        tool_result = None

        # ====================================================
        # GMAIL SEARCH
        # ====================================================

        if tool_name == "gmail_search":

            query = tool_args.get(
                "query",
                "in:inbox"
            )

            max_results = tool_args.get(
                "max_results",
                5
            )

            try:

                tool_result = gmail_search_tool(
                    query=query,
                    max_results=max_results
                )

            except Exception as e:

                tool_result = {
                    "error": (
                        "Gmail search failed: "
                        f"{str(e)}"
                    )
                }

        # ====================================================
        # GMAIL READ
        # ====================================================

        elif tool_name == "gmail_read":

            message_id = tool_args.get(
                "message_id"
            )

            if not message_id:

                tool_result = {
                    "error": "Gmail message ID is required."
                }

            else:

                try:

                    tool_result = gmail_read_tool(
                        message_id=message_id
                    )

                except Exception as e:

                    tool_result = {
                        "error": (
                            "Gmail read failed: "
                            f"{str(e)}"
                        )
                    }

        # ====================================================
        # GMAIL DRAFT
        # ====================================================

        elif tool_name == "gmail_draft":

            to = tool_args.get("to")
            subject = tool_args.get("subject")
            body = tool_args.get("body")

            if not to or not subject or not body:

                tool_result = {
                    "error": (
                        "Recipient, subject, and body "
                        "are required."
                    )
                }

            else:

                try:

                    tool_result = gmail_draft_tool(
                        to=to,
                        subject=subject,
                        body=body
                    )

                except Exception as e:

                    tool_result = {
                        "error": (
                            "Gmail draft creation failed: "
                            f"{str(e)}"
                        )
                    }

        # ====================================================
        # GMAIL SEND PREPARE
        # ====================================================

        elif tool_name == "gmail_send_prepare":

            to = tool_args.get("to")
            subject = tool_args.get("subject")
            body = tool_args.get("body")

            if not to or not subject or not body:

                tool_result = {
                    "error": (
                        "Recipient, subject, and body "
                        "are required."
                    )
                }

            else:

                try:

                    tool_result = gmail_send_prepare(
                        to=to,
                        subject=subject,
                        body=body,
                        db=db,
                        user_id=user_id
                    )

                except Exception as e:

                    tool_result = {
                        "error": (
                            "Email preparation failed: "
                            f"{str(e)}"
                        )
                    }

        # ====================================================
        # GMAIL REPLY PREPARE
        # ====================================================

        elif tool_name == "gmail_reply_prepare":

            message_id = tool_args.get(
                "message_id"
            )

            body = tool_args.get(
                "body"
            )

            if not message_id:

                tool_result = {
                    "error": (
                        "Gmail message ID is required."
                    )
                }

            elif not body:

                tool_result = {
                    "error": (
                        "Reply body is required."
                    )
                }

            else:

                try:

                    tool_result = gmail_reply_prepare(
                        message_id=message_id,
                        body=body,
                        db=db,
                        user_id=user_id
                    )

                except Exception as e:

                    tool_result = {
                        "error": (
                            "Gmail reply preparation failed: "
                            f"{str(e)}"
                        )
                    }

        # ====================================================
        # GMAIL FORWARD PREPARE
        # ====================================================

        elif tool_name == "gmail_forward_prepare":

            message_id = tool_args.get(
                "message_id"
            )

            to = tool_args.get(
                "to"
            )

            body = tool_args.get(
                "body",
                ""
            )

            if not message_id:

                tool_result = {
                    "error": (
                        "Gmail message ID is required."
                    )
                }

            elif not to:

                tool_result = {
                    "error": (
                        "Forward recipient email address "
                        "is required."
                    )
                }

            else:

                try:

                    tool_result = gmail_forward_prepare(
                        message_id=message_id,
                        to=to,
                        body=body,
                        db=db,
                        user_id=user_id
                    )

                except Exception as e:

                    tool_result = {
                        "error": (
                            "Gmail forward preparation failed: "
                            f"{str(e)}"
                        )
                    }

        # ====================================================
        # CALENDAR LIST
        # ====================================================

        elif tool_name == "calendar_list_events":

            max_results = tool_args.get(
                "max_results",
                10
            )

            try:

                events = list_events(
                    max_results=max_results
                )

                tool_result = {
                    "tool": "calendar_list_events",
                    "events": events
                }

            except Exception as e:

                tool_result = {
                    "error": (
                        "Calendar event listing failed: "
                        f"{str(e)}"
                    )
                }

        # ====================================================
        # CALENDAR CREATE
        # ====================================================

        elif tool_name == "calendar_create_event":

            summary = tool_args.get(
                "summary"
            )

            start_datetime = tool_args.get(
                "start_datetime"
            )

            end_datetime = tool_args.get(
                "end_datetime"
            )

            description = tool_args.get(
                "description",
                ""
            )

            location = tool_args.get(
                "location",
                ""
            )

            if not summary:

                tool_result = {
                    "error": "Event title is required."
                }

            elif not start_datetime:

                tool_result = {
                    "error": (
                        "Event start datetime is required."
                    )
                }

            elif not end_datetime:

                tool_result = {
                    "error": (
                        "Event end datetime is required."
                    )
                }

            else:

                try:

                    event = create_event(
                        summary=summary,
                        start_datetime=start_datetime,
                        end_datetime=end_datetime,
                        description=description,
                        location=location
                    )

                    tool_result = {
                        "tool": "calendar_create_event",
                        "message": (
                            "Calendar event created "
                            "successfully."
                        ),
                        "event": event
                    }

                except Exception as e:

                    tool_result = {
                        "error": (
                            "Calendar event creation failed: "
                            f"{str(e)}"
                        )
                    }

        # ====================================================
        # CALENDAR UPDATE
        # ====================================================

        elif tool_name == "calendar_update_event":

            event_id = tool_args.get(
                "event_id"
            )

            summary = tool_args.get(
                "summary"
            )

            start_datetime = tool_args.get(
                "start_datetime"
            )

            end_datetime = tool_args.get(
                "end_datetime"
            )

            description = tool_args.get(
                "description"
            )

            location = tool_args.get(
                "location"
            )

            if not event_id:

                tool_result = {
                    "error": (
                        "Calendar event ID is required."
                    )
                }

            else:

                try:

                    tool_result = calendar_update_tool(
                        event_id=event_id,
                        summary=summary,
                        start_datetime=start_datetime,
                        end_datetime=end_datetime,
                        description=description,
                        location=location
                    )

                except Exception as e:

                    tool_result = {
                        "error": (
                            "Calendar event update failed: "
                            f"{str(e)}"
                        )
                    }

        # ====================================================
        # CALENDAR DELETE
        # ====================================================

        elif tool_name == "calendar_delete_event":

            event_id = tool_args.get(
                "event_id"
            )

            if not event_id:

                tool_result = {
                    "error": (
                        "Calendar event ID is required."
                    )
                }

            else:

                try:

                    tool_result = calendar_delete_tool(
                        event_id=event_id
                    )

                except Exception as e:

                    tool_result = {
                        "error": (
                            "Calendar event deletion failed: "
                            f"{str(e)}"
                        )
                    }

        # ====================================================
        # MEETING - CHECK AVAILABILITY
        # ====================================================

        elif tool_name == "meeting_check_availability":

            start_datetime = tool_args.get(
                "start_datetime"
            )

            duration = tool_args.get(
                "duration",
                30
            )

            if not start_datetime:

                tool_result = {
                    "error": (
                        "Meeting start datetime is required."
                    )
                }

            elif db is None or user_id is None:

                tool_result = {
                    "error": (
                        "Database session and user ID are required "
                        "to check meeting availability."
                    )
                }

            else:

                try:

                    tool_result = meeting_check_availability_tool(
                        db=db,
                        user_id=user_id,
                        start_datetime=start_datetime,
                        duration=duration
                    )

                # except Exception as e:

                #     tool_result = {
                #         "error": (
                #             "Meeting availability check failed: "
                #             f"{str(e)}"
                #         )
                #     }
                 
                except Exception as e:
                    import traceback

                    print("\n========== MEETING AVAILABILITY ERROR ==========")
                    print(str(e))
                    traceback.print_exc()
                    print("================================================\n")

                    tool_result = {
                        "error": (
                            f"Meeting availability check failed: {str(e)}"
                        )
                    }
        # ====================================================
        # MEETING - REQUEST
        # ====================================================

        elif tool_name == "meeting_request":

            start_datetime = tool_args.get(
                "start_datetime"
            )

            duration = tool_args.get(
                "duration",
                30
            )

            if not start_datetime:

                tool_result = {
                    "error": (
                        "Meeting start datetime is required."
                    )
                }

            elif db is None or user_id is None:

                tool_result = {
                    "error": (
                        "Database session and user ID are required "
                        "to create a meeting request."
                    )
                }

            else:

                try:

                    current_user = (
                        db.query(User)
                        .filter(User.id == user_id)
                        .first()
                    )

                    if current_user is None:

                        tool_result = {
                            "error": "Current user was not found."
                        }

                    else:

                        tool_result = meeting_request_tool(
                            db=db,
                            user_id=user_id,
                            user_name=current_user.name,
                            user_email=current_user.email,
                            start_datetime=start_datetime,
                            duration=duration
                        )

                except Exception as e:

                    tool_result = {
                        "error": (
                            "Meeting request creation failed: "
                            f"{str(e)}"
                        )
                    }

        # ====================================================
        # MEETING - MY MEETINGS
        # ====================================================

        elif tool_name == "meeting_my_meetings":

            if db is None or user_id is None:

                tool_result = {
                    "error": (
                        "Database session and user ID are required "
                        "to retrieve meetings."
                    )
                }

            else:

                try:

                    tool_result = meeting_my_meetings_tool(
                        db=db,
                        user_id=user_id
                    )

                except Exception as e:

                    tool_result = {
                        "error": (
                            "Meeting retrieval failed: "
                            f"{str(e)}"
                        )
                    }

        # ====================================================
        # UNKNOWN TOOL
        # ====================================================

        else:

            tool_result = {
                "error": (
                    f"Unknown tool: {tool_name}"
                )
            }

        # ----------------------------------------------------
        # Preserve Gemini response content
        # ----------------------------------------------------

        if response.candidates:

            current_messages.append(
                response.candidates[0].content
            )

        # ----------------------------------------------------
        # Add function response
        # ----------------------------------------------------

        current_messages.append(
            types.Content(
                role="user",
                parts=[
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=tool_name,
                            response=tool_result
                        )
                    )
                ]
            )
        )

    # --------------------------------------------------------
    # Safety fallback
    # --------------------------------------------------------

    return (
        "I was unable to complete the requested action "
        "because too many tool calls were required."
    )


# ============================================================
# MEMORY EXTRACTION
# ============================================================

def extract_memories(message: str):
    """
    Extract stable personal information from a user message.
    """

    prompt = f"""
Extract stable personal information from the following
user message.

Only extract information that is likely to remain useful
in future conversations.

Do not extract:
- temporary requests
- one-time tasks
- passwords
- API keys
- sensitive information
- random details

Return ONLY valid JSON.

Format:

[
    {{
        "key": "example_key",
        "value": "example value"
    }}
]

If there is no useful memory, return:

[]

User message:

{message}
"""

    try:

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )

        text = response.text.strip()

        if text.startswith("```"):

            lines = text.splitlines()

            if lines:
                lines = lines[1:]

            if (
                lines
                and lines[-1].strip() == "```"
            ):
                lines = lines[:-1]

            text = "\n".join(lines)

        memories = json.loads(text)

        if not isinstance(memories, list):
            return []

        return memories

    except Exception:

        return []


# ============================================================
# SAVE LOCAL MEMORY
# ============================================================

def extract_local_memory(
    db,
    user_id,
    message: str
):
    """
    Extract memories from the message and save/update them
    in the database.
    """

    from .models import Memory

    memories = extract_memories(
        message
    )

    for memory in memories:

        key = memory.get("key")
        value = memory.get("value")

        if not key or value is None:
            continue

        existing_memory = (
            db.query(Memory)
            .filter(
                Memory.user_id == user_id,
                Memory.key == key
            )
            .first()
        )

        if existing_memory:

            existing_memory.value = str(value)

        else:

            new_memory = Memory(
                user_id=user_id,
                key=key,
                value=str(value)
            )

            db.add(new_memory)

    db.commit()

    return memories


# ============================================================
# GET RELEVANT MEMORIES
# ============================================================

def get_relevant_memories(
    db,
    user_id,
    query: str,
    limit: int = 10
):
    """
    Retrieve stored memories for the current user.
    """

    from .models import Memory

    memories = (
        db.query(Memory)
        .filter(
            Memory.user_id == user_id
        )
        .order_by(
            Memory.id.desc()
        )
        .limit(limit)
        .all()
    )

    return [
        {
            "key": memory.key,
            "value": memory.value
        }
        for memory in memories
    ]


# ============================================================
# CONVERSATION SUMMARY
# ============================================================

def generate_conversation_summary(
    messages,
    previous_summary=None
):
    """
    Generate a concise rolling summary of the conversation.
    """

    conversation_text = ""

    for message in messages:

        if isinstance(message, dict):

            role = message.get(
                "role",
                ""
            )

            content = message.get(
                "content",
                ""
            )

        else:

            role = getattr(
                message,
                "role",
                ""
            )

            content = getattr(
                message,
                "content",
                ""
            )

        conversation_text += (
            f"{role}: {content}\n"
        )

    prompt = f"""
Create a concise summary of the conversation.

Previous summary:
{previous_summary or "None"}

Recent conversation:
{conversation_text}

Keep important:
- user goals
- decisions
- tasks
- preferences
- important context
- unresolved items

Do not include unnecessary details.

Return only the summary.
"""

    try:

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )

        return response.text.strip()

    except Exception:

        return previous_summary or ""





