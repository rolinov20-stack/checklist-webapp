from datetime import datetime
from sqlalchemy import String, Integer, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.database import Base


class Checklist(Base):
    __tablename__ = "checklists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    items: Mapped[list["ChecklistItem"]] = relationship(
        back_populates="checklist", cascade="all, delete-orphan"
    )
    sessions: Mapped[list["ChecklistSession"]] = relationship(
        back_populates="checklist", cascade="all, delete-orphan"
    )


class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    checklist_id: Mapped[int] = mapped_column(ForeignKey("checklists.id"))
    text: Mapped[str] = mapped_column(String(500))
    order: Mapped[int] = mapped_column(Integer, default=0)

    checklist: Mapped["Checklist"] = relationship(back_populates="items")


class ChecklistSession(Base):
    """Сессия прохождения чеклиста пользователем."""

    __tablename__ = "checklist_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    checklist_id: Mapped[int] = mapped_column(ForeignKey("checklists.id"))
    user_id: Mapped[int] = mapped_column(Integer)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    checklist: Mapped["Checklist"] = relationship(back_populates="sessions")
    checks: Mapped[list["SessionCheck"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class SessionCheck(Base):
    """Отметка выполнения конкретного пункта в сессии."""

    __tablename__ = "session_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("checklist_sessions.id"))
    item_id: Mapped[int] = mapped_column(ForeignKey("checklist_items.id"))
    is_checked: Mapped[bool] = mapped_column(Boolean, default=False)

    session: Mapped["ChecklistSession"] = relationship(back_populates="checks")
    item: Mapped["ChecklistItem"] = relationship()
