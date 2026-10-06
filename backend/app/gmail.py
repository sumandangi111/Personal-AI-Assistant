from fastapi import APIRouter, Depends

from .auth import get_current_user
from .models import User
from .gmail_service import search_emails


router = APIRouter(
    prefix="/gmail",
    tags=["Gmail"]
)


@router.get("/search")
def search_gmail(
    query: str,
    max_results: int = 10,
    current_user: User = Depends(get_current_user)
):
    results = search_emails(
        query=query,
        max_results=max_results
    )

    return {
        "user_id": current_user.id,
        "query": query,
        "results": results
    }

