"""
SQLAlchemy модели для Telegram-бота STNGrobot.
"""
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, List

from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, ForeignKey,
    DateTime, Enum, UniqueConstraint
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func

from .database import Base


class UserRole(str, PyEnum):
    ROOT = "root"
    ADMIN = "admin"
    SPEC = "spec"
    USER = "user"


class RequestStatus(str, PyEnum):
    NEW = "new"
    ASSIGNED = "assigned"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AssignmentStatus(str, PyEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    role: Mapped[str] = mapped_column(
        Enum(UserRole), default=UserRole.USER, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    specialist: Mapped[Optional["Specialist"]] = relationship(
        "Specialist", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    created_requests: Mapped[List["Request"]] = relationship(
        "Request", back_populates="user", foreign_keys="Request.user_id"
    )
    created_groups: Mapped[List["Group"]] = relationship(
        "Group", back_populates="creator", foreign_keys="Group.created_by"
    )
    assigned_specialists: Mapped[List["Specialist"]] = relationship(
        "Specialist", back_populates="assigned_by_user", foreign_keys="Specialist.assigned_by"
    )

    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, role={self.role})>"

    @property
    def full_name(self) -> str:
        parts = [self.first_name, self.last_name]
        name = " ".join(p for p in parts if p)
        return name or self.username or f"User {self.telegram_id}"


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    creator: Mapped["User"] = relationship(
        "User", back_populates="created_groups", foreign_keys=[created_by]
    )
    specialists: Mapped[List["Specialist"]] = relationship(
        "Specialist", back_populates="group", cascade="all, delete-orphan"
    )
    requests: Mapped[List["Request"]] = relationship(
        "Request", back_populates="group"
    )

    def __repr__(self):
        return f"<Group(id={self.id}, name='{self.name}')>"


class Specialist(Base):
    __tablename__ = "specialists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), unique=True, nullable=False
    )
    group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("groups.id"), nullable=False, index=True
    )
    assigned_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="specialist")
    group: Mapped["Group"] = relationship("Group", back_populates="specialists")
    assigned_by_user: Mapped["User"] = relationship(
        "User", back_populates="assigned_specialists", foreign_keys=[assigned_by]
    )
    assignments: Mapped[List["RequestAssignment"]] = relationship(
        "RequestAssignment", back_populates="specialist", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Specialist(id={self.id}, user_id={self.user_id}, group_id={self.group_id})>"


class Request(Base):
    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(RequestStatus), default=RequestStatus.NEW, nullable=False, index=True
    )
    assigned_to: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("specialists.id"), nullable=True
    )
    assigned_group: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("groups.id"), nullable=True, index=True
    )
    completed_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("specialists.id"), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="created_requests")
    group: Mapped[Optional["Group"]] = relationship("Group", back_populates="requests")
    specialist_assigned: Mapped[Optional["Specialist"]] = relationship(
        "Specialist", foreign_keys=[assigned_to]
    )
    specialist_completed: Mapped[Optional["Specialist"]] = relationship(
        "Specialist", foreign_keys=[completed_by]
    )
    assignments: Mapped[List["RequestAssignment"]] = relationship(
        "RequestAssignment", back_populates="request", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Request(id={self.id}, status={self.status}, user_id={self.user_id})>"


class RequestAssignment(Base):
    __tablename__ = "request_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("requests.id"), nullable=False, index=True
    )
    specialist_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("specialists.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        Enum(AssignmentStatus), default=AssignmentStatus.PENDING, nullable=False
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("request_id", "specialist_id", name="uq_request_specialist"),
    )

    # Relationships
    request: Mapped["Request"] = relationship("Request", back_populates="assignments")
    specialist: Mapped["Specialist"] = relationship("Specialist", back_populates="assignments")

    def __repr__(self):
        return f"<RequestAssignment(id={self.id}, request_id={self.request_id}, status={self.status})>"
