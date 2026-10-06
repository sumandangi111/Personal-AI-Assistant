import json
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from google.genai import types

from .database import get_db
from .models import (
    User,
    Conversation,
    Message,
    PendingAction
)
from .schemas import ChatRequest
from .auth import get_current_user

from .ai_service import (
    generate_ai_response_with_tools,
    extract_local_memory,
    generate_conversation_summary
)

from .memory import get_relevant_memories

from .gmail_service import (
    send_email,
    reply_to_email,
    forward_email
)


# =========================================================
# LOGGER
# =========================================================

logger = logging.getLogger(__name__)


# =========================================================
# ROUTER
# =========================================================

router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)


# =========================================================
# SETTINGS
# =========================================================

MAX_HISTORY_MESSAGES = 10
SUMMARY_TRIGGER_MESSAGES = 20
SUMMARY_BATCH_SIZE = 10

# Pending Gmail actions expire after 15 minutes.
PENDING_ACTION_EXPIRATION_MINUTES = 15

GMAIL_ACTION_TYPES = [
    "gmail_send",
    "gmail_reply",
    "gmail_forward"
]


# =========================================================
# PENDING ACTION HELPERS
# =========================================================

def expire_pending_actions(
    db: Session,
    user_id: int
):
    """
    Mark old pending Gmail actions as expired.

    Actions with created_at=None are ignored so that
    existing database records created before the
    created_at column was added are not accidentally expired.
    """

    expiration_time = (
        datetime.utcnow()
        - timedelta(
            minutes=PENDING_ACTION_EXPIRATION_MINUTES
        )
    )

    expired_actions = (
        db.query(PendingAction)
        .filter(
            PendingAction.user_id == user_id,
            PendingAction.action_type.in_(GMAIL_ACTION_TYPES),
            PendingAction.status == "pending",
            PendingAction.created_at.isnot(None),
            PendingAction.created_at <= expiration_time
        )
        .all()
    )

    if not expired_actions:
        return

    for action in expired_actions:

        action.status = "expired"

        logger.info(
            "Pending Gmail action expired: "
            "action_id=%s user_id=%s action_type=%s",
            action.id,
            user_id,
            action.action_type
        )

    db.commit()


def get_new_pending_action(
    db: Session,
    user_id: int,
    previous_action_ids: set[int]
):
    """
    Return only a newly created pending Gmail action.

    This prevents old pending actions from appearing
    in unrelated requests.
    """

    new_action = (
        db.query(PendingAction)
        .filter(
            PendingAction.user_id == user_id,
            PendingAction.action_type.in_(GMAIL_ACTION_TYPES),
            PendingAction.status == "pending",
            ~PendingAction.id.in_(previous_action_ids)
        )
        .order_by(
            PendingAction.id.desc()
        )
        .first()
    )

    return new_action


# =========================================================
# MAIN CHAT ENDPOINT
# =========================================================

@router.post("")
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Main AI chat endpoint.
    """

    # -----------------------------------------------------
    # 1. EXPIRE OLD PENDING GMAIL ACTIONS
    # -----------------------------------------------------

    expire_pending_actions(
        db=db,
        user_id=current_user.id
    )

    # -----------------------------------------------------
    # 2. CAPTURE EXISTING PENDING ACTION IDS
    # -----------------------------------------------------

    existing_pending_actions = (
        db.query(PendingAction.id)
        .filter(
            PendingAction.user_id == current_user.id,
            PendingAction.action_type.in_(GMAIL_ACTION_TYPES),
            PendingAction.status == "pending"
        )
        .all()
    )

    previous_action_ids = {
        action_id
        for (action_id,) in existing_pending_actions
    }

    # -----------------------------------------------------
    # 3. GET REQUESTED CONVERSATION
    # -----------------------------------------------------

    conversation = None

    if request.conversation_id is not None:

        conversation = (
            db.query(Conversation)
            .filter(
                Conversation.id == request.conversation_id,
                Conversation.user_id == current_user.id
            )
            .first()
        )

        if not conversation:

            raise HTTPException(
                status_code=404,
                detail="Conversation not found"
            )

    # -----------------------------------------------------
    # 4. CREATE CONVERSATION IF NEEDED
    # -----------------------------------------------------

    if conversation is None:

        conversation = Conversation(
            user_id=current_user.id
        )

        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # -----------------------------------------------------
    # 5. SAVE USER MESSAGE
    # -----------------------------------------------------

    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.message
    )

    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    # -----------------------------------------------------
    # 6. EXTRACT LOCAL MEMORY
    # -----------------------------------------------------

    try:

        extract_local_memory(
            db=db,
            user_id=current_user.id,
            message=request.message
        )

    except Exception:

        logger.exception(
            "Local memory extraction failed: "
            "user_id=%s conversation_id=%s",
            current_user.id,
            conversation.id
        )

        # Memory failure should not stop chat.

    # -----------------------------------------------------
    # 7. LOAD RECENT CONVERSATION MESSAGES
    # -----------------------------------------------------

    recent_messages = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation.id
        )
        .order_by(
            Message.id.desc()
        )
        .limit(MAX_HISTORY_MESSAGES)
        .all()
    )

    recent_messages.reverse()

    # -----------------------------------------------------
    # 8. CONVERT HISTORY TO GEMINI FORMAT
    # -----------------------------------------------------

    history = []

    for message in recent_messages:

        role = message.role

        if role == "assistant":
            role = "model"

        history.append(
            types.Content(
                role=role,
                parts=[
                    types.Part(
                        text=message.content
                    )
                ]
            )
        )

    # -----------------------------------------------------
    # 9. GET RELEVANT LONG-TERM MEMORIES
    # -----------------------------------------------------

    try:

        relevant_memories = get_relevant_memories(
            db=db,
            user_id=current_user.id,
            user_message=request.message
        )

    except Exception:

        logger.exception(
            "Relevant memory retrieval failed: "
            "user_id=%s conversation_id=%s",
            current_user.id,
            conversation.id
        )

        relevant_memories = []

    # -----------------------------------------------------
    # 10. GET CONVERSATION SUMMARY
    # -----------------------------------------------------

    conversation_summary = getattr(
        conversation,
        "summary",
        None
    )

    # -----------------------------------------------------
    # 11. GENERATE AI RESPONSE
    # -----------------------------------------------------

    try:

        ai_response = generate_ai_response_with_tools(
            messages=history,
            db=db,
            user_id=current_user.id,
            memories=relevant_memories,
            conversation_summary=conversation_summary
        )

    except Exception:

        logger.exception(
            "AI response generation failed: "
            "user_id=%s conversation_id=%s",
            current_user.id,
            conversation.id
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "I'm sorry, I couldn't generate a response right now. "
                "Please try again."
            )
        )

    # -----------------------------------------------------
    # 12. EXTRACT AI RESPONSE TEXT
    # -----------------------------------------------------

    if isinstance(ai_response, dict):

        assistant_text = (
            ai_response.get("response")
            or ai_response.get("message")
            or ai_response.get("text")
            or str(ai_response)
        )

    else:

        assistant_text = str(ai_response)

    # -----------------------------------------------------
    # 13. SAVE ASSISTANT MESSAGE
    # -----------------------------------------------------

    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=assistant_text
    )

    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)

    # -----------------------------------------------------
    # 14. CHECK MESSAGE COUNT
    # -----------------------------------------------------

    total_messages = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation.id
        )
        .count()
    )

    # -----------------------------------------------------
    # 15. UPDATE CONVERSATION SUMMARY
    # -----------------------------------------------------

    if total_messages >= SUMMARY_TRIGGER_MESSAGES:

        try:

            summary_messages = (
                db.query(Message)
                .filter(
                    Message.conversation_id == conversation.id
                )
                .order_by(
                    Message.id.desc()
                )
                .limit(SUMMARY_BATCH_SIZE)
                .all()
            )

            summary_messages.reverse()

            summary_text = generate_conversation_summary(
                summary_messages
            )

            if hasattr(conversation, "summary"):

                conversation.summary = summary_text

                db.commit()

        except Exception:

            logger.exception(
                "Conversation summary generation failed: "
                "user_id=%s conversation_id=%s",
                current_user.id,
                conversation.id
            )

    # -----------------------------------------------------
    # 16. CHECK FOR NEW PENDING GMAIL ACTION
    # -----------------------------------------------------

    pending_action = get_new_pending_action(
        db=db,
        user_id=current_user.id,
        previous_action_ids=previous_action_ids
    )

    # -----------------------------------------------------
    # 17. BUILD RESPONSE
    # -----------------------------------------------------

    response = {
        "message": assistant_text,
        "conversation_id": conversation.id
    }

    # -----------------------------------------------------
    # 18. RETURN ONLY NEW PENDING ACTION
    # -----------------------------------------------------

    if pending_action:

        response["pending_action"] = {
            "action_id": pending_action.id,
            "action_type": pending_action.action_type,
            "status": pending_action.status
        }

    return response


# =========================================================
# CONFIRM EMAIL ACTION
# =========================================================

@router.post(
    "/confirm-email/{action_id}"
)
def confirm_email_action(
    action_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Confirm and execute a pending Gmail action.

    Supported actions:
    - gmail_send
    - gmail_reply
    - gmail_forward
    """

    # -----------------------------------------------------
    # 1. EXPIRE OLD ACTIONS
    # -----------------------------------------------------

    expire_pending_actions(
        db=db,
        user_id=current_user.id
    )

    # -----------------------------------------------------
    # 2. FIND PENDING ACTION
    # -----------------------------------------------------

    action = (
        db.query(PendingAction)
        .filter(
            PendingAction.id == action_id,
            PendingAction.user_id == current_user.id,
            PendingAction.action_type.in_(GMAIL_ACTION_TYPES),
            PendingAction.status == "pending"
        )
        .first()
    )

    # -----------------------------------------------------
    # 3. CHECK ACTION
    # -----------------------------------------------------

    if not action:

        expired_action = (
            db.query(PendingAction)
            .filter(
                PendingAction.id == action_id,
                PendingAction.user_id == current_user.id,
                PendingAction.action_type.in_(GMAIL_ACTION_TYPES),
                PendingAction.status == "expired"
            )
            .first()
        )

        if expired_action:

            raise HTTPException(
                status_code=410,
                detail="Pending email action has expired."
            )

        raise HTTPException(
            status_code=404,
            detail="Pending email action not found."
        )

    # -----------------------------------------------------
    # 4. LOAD ACTION DATA
    # -----------------------------------------------------

    try:

        action_data = json.loads(
            action.action_data
        )

    except Exception:

        logger.exception(
            "Invalid pending action data: "
            "action_id=%s user_id=%s",
            action_id,
            current_user.id
        )

        raise HTTPException(
            status_code=500,
            detail="The pending email action contains invalid data."
        )

    # =====================================================
    # GMAIL SEND
    # =====================================================

    if action.action_type == "gmail_send":

        to = action_data.get("to")
        subject = action_data.get("subject")
        body = action_data.get("body", "")

        if not to:

            raise HTTPException(
                status_code=400,
                detail="Recipient email address is missing."
            )

        if not subject:

            raise HTTPException(
                status_code=400,
                detail="Email subject is missing."
            )

        try:

            result = send_email(
                to=to,
                subject=subject,
                body=body
            )

        except Exception:

            logger.exception(
                "Failed to send Gmail email: "
                "action_id=%s user_id=%s",
                action.id,
                current_user.id
            )

            raise HTTPException(
                status_code=500,
                detail="Failed to send the email. Please try again."
            )

        action.status = "completed"

        db.commit()

        return {
            "message": "Gmail email sent successfully.",
            "action_id": action.id,
            "action_type": action.action_type,
            "to": to,
            "subject": subject,
            "gmail_message_id": (
                result.get("message_id")
                if isinstance(result, dict)
                else None
            )
        }

    # =====================================================
    # GMAIL REPLY
    # =====================================================

    elif action.action_type == "gmail_reply":

        message_id = action_data.get("message_id")
        body = action_data.get("body", "")

        if not message_id:

            raise HTTPException(
                status_code=400,
                detail="Original Gmail message ID is missing."
            )

        try:

            result = reply_to_email(
                message_id=message_id,
                body=body
            )

        except Exception:

            logger.exception(
                "Failed to reply to Gmail email: "
                "action_id=%s user_id=%s",
                action.id,
                current_user.id
            )

            raise HTTPException(
                status_code=500,
                detail="Failed to send the email reply. Please try again."
            )

        action.status = "completed"

        db.commit()

        return {
            "message": "Gmail email reply sent successfully.",
            "action_id": action.id,
            "action_type": action.action_type,
            "gmail_message_id": (
                result.get("message_id")
                if isinstance(result, dict)
                else None
            )
        }

    # =====================================================
    # GMAIL FORWARD
    # =====================================================

    elif action.action_type == "gmail_forward":

        message_id = action_data.get("message_id")
        to = action_data.get("to")
        body = action_data.get("body", "")

        if not message_id:

            raise HTTPException(
                status_code=400,
                detail="Original Gmail message ID is missing."
            )

        if not to:

            raise HTTPException(
                status_code=400,
                detail="Forward recipient email address is missing."
            )

        try:

            result = forward_email(
                message_id=message_id,
                to=to,
                body=body
            )

        except Exception:

            logger.exception(
                "Failed to forward Gmail email: "
                "action_id=%s user_id=%s",
                action.id,
                current_user.id
            )

            raise HTTPException(
                status_code=500,
                detail="Failed to forward the email. Please try again."
            )

        action.status = "completed"

        db.commit()

        return {
            "message": "Gmail email forwarded successfully.",
            "action_id": action.id,
            "action_type": action.action_type,
            "to": to,
            "subject": (
                result.get("subject")
                if isinstance(result, dict)
                else None
            ),
            "gmail_message_id": (
                result.get("message_id")
                if isinstance(result, dict)
                else None
            )
        }

    # -----------------------------------------------------
    # UNKNOWN ACTION
    # -----------------------------------------------------

    raise HTTPException(
        status_code=400,
        detail="Unsupported email action."
    )


# =========================================================
# CANCEL PENDING EMAIL ACTION
# =========================================================

@router.post(
    "/cancel/{action_id}"
)
def cancel_pending_action(
    action_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel a pending Gmail action.

    Supported actions:
    - gmail_send
    - gmail_reply
    - gmail_forward
    """

    # -----------------------------------------------------
    # 1. EXPIRE OLD ACTIONS
    # -----------------------------------------------------

    expire_pending_actions(
        db=db,
        user_id=current_user.id
    )

    # -----------------------------------------------------
    # 2. FIND PENDING ACTION
    # -----------------------------------------------------

    action = (
        db.query(PendingAction)
        .filter(
            PendingAction.id == action_id,
            PendingAction.user_id == current_user.id,
            PendingAction.action_type.in_(GMAIL_ACTION_TYPES),
            PendingAction.status == "pending"
        )
        .first()
    )

    # -----------------------------------------------------
    # 3. CHECK ACTION
    # -----------------------------------------------------

    if not action:

        expired_action = (
            db.query(PendingAction)
            .filter(
                PendingAction.id == action_id,
                PendingAction.user_id == current_user.id,
                PendingAction.action_type.in_(GMAIL_ACTION_TYPES),
                PendingAction.status == "expired"
            )
            .first()
        )

        if expired_action:

            raise HTTPException(
                status_code=410,
                detail=(
                    "Pending email action has expired "
                    "and cannot be cancelled."
                )
            )

        raise HTTPException(
            status_code=404,
            detail="Pending email action not found."
        )

    # -----------------------------------------------------
    # 4. CANCEL ACTION
    # -----------------------------------------------------

    action.status = "cancelled"

    db.commit()

    logger.info(
        "Pending Gmail action cancelled: "
        "action_id=%s user_id=%s action_type=%s",
        action.id,
        current_user.id,
        action.action_type
    )

    # -----------------------------------------------------
    # 5. RETURN RESULT
    # -----------------------------------------------------

    return {
        "message": "Pending email action cancelled successfully.",
        "action_id": action.id,
        "action_type": action.action_type,
        "status": action.status
    }
