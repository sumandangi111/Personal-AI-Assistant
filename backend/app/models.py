from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    Text,
    DateTime
)
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(
        String,
        nullable=False
    )

    email = Column(
        String,
        unique=True,
        index=True,
        nullable=False
    )

    password = Column(
        String,
        nullable=False
    )

    role = Column(
        String,
        default="user",
        nullable=False
    )

    conversations = relationship(
        "Conversation",
        back_populates="user"
    )

    memories = relationship(
        "Memory",
        back_populates="user"
    )

    meeting_requests = relationship(
        "MeetingRequest",
        back_populates="user"
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    title = Column(
        String,
        default="New Conversation"
    )

    summary = Column(
        Text,
        nullable=True
    )

    user = relationship(
        "User",
        back_populates="conversations"
    )

    messages = relationship(
        "Message",
        back_populates="conversation"
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    conversation_id = Column(
        Integer,
        ForeignKey("conversations.id"),
        nullable=False
    )

    role = Column(
        String,
        nullable=False
    )

    content = Column(
        Text,
        nullable=False
    )

    conversation = relationship(
        "Conversation",
        back_populates="messages"
    )


class Memory(Base):
    __tablename__ = "memories"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    key = Column(
        String,
        nullable=False
    )

    value = Column(
        Text,
        nullable=False
    )

    user = relationship(
        "User",
        back_populates="memories"
    )


class PendingAction(Base):
    __tablename__ = "pending_actions"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    action_type = Column(
        String,
        nullable=False
    )

    action_data = Column(
        Text,
        nullable=False
    )

    status = Column(
        String,
        default="pending",
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )


class MeetingRequest(Base):
    __tablename__ = "meeting_requests"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    # User who requested the meeting
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    # Store requester information at the time of request
    user_name = Column(
        String,
        nullable=False
    )

    user_email = Column(
        String,
        nullable=False
    )

    # Requested meeting timing
    start_datetime = Column(
        String,
        nullable=False
    )

    end_datetime = Column(
        String,
        nullable=False
    )

    duration = Column(
        Integer,
        nullable=False
    )

    # pending / approved / rejected
    status = Column(
        String,
        default="pending",
        nullable=False,
        index=True
    )

    # Optional message from Admin
    admin_message = Column(
        Text,
        nullable=True
    )

    # Google Calendar event created after approval
    google_event_id = Column(
        String,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    user = relationship(
        "User",
        back_populates="meeting_requests"
    )