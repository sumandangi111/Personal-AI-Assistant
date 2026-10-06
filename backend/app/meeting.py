from datetime import datetime, timedelta

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)

from pydantic import BaseModel, Field

from sqlalchemy.orm import Session

from .auth import get_current_user
from .database import get_db
from .models import User, MeetingRequest

from .meeting_service import (
    check_admin_availability,
    create_user_meeting,
    get_user_meetings,
)

from .ai_service import (
    check_personal_availability,
)


router = APIRouter(
    prefix="/meeting",
    tags=["Meet Admin"],
)


# ============================================================
# REQUEST SCHEMAS
# ============================================================


class MeetingRequestCreate(BaseModel):
    start_datetime: str = Field(
        ...,
        description="Meeting start datetime in ISO 8601 format.",
    )

    duration: int = Field(
        30,
        ge=15,
        le=480,
        description="Meeting duration in minutes.",
    )


class MeetingRejectRequest(BaseModel):
    message: str = Field(
        "",
        description="Optional rejection message from Admin.",
    )


# ============================================================
# HELPER — GET ADMIN
# ============================================================


def get_admin_user(
    db: Session,
):
    admin_user = (
        db.query(User)
        .filter(
            User.role == "admin"
        )
        .first()
    )

    if not admin_user:
        raise HTTPException(
            status_code=404,
            detail="No Admin account is configured.",
        )

    return admin_user


# ============================================================
# CHECK ADMIN AVAILABILITY
# ============================================================


@router.get("/availability")
def get_admin_availability(
    date: str = Query(
        ...,
        description="Requested date, e.g. 2026-10-02",
    ),

    time: str = Query(
        ...,
        description="Requested time, e.g. 19:00",
    ),

    duration: int = Query(
        30,
        ge=15,
        le=480,
        description="Meeting duration in minutes",
    ),

    current_user: User = Depends(
        get_current_user
    ),

    db: Session = Depends(get_db),
):
    """
    Check Admin availability.

    Order:

    1. Admin Personal Memory
    2. Admin Google Calendar

    The requesting user's Personal Memory is NOT used
    for Admin meeting availability.
    """

    # --------------------------------------------------------
    # GET ADMIN
    # --------------------------------------------------------

    admin_user = get_admin_user(db)

    # --------------------------------------------------------
    # VALIDATE DATETIME
    # --------------------------------------------------------

    requested_datetime = (
        f"{date}T{time}:00+05:30"
    )

    try:

        datetime.fromisoformat(
            requested_datetime
        )

    except ValueError:

        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid date or time. "
                "Use date=YYYY-MM-DD and time=HH:MM."
            ),
        )

    # --------------------------------------------------------
    # CHECK ADMIN PERSONAL MEMORY
    # --------------------------------------------------------

    try:

        personal_result = check_personal_availability(
            db=db,
            user_id=admin_user.id,
            requested_start_datetime=requested_datetime,
            duration_minutes=duration,
        )

    except Exception as error:

        print(
            "Admin personal availability error:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to check Admin personal availability."
            ),
        )

    # --------------------------------------------------------
    # ADMIN PERSONAL MEMORY BLOCKS TIME
    # --------------------------------------------------------

    if not personal_result.get("available"):

        return {
            "available": False,
            "requested_time": requested_datetime,
            "personal_available": False,
            "admin_available": False,
            "slot": None,
            "message": (
                "Admin is not available at the requested "
                "time according to Admin's availability."
            ),
            "reason": personal_result.get(
                "message",
                "",
            ),
        }

    # --------------------------------------------------------
    # CHECK ADMIN GOOGLE CALENDAR
    # --------------------------------------------------------

    try:

        admin_result = check_admin_availability(
            requested_datetime=requested_datetime,
            duration_minutes=duration,
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:

        print(
            "Admin calendar availability error:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to check Admin Google Calendar "
                "availability."
            ),
        )

    # --------------------------------------------------------
    # ADMIN CALENDAR CONFLICT
    # --------------------------------------------------------

    if not admin_result.get("available"):

        return {
            "available": False,
            "requested_time": requested_datetime,
            "personal_available": True,
            "admin_available": False,
            "slot": admin_result.get("slot"),
            "message": (
                "Admin is not available at the requested "
                "time because Admin's calendar has a conflict."
            ),
        }

    # --------------------------------------------------------
    # BOTH CHECKS PASSED
    # --------------------------------------------------------

    return {
        "available": True,
        "requested_time": requested_datetime,
        "personal_available": True,
        "admin_available": True,
        "slot": admin_result.get("slot"),
        "message": (
            "Admin is available at the requested time."
        ),
    }


# ============================================================
# CREATE PENDING MEETING REQUEST
# ============================================================


@router.post("/request")
def request_meeting(
    request: MeetingRequestCreate,

    current_user: User = Depends(
        get_current_user
    ),

    db: Session = Depends(get_db),
):
    """
    Create a PENDING meeting request.

    IMPORTANT:

    This endpoint does NOT immediately create a
    Google Calendar event.

    Flow:

    User
      ↓
    Admin Personal Memory
      ↓
    Admin Google Calendar
      ↓
    Create PENDING request
      ↓
    Admin approves/rejects
    """

    # --------------------------------------------------------
    # GET ADMIN
    # --------------------------------------------------------

    admin_user = get_admin_user(db)

    # --------------------------------------------------------
    # VALIDATE DATETIME
    # --------------------------------------------------------

    try:

        requested_start = datetime.fromisoformat(
            request.start_datetime
        )

    except ValueError:

        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid start_datetime. "
                "Use ISO 8601 format."
            ),
        )

    # --------------------------------------------------------
    # CHECK ADMIN PERSONAL MEMORY
    # --------------------------------------------------------

    try:

        personal_result = check_personal_availability(
            db=db,
            user_id=admin_user.id,
            requested_start_datetime=request.start_datetime,
            duration_minutes=request.duration,
        )

    except Exception as error:

        print(
            "Admin personal availability error:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to verify Admin availability."
            ),
        )

    # --------------------------------------------------------
    # ADMIN PERSONAL MEMORY CONFLICT
    # --------------------------------------------------------

    if not personal_result.get("available"):

        raise HTTPException(
            status_code=409,
            detail={
                "code": "ADMIN_PERSONAL_AVAILABILITY_CONFLICT",
                "message": (
                    "Admin is not available at the "
                    "requested time."
                ),
                "reason": personal_result.get(
                    "message",
                    "",
                ),
            },
        )

    # --------------------------------------------------------
    # CHECK ADMIN GOOGLE CALENDAR
    # --------------------------------------------------------

    try:

        admin_result = check_admin_availability(
            requested_datetime=request.start_datetime,
            duration_minutes=request.duration,
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:

        print(
            "Admin calendar availability error:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to check Admin calendar availability."
            ),
        )

    # --------------------------------------------------------
    # ADMIN CALENDAR CONFLICT
    # --------------------------------------------------------

    if not admin_result.get("available"):

        raise HTTPException(
            status_code=409,
            detail={
                "code": "ADMIN_CALENDAR_CONFLICT",
                "message": (
                    "Admin is not available at the "
                    "requested time."
                ),
            },
        )

    # --------------------------------------------------------
    # CALCULATE END DATETIME
    # --------------------------------------------------------

    end_datetime = (
        requested_start
        + timedelta(minutes=request.duration)
    )

    # --------------------------------------------------------
    # CREATE PENDING REQUEST
    # --------------------------------------------------------

    meeting_request = MeetingRequest(
        user_id=current_user.id,

        user_name=current_user.name,

        user_email=current_user.email,

        start_datetime=request.start_datetime,

        end_datetime=end_datetime.isoformat(),

        duration=request.duration,

        status="pending",

        admin_message=None,

        google_event_id=None,
    )

    db.add(meeting_request)

    db.commit()

    db.refresh(meeting_request)

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {
        "message": (
            "Your meeting request has been sent to Admin "
            "for approval."
        ),

        "request": {
            "id": meeting_request.id,

            "user_name": meeting_request.user_name,

            "user_email": meeting_request.user_email,

            "start_datetime": (
                meeting_request.start_datetime
            ),

            "end_datetime": (
                meeting_request.end_datetime
            ),

            "duration": meeting_request.duration,

            "status": meeting_request.status,
        },
    }


# ============================================================
# USER — MY MEETING REQUESTS
# ============================================================


@router.get("/my-requests")
def my_meeting_requests(
    current_user: User = Depends(
        get_current_user
    ),

    db: Session = Depends(get_db),
):
    """
    Return meeting requests belonging only
    to the currently logged-in user.
    """

    requests = (
        db.query(MeetingRequest)
        .filter(
            MeetingRequest.user_id == current_user.id
        )
        .order_by(
            MeetingRequest.id.desc()
        )
        .all()
    )

    return {
        "requests": [
            {
                "id": item.id,

                "user_name": item.user_name,

                "user_email": item.user_email,

                "start_datetime": item.start_datetime,

                "end_datetime": item.end_datetime,

                "duration": item.duration,

                "status": item.status,

                "admin_message": item.admin_message,

                "google_event_id": item.google_event_id,

                "created_at": item.created_at,

                "updated_at": item.updated_at,
            }

            for item in requests
        ]
    }


# ============================================================
# ADMIN — ALL MEETING REQUESTS
# ============================================================


@router.get("/admin-requests")
def admin_meeting_requests(
    current_user: User = Depends(
        get_current_user
    ),

    db: Session = Depends(get_db),
):
    """
    Admin-only endpoint.

    Returns meeting requests from users.
    """

    # --------------------------------------------------------
    # ADMIN AUTHORIZATION
    # --------------------------------------------------------

    if current_user.role != "admin":

        raise HTTPException(
            status_code=403,
            detail="Only Admin can view meeting requests.",
        )

    # --------------------------------------------------------
    # GET REQUESTS
    # --------------------------------------------------------

    requests = (
        db.query(MeetingRequest)
        .order_by(
            MeetingRequest.id.desc()
        )
        .all()
    )

    return {
        "requests": [
            {
                "id": item.id,

                "user_id": item.user_id,

                "user_name": item.user_name,

                "user_email": item.user_email,

                "start_datetime": item.start_datetime,

                "end_datetime": item.end_datetime,

                "duration": item.duration,

                "status": item.status,

                "admin_message": item.admin_message,

                "google_event_id": item.google_event_id,

                "created_at": item.created_at,

                "updated_at": item.updated_at,
            }

            for item in requests
        ]
    }


# ============================================================
# ADMIN — APPROVE MEETING REQUEST
# ============================================================


@router.post("/{request_id}/approve")
def approve_meeting_request(
    request_id: int,

    current_user: User = Depends(
        get_current_user
    ),

    db: Session = Depends(get_db),
):
    """
    Admin approves a pending meeting request.

    Final flow:

    Pending
       ↓
    Final Personal Memory check
       ↓
    Final Google Calendar check
       ↓
    Create Google Calendar event
       ↓
    Approved
    """

    # --------------------------------------------------------
    # ADMIN AUTHORIZATION
    # --------------------------------------------------------

    if current_user.role != "admin":

        raise HTTPException(
            status_code=403,
            detail="Only Admin can approve meetings.",
        )

    # --------------------------------------------------------
    # FIND REQUEST
    # --------------------------------------------------------

    meeting_request = (
        db.query(MeetingRequest)
        .filter(
            MeetingRequest.id == request_id
        )
        .first()
    )

    if not meeting_request:

        raise HTTPException(
            status_code=404,
            detail="Meeting request not found.",
        )

    # --------------------------------------------------------
    # ONLY PENDING REQUESTS CAN BE APPROVED
    # --------------------------------------------------------

    if meeting_request.status != "pending":

        raise HTTPException(
            status_code=409,
            detail=(
                f"This meeting request is already "
                f"{meeting_request.status}."
            ),
        )

    # --------------------------------------------------------
    # FINAL PERSONAL MEMORY CHECK
    # --------------------------------------------------------

    try:

        personal_result = check_personal_availability(
            db=db,
            user_id=current_user.id,
            requested_start_datetime=(
                meeting_request.start_datetime
            ),
            duration_minutes=meeting_request.duration,
            exclude_request_id=meeting_request.id,
        )

    except Exception as error:

        print(
            "Final Admin personal availability error:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to verify Admin availability."
            ),
        )

    # --------------------------------------------------------
    # ADMIN PERSONAL MEMORY CONFLICT
    # --------------------------------------------------------

    if not personal_result.get("available"):

        raise HTTPException(
            status_code=409,
            detail={
                "code": "ADMIN_PERSONAL_AVAILABILITY_CONFLICT",
                "message": (
                    "Admin is no longer available at "
                    "the requested time."
                ),
                "reason": personal_result.get(
                    "message",
                    "",
                ),
            },
        )

    # --------------------------------------------------------
    # FINAL GOOGLE CALENDAR CHECK + CREATE
    # --------------------------------------------------------

    try:

        result = create_user_meeting(
            user_id=meeting_request.user_id,

            user_name=meeting_request.user_name,

            user_email=meeting_request.user_email,

            start_datetime=(
                meeting_request.start_datetime
            ),

            duration_minutes=meeting_request.duration,
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:

        print(
            "Meeting approval error:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to create the Google "
                "Calendar meeting."
            ),
        )

    # --------------------------------------------------------
    # CALENDAR BECAME UNAVAILABLE
    # --------------------------------------------------------

    if not result.get("success"):

        raise HTTPException(
            status_code=409,
            detail={
                "code": "ADMIN_CALENDAR_CONFLICT",
                "message": result.get(
                    "message",
                    "The selected slot is no longer available.",
                ),
            },
        )

    # --------------------------------------------------------
    # UPDATE REQUEST
    # --------------------------------------------------------

    event = result.get("event") or {}

    meeting_request.status = "approved"

    meeting_request.google_event_id = (
        event.get("id")
    )

    meeting_request.admin_message = (
        "Meeting request approved by Admin."
    )

    db.commit()

    db.refresh(meeting_request)

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {
        "message": (
            "Meeting request approved successfully."
        ),

        "request": {
            "id": meeting_request.id,

            "user_name": meeting_request.user_name,

            "user_email": meeting_request.user_email,

            "start_datetime": (
                meeting_request.start_datetime
            ),

            "end_datetime": (
                meeting_request.end_datetime
            ),

            "duration": meeting_request.duration,

            "status": meeting_request.status,

            "google_event_id": (
                meeting_request.google_event_id
            ),
        },
    }


# ============================================================
# ADMIN — REJECT MEETING REQUEST
# ============================================================


@router.post("/{request_id}/reject")
def reject_meeting_request(
    request_id: int,

    request: MeetingRejectRequest,

    current_user: User = Depends(
        get_current_user
    ),

    db: Session = Depends(get_db),
):
    """
    Admin rejects a pending meeting request.
    """

    # --------------------------------------------------------
    # ADMIN AUTHORIZATION
    # --------------------------------------------------------

    if current_user.role != "admin":

        raise HTTPException(
            status_code=403,
            detail="Only Admin can reject meetings.",
        )

    # --------------------------------------------------------
    # FIND REQUEST
    # --------------------------------------------------------

    meeting_request = (
        db.query(MeetingRequest)
        .filter(
            MeetingRequest.id == request_id
        )
        .first()
    )

    if not meeting_request:

        raise HTTPException(
            status_code=404,
            detail="Meeting request not found.",
        )

    # --------------------------------------------------------
    # ONLY PENDING REQUESTS CAN BE REJECTED
    # --------------------------------------------------------

    if meeting_request.status != "pending":

        raise HTTPException(
            status_code=409,
            detail=(
                f"This meeting request is already "
                f"{meeting_request.status}."
            ),
        )

    # --------------------------------------------------------
    # UPDATE STATUS
    # --------------------------------------------------------

    meeting_request.status = "rejected"

    if request.message.strip():

        meeting_request.admin_message = (
            request.message.strip()
        )

    else:

        meeting_request.admin_message = (
            "Meeting request rejected by Admin."
        )

    db.commit()

    db.refresh(meeting_request)

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {
        "message": (
            "Meeting request rejected successfully."
        ),

        "request": {
            "id": meeting_request.id,

            "user_name": meeting_request.user_name,

            "user_email": meeting_request.user_email,

            "start_datetime": (
                meeting_request.start_datetime
            ),

            "end_datetime": (
                meeting_request.end_datetime
            ),

            "duration": meeting_request.duration,

            "status": meeting_request.status,

            "admin_message": (
                meeting_request.admin_message
            ),
        },
    }


# ============================================================
# MY APPROVED CALENDAR MEETINGS
# ============================================================


@router.get("/my-meetings")
def my_meetings(
    current_user: User = Depends(
        get_current_user
    ),
):
    """
    Return Google Calendar meetings belonging
    to the current user.
    """

    try:

        meetings = get_user_meetings(
            user_id=current_user.id
        )

        return {
            "meetings": meetings
        }

    except Exception as error:

        print(
            "My meetings error:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to load your meetings."
            ),
        )












