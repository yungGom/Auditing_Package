"""Pydantic v2 request/response schemas.

Create schemas are permissive (sensible defaults); Update schemas are all-optional
for PATCH-style partial updates. Response schemas read straight off the ORM.
"""
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

EngType = Literal["audit", "review", "etc"]
PhaseKind = Literal["phase", "folder"]
TaskStatus = Literal["todo", "in_progress", "review", "done"]
Priority = Literal["high", "mid", "low"]
PBCStatus = Literal["draft", "requested", "received", "overdue"]
PBCDone = Literal["full", "partial", "none"]
InterviewStatus = Literal["in_progress", "done"]
IcfrStatus = Literal["todo", "in_progress", "review", "done", "exception"]
IcfrType = Literal["design", "operating"]


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- Fiscal Year ----
class FiscalYearCreate(BaseModel):
    label: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_active: bool = False


class FiscalYearUpdate(BaseModel):
    label: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_active: Optional[bool] = None


class FiscalYearOut(ORMBase):
    id: int
    label: str
    start_date: Optional[str]
    end_date: Optional[str]
    is_active: bool


# ---- Client ----
class ClientCreate(BaseModel):
    fy_id: int
    name: str
    industry: Optional[str] = "미지정"


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None


class ClientOut(ORMBase):
    id: int
    fy_id: int
    name: str
    industry: Optional[str]


# ---- Engagement ----
class EngagementCreate(BaseModel):
    client_id: int
    name: str
    eng_type: EngType = "audit"
    # When true, seed default phases for the type (audit/review). Default true.
    apply_template: bool = True


class EngagementUpdate(BaseModel):
    name: Optional[str] = None
    eng_type: Optional[EngType] = None


class EngagementOut(ORMBase):
    id: int
    client_id: int
    name: str
    eng_type: str


# ---- Phase / Folder ----
class PhaseCreate(BaseModel):
    engagement_id: int
    name: str
    kind: PhaseKind = "phase"
    parent_id: Optional[int] = None
    order_index: int = 0


class PhaseUpdate(BaseModel):
    name: Optional[str] = None
    kind: Optional[PhaseKind] = None
    parent_id: Optional[int] = None
    order_index: Optional[int] = None


class PhaseOut(ORMBase):
    id: int
    engagement_id: int
    parent_id: Optional[int]
    name: str
    kind: str
    order_index: int


# ---- Account ----
class AccountCreate(BaseModel):
    phase_id: int
    name: str
    order_index: int = 0


class AccountBulkCreate(BaseModel):
    phase_id: int
    names: List[str]


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    order_index: Optional[int] = None


class AccountReorder(BaseModel):
    phase_id: int
    ordered_ids: List[int]


class AccountOut(ORMBase):
    id: int
    phase_id: int
    name: str
    order_index: int


# ---- Task ----
class TaskHistoryOut(ORMBase):
    id: int
    status: str
    at: str


class TaskCreate(BaseModel):
    account_id: int
    title: str
    status: TaskStatus = "todo"
    assignee: Optional[str] = ""
    deadline: Optional[str] = None
    priority: Priority = "mid"
    memo: Optional[str] = ""
    file: Optional[str] = ""


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[TaskStatus] = None
    assignee: Optional[str] = None
    deadline: Optional[str] = None
    priority: Optional[Priority] = None
    memo: Optional[str] = None
    file: Optional[str] = None


class TaskOut(ORMBase):
    id: int
    account_id: int
    title: str
    status: str
    assignee: Optional[str]
    deadline: Optional[str]
    priority: str
    memo: Optional[str]
    file: Optional[str]
    history: List[TaskHistoryOut] = []


# ---- PBC ----
class PBCCreate(BaseModel):
    account_id: int
    name: str
    dept: Optional[str] = ""
    requested: Optional[str] = ""
    due: Optional[str] = ""
    status: PBCStatus = "draft"
    recv_date: Optional[str] = ""
    done: PBCDone = "none"


class PBCBulkCreate(BaseModel):
    items: List[PBCCreate]


class PBCUpdate(BaseModel):
    name: Optional[str] = None
    dept: Optional[str] = None
    requested: Optional[str] = None
    due: Optional[str] = None
    status: Optional[PBCStatus] = None
    recv_date: Optional[str] = None
    done: Optional[PBCDone] = None


class PBCOut(ORMBase):
    id: int
    account_id: int
    name: str
    dept: Optional[str]
    requested: Optional[str]
    due: Optional[str]
    status: str
    recv_date: Optional[str]
    done: str


# ---- Interview ----
class QuestionIn(BaseModel):
    q: Optional[str] = ""
    a: Optional[str] = ""
    answerer: Optional[str] = ""
    follow_up: bool = False
    follow_up_note: Optional[str] = ""


class QuestionOut(ORMBase):
    id: int
    q: Optional[str]
    a: Optional[str]
    answerer: Optional[str]
    follow_up: bool
    follow_up_note: Optional[str]
    order_index: int


class InterviewCreate(BaseModel):
    account_id: int
    date: Optional[str] = None
    person: Optional[str] = ""
    title: Optional[str] = ""
    dept: Optional[str] = ""
    place: Optional[str] = ""
    attendees: Optional[str] = ""
    topic: Optional[str] = ""
    status: InterviewStatus = "in_progress"
    memo: Optional[str] = ""
    questions: Optional[List[QuestionIn]] = None


class InterviewUpdate(BaseModel):
    date: Optional[str] = None
    person: Optional[str] = None
    title: Optional[str] = None
    dept: Optional[str] = None
    place: Optional[str] = None
    attendees: Optional[str] = None
    topic: Optional[str] = None
    status: Optional[InterviewStatus] = None
    memo: Optional[str] = None
    # When provided, the question list is replaced wholesale (supports reorder).
    questions: Optional[List[QuestionIn]] = None


class InterviewOut(ORMBase):
    id: int
    account_id: int
    date: Optional[str]
    person: Optional[str]
    title: Optional[str]
    dept: Optional[str]
    place: Optional[str]
    attendees: Optional[str]
    topic: Optional[str]
    status: str
    memo: Optional[str]
    questions: List[QuestionOut] = []


# ---- ICFR ----
class RcmIn(BaseModel):
    risk: Optional[str] = ""
    objective: Optional[str] = ""
    org: Optional[str] = ""
    nature: Optional[str] = ""
    frequency: Optional[str] = ""
    residual_risk: Optional[str] = ""
    mrc: bool = False
    ipe: bool = False
    accounts: List[str] = []
    assertions: List[str] = []
    test_types: List[str] = []
    eval_result: Optional[str] = ""
    sample_size: Optional[str] = ""
    exception_note: Optional[str] = ""


class IcfrCreate(BaseModel):
    client_id: int
    code: str
    process: Optional[str] = ""
    description: Optional[str] = ""
    ctrl_type: IcfrType = "operating"
    owner: Optional[str] = ""
    due: Optional[str] = ""
    status: IcfrStatus = "todo"
    rcm: RcmIn = Field(default_factory=RcmIn)


class IcfrUpdate(BaseModel):
    code: Optional[str] = None
    process: Optional[str] = None
    description: Optional[str] = None
    ctrl_type: Optional[IcfrType] = None
    owner: Optional[str] = None
    due: Optional[str] = None
    status: Optional[IcfrStatus] = None
    rcm: Optional[RcmIn] = None


class RcmOut(BaseModel):
    risk: Optional[str]
    objective: Optional[str]
    org: Optional[str]
    nature: Optional[str]
    frequency: Optional[str]
    residual_risk: Optional[str]
    mrc: bool
    ipe: bool
    accounts: List[str]
    assertions: List[str]
    test_types: List[str]
    eval_result: Optional[str]
    sample_size: Optional[str]
    exception_note: Optional[str]


class IcfrOut(BaseModel):
    id: int
    client_id: int
    code: str
    process: Optional[str]
    description: Optional[str]
    ctrl_type: str
    owner: Optional[str]
    due: Optional[str]
    status: str
    rcm: RcmOut


# ---- Template ----
class TemplateAccountIn(BaseModel):
    name: str
    task_count: int = 0


class TemplateAccountOut(ORMBase):
    id: int
    name: str
    task_count: int


class TemplateCreate(BaseModel):
    name: str
    industry: Optional[str] = ""
    accounts: List[TemplateAccountIn] = []


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    accounts: Optional[List[TemplateAccountIn]] = None


class TemplateOut(ORMBase):
    id: int
    name: str
    industry: Optional[str]
    updated_at: datetime
    accounts: List[TemplateAccountOut] = []


# ---- Settings ----
class SettingsUpdate(BaseModel):
    user_name: Optional[str] = None
    org: Optional[str] = None
    email: Optional[str] = None
    deadline_threshold: Optional[str] = None
    startup_alert: Optional[bool] = None
    highlight_overdue: Optional[bool] = None


class SettingsOut(ORMBase):
    id: int
    user_name: Optional[str]
    org: Optional[str]
    email: Optional[str]
    deadline_threshold: str
    startup_alert: bool
    highlight_overdue: bool


# ---- Engagement tree ----
class TreeNode(BaseModel):
    id: str
    label: str
    type: str
    children: List["TreeNode"] = []
    # optional adornments depending on type
    is_active: Optional[bool] = None
    industry: Optional[str] = None
    eng_type: Optional[str] = None
    kind: Optional[str] = None
    parent_label: Optional[str] = None
    task_count: Optional[int] = None
    ref_id: Optional[int] = None


TreeNode.model_rebuild()
