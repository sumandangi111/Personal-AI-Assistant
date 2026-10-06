from fastapi import APIRouter, Depends, HTTPException

from .auth import get_current_user
from .models import User
from .calendar_service import (
    list_events,
    create_event
)


router = APIRouter(
    prefix="/calendar",
    tags=["Google Calendar"]
)


@router.get("/events")
def get_calendar_events(
    max_results: int = 10,
    current_user: User = Depends(get_current_user)
):
    try:
        events = list_events(
            max_results=max_results
        )

        return {
            "user_id": current_user.id,
            "events": events
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Calendar error: {str(e)}"
        )

@router.post("/events")
def add_calendar_event(
    summary: str,
    start_datetime: str,
    end_datetime: str,
    description: str = "",
    location: str = "",
    current_user: User = Depends(get_current_user)
):
    try:

        event = create_event(
            summary=summary,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            description=description,
            location=location
        )

        return {
            "user_id": current_user.id,
            "message": "Calendar event created successfully.",
            "event": event
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Calendar error: {str(e)}"
        )


