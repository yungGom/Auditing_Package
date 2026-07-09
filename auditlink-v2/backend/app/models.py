"""ORM models for AuditLink v2.

Hierarchy: FiscalYear -> Client -> Engagement -> Phase(/Folder, nestable)
           -> Account -> Task. PBCItem, Interview, and IcfrControl also hang
off the structure. Cascades are declared so deleting a parent removes its
whole subtree (paired with PRAGMA foreign_keys=ON in database.py).
"""
from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey, Integer, JSON, String, Text, func,
)
from sqlalchemy.orm import relationship

from .database import Base


class FiscalYear(Base):
    __tablename__ = "fiscal_years"

    id = Column(Integer, primary_key=True)
    label = Column(String, nullable=False)
    start_date = Column(String, nullable=True)   # "2025-01-01"
    end_date = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=False)

    clients = relationship(
        "Client", back_populates="fiscal_year",
        cascade="all, delete-orphan", passive_deletes=True,
        order_by="Client.id",
    )


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True)
    fy_id = Column(Integer, ForeignKey("fiscal_years.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    industry = Column(String, nullable=True, default="미지정")

    fiscal_year = relationship("FiscalYear", back_populates="clients")
    engagements = relationship(
        "Engagement", back_populates="client",
        cascade="all, delete-orphan", passive_deletes=True,
        order_by="Engagement.id",
    )
    icfr_controls = relationship(
        "IcfrControl", back_populates="client",
        cascade="all, delete-orphan", passive_deletes=True,
        order_by="IcfrControl.id",
    )


class Engagement(Base):
    __tablename__ = "engagements"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    eng_type = Column(String, nullable=False, default="audit")  # audit | review | etc

    client = relationship("Client", back_populates="engagements")
    phases = relationship(
        "Phase", back_populates="engagement",
        cascade="all, delete-orphan", passive_deletes=True,
        order_by="Phase.order_index",
    )


class Phase(Base):
    """Structural container under an engagement.

    `kind` is "phase" or "folder"; `parent_id` lets folders/phases nest freely
    (used by the "기타" engagement type). Accounts attach to the leaf node.
    """
    __tablename__ = "phases"

    id = Column(Integer, primary_key=True)
    engagement_id = Column(Integer, ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False)
    parent_id = Column(Integer, ForeignKey("phases.id", ondelete="CASCADE"), nullable=True)
    name = Column(String, nullable=False)
    kind = Column(String, nullable=False, default="phase")  # phase | folder
    order_index = Column(Integer, nullable=False, default=0)

    engagement = relationship("Engagement", back_populates="phases")
    parent = relationship("Phase", remote_side=[id], back_populates="children")
    children = relationship(
        "Phase", back_populates="parent",
        cascade="all, delete-orphan", passive_deletes=True,
        order_by="Phase.order_index",
    )
    accounts = relationship(
        "Account", back_populates="phase",
        cascade="all, delete-orphan", passive_deletes=True,
        order_by="Account.order_index",
    )


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True)
    phase_id = Column(Integer, ForeignKey("phases.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    order_index = Column(Integer, nullable=False, default=0)

    phase = relationship("Phase", back_populates="accounts")
    tasks = relationship(
        "Task", back_populates="account",
        cascade="all, delete-orphan", passive_deletes=True,
        order_by="Task.id",
    )
    pbc_items = relationship(
        "PBCItem", back_populates="account",
        cascade="all, delete-orphan", passive_deletes=True,
        order_by="PBCItem.id",
    )
    interviews = relationship(
        "Interview", back_populates="account",
        cascade="all, delete-orphan", passive_deletes=True,
        order_by="Interview.id",
    )


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    status = Column(String, nullable=False, default="todo")  # todo|in_progress|review|done
    assignee = Column(String, nullable=True, default="")
    deadline = Column(String, nullable=True)   # "2025-04-10"
    priority = Column(String, nullable=False, default="mid")  # high|mid|low
    memo = Column(Text, nullable=True, default="")
    file = Column(String, nullable=True, default="")

    account = relationship("Account", back_populates="tasks")
    history = relationship(
        "TaskHistory", back_populates="task",
        cascade="all, delete-orphan", passive_deletes=True,
        order_by="TaskHistory.id",
    )


class TaskHistory(Base):
    __tablename__ = "task_history"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, nullable=False)
    at = Column(String, nullable=False)  # "2025-04-10"

    task = relationship("Task", back_populates="history")


class PBCItem(Base):
    __tablename__ = "pbc_items"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    dept = Column(String, nullable=True, default="")
    requested = Column(String, nullable=True, default="")
    due = Column(String, nullable=True, default="")
    status = Column(String, nullable=False, default="draft")   # draft|requested|received|overdue
    recv_date = Column(String, nullable=True, default="")
    done = Column(String, nullable=False, default="none")       # full|partial|none

    account = relationship("Account", back_populates="pbc_items")


class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    date = Column(String, nullable=True)
    person = Column(String, nullable=True, default="")
    title = Column(String, nullable=True, default="")
    dept = Column(String, nullable=True, default="")
    place = Column(String, nullable=True, default="")
    attendees = Column(String, nullable=True, default="")
    topic = Column(String, nullable=True, default="")
    status = Column(String, nullable=False, default="in_progress")  # in_progress|done
    memo = Column(Text, nullable=True, default="")

    account = relationship("Account", back_populates="interviews")
    questions = relationship(
        "InterviewQuestion", back_populates="interview",
        cascade="all, delete-orphan", passive_deletes=True,
        order_by="InterviewQuestion.order_index",
    )


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id = Column(Integer, primary_key=True)
    interview_id = Column(Integer, ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False)
    q = Column(Text, nullable=True, default="")
    a = Column(Text, nullable=True, default="")
    answerer = Column(String, nullable=True, default="")
    follow_up = Column(Boolean, nullable=False, default=False)
    follow_up_note = Column(Text, nullable=True, default="")
    order_index = Column(Integer, nullable=False, default=0)

    interview = relationship("Interview", back_populates="questions")


class IcfrControl(Base):
    """Internal-control (ICFR) test row with embedded RCM detail fields."""
    __tablename__ = "icfr_controls"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    code = Column(String, nullable=False)
    process = Column(String, nullable=True, default="")
    description = Column(Text, nullable=True, default="")
    ctrl_type = Column(String, nullable=False, default="operating")  # design|operating
    owner = Column(String, nullable=True, default="")
    due = Column(String, nullable=True, default="")
    status = Column(String, nullable=False, default="todo")  # todo|in_progress|review|done|exception

    # RCM detail
    risk = Column(Text, nullable=True, default="")
    objective = Column(String, nullable=True, default="")
    org = Column(String, nullable=True, default="")
    nature = Column(String, nullable=True, default="")
    frequency = Column(String, nullable=True, default="")
    residual_risk = Column(String, nullable=True, default="")
    mrc = Column(Boolean, nullable=False, default=False)
    ipe = Column(Boolean, nullable=False, default=False)
    accounts = Column(JSON, nullable=False, default=list)      # list[str]
    assertions = Column(JSON, nullable=False, default=list)    # list[str]
    test_types = Column(JSON, nullable=False, default=list)    # list[str]
    eval_result = Column(String, nullable=True, default="")
    sample_size = Column(String, nullable=True, default="")
    exception_note = Column(Text, nullable=True, default="")

    client = relationship("Client", back_populates="icfr_controls")


class Template(Base):
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    industry = Column(String, nullable=True, default="")
    updated_at = Column(DateTime, nullable=False, server_default=func.now())

    accounts = relationship(
        "TemplateAccount", back_populates="template",
        cascade="all, delete-orphan", passive_deletes=True,
        order_by="TemplateAccount.id",
    )


class TemplateAccount(Base):
    __tablename__ = "template_accounts"

    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey("templates.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    task_count = Column(Integer, nullable=False, default=0)

    template = relationship("Template", back_populates="accounts")


class Settings(Base):
    """Single-row app settings / user profile (id is always 1)."""
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True)
    user_name = Column(String, nullable=True, default="")
    org = Column(String, nullable=True, default="")
    email = Column(String, nullable=True, default="")
    deadline_threshold = Column(String, nullable=False, default="D-7")
    startup_alert = Column(Boolean, nullable=False, default=True)
    highlight_overdue = Column(Boolean, nullable=False, default=True)
