from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .auth import get_current_admin


router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)


@router.get("/users")
def get_all_users(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    users = db.query(User).all()

    return {
        "total_users": len(users),
        "users": [
            {
                "user_id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role
            }
            for user in users
        ]
    }

# --------------------------------------------------
# ADMIN STATISTICS
# --------------------------------------------------

@router.get("/stats")
def get_admin_stats(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    total_users = db.query(User).count()

    total_admins = db.query(User).filter(
        User.role == "admin"
    ).count()

    total_normal_users = db.query(User).filter(
        User.role == "user"
    ).count()

    return {
        "total_users": total_users,
        "total_admins": total_admins,
        "total_normal_users": total_normal_users
    }

