from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session

from .auth import get_current_user
from .database import get_db
from .models import User, Memory
from .semantic_memory import find_relevant_memories

router = APIRouter(
    prefix="/memory",
    tags=["Memory"]
)


@router.post("/")
def create_memory(
    key: str,
    value: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    # Check if this memory already exists
    existing_memory = db.query(Memory).filter(
        Memory.user_id == current_user.id,
        Memory.key == key
    ).first()

    # Update existing memory
    if existing_memory:

        existing_memory.value = value

        db.commit()
        db.refresh(existing_memory)

        return {
            "message": "Memory updated successfully",
            "memory_id": existing_memory.id,
            "key": existing_memory.key,
            "value": existing_memory.value
        }

    # Create new memory
    new_memory = Memory(
        user_id=current_user.id,
        key=key,
        value=value
    )

    db.add(new_memory)
    db.commit()
    db.refresh(new_memory)

    return {
        "message": "Memory saved successfully",
        "memory_id": new_memory.id,
        "key": new_memory.key,
        "value": new_memory.value
    }

@router.get("/")
def get_memories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    memories = db.query(Memory).filter(
        Memory.user_id == current_user.id
    ).all()

    return {
        "user_id": current_user.id,
        "memories": [
            {
                "id": memory.id,
                "key": memory.key,
                "value": memory.value
            }
            for memory in memories
        ]
    }


@router.delete("/{memory_id}")
def delete_memory(
    memory_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    memory = db.query(Memory).filter(
        Memory.id == memory_id,
        Memory.user_id == current_user.id
    ).first()

    if not memory:

        raise HTTPException(
            status_code=404,
            detail="Memory not found"
        )

    db.delete(memory)
    db.commit()

    return {
        "message": "Memory deleted successfully",
        "memory_id": memory_id
    }

def get_relevant_memories(
    user_message: str,
    user_id: int,
    db: Session
):
    memories = db.query(Memory).filter(
        Memory.user_id == user_id
    ).all()

    if not memories:
        return []

    return find_relevant_memories(
        user_message,
        memories,
        threshold=0.35
    )