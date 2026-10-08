"""Pure V2-1 domain contracts: no I/O or legacy imports."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import Any


def stable_id(namespace: str, value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return namespace + ":" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


class DecisionState(str, Enum):
    UNRESOLVED = "UNRESOLVED"
    SUGGESTED = "SUGGESTED"
    REVIEWABLE = "REVIEWABLE"
    USER_CONFIRMED = "USER_CONFIRMED"
    DERIVED_FROM_CONFIRMED = "DERIVED_FROM_CONFIRMED"
    STALE = "STALE"
    CONFLICT = "CONFLICT"


class OutputScope(str, Enum):
    SOURCE_COVERED = "SOURCE_COVERED"
    CONNECTED = "CONNECTED"
    SEPARATE = "SEPARATE"
    FULL_COMPANY = "FULL_COMPANY"


@dataclass(frozen=True)
class ExpandedQName:
    namespace_uri: str
    local_name: str
    def __post_init__(self):
        if not self.namespace_uri or not self.local_name:
            raise ValueError("expanded QName needs namespace URI and local name")
    @property
    def key(self) -> str:
        return "{" + self.namespace_uri + "}" + self.local_name


@dataclass(frozen=True)
class SourceSnapshot:
    snapshot_id: str
    content_id: str
    kind: str
    logical_uri: str
    byte_length: int
    parser_profile: str
    @classmethod
    def from_bytes(cls, *, kind: str, logical_uri: str, data: bytes,
                   parser_profile: str) -> "SourceSnapshot":
        if not kind or not logical_uri or not parser_profile:
            raise ValueError("source kind, logical URI, parser profile required")
        content_id = hashlib.sha256(data).hexdigest()
        return cls(stable_id("source", (kind, logical_uri, content_id, parser_profile)),
                   content_id, kind, logical_uri, len(data), parser_profile)


@dataclass(frozen=True)
class SourceRef:
    role: str
    snapshot_id: str | None
    missing_reason: str | None = None
    def __post_init__(self):
        if not self.role or (self.snapshot_id is None) == (self.missing_reason is None):
            raise ValueError("source ref needs exactly one snapshot or missing reason")


@dataclass(frozen=True)
class SourceBundle:
    bundle_hash: str
    members: tuple[SourceRef, ...]
    @classmethod
    def create(cls, members: tuple[SourceRef, ...]) -> "SourceBundle":
        ordered = tuple(sorted(members, key=lambda item: item.role))
        roles = [m.role for m in ordered]
        allowed = {"CURRENT_DSD", "CURRENT_TAXONOMY", "CURRENT_EXTENSION",
                   "CURRENT_INSTANCE", "PRIOR_COMPANY_XBRL", "REFERENCE_CORPUS"}
        if (len(roles) != len(set(roles))
                or not {"CURRENT_DSD", "CURRENT_TAXONOMY"}.issubset(roles)
                or not set(roles).issubset(allowed)):
            raise ValueError("unique permitted source roles and current slots required")
        return cls(stable_id("bundle", [(m.role, m.snapshot_id, m.missing_reason) for m in ordered]), ordered)
    @property
    def missing(self) -> tuple[SourceRef, ...]:
        return tuple(m for m in self.members if m.snapshot_id is None)


@dataclass(frozen=True)
class ReportIdentity:
    entity_scheme: str
    entity_identifier: str
    company_name: str
    scope: OutputScope
    report_type: str
    period_end: str
    fiscal_calendar: str


@dataclass(frozen=True)
class DocumentRevision:
    document_id: str
    snapshot_id: str
    parser_version: str
    revision_id: str
    @classmethod
    def identity(cls, document_id: str, snapshot_id: str, parser_version: str) -> "DocumentRevision":
        return cls(document_id, snapshot_id, parser_version,
                   stable_id("document-revision", (document_id, snapshot_id, parser_version)))


@dataclass(frozen=True)
class SemanticSubject:
    subject_id: str
    document_revision_id: str
    structural_path: tuple[str, ...]
    facet: str
    scope: OutputScope
    source_snapshot_id: str
    @classmethod
    def identity(cls, document_revision_id: str, structural_path: tuple[str, ...],
                 facet: str, scope: OutputScope, source_snapshot_id: str) -> "SemanticSubject":
        sid = stable_id("subject", (document_revision_id, structural_path, facet, scope.value))
        return cls(sid, document_revision_id, structural_path, facet, scope, source_snapshot_id)


@dataclass(frozen=True)
class ResolutionProposal:
    proposal_id: str
    subject_id: str
    facet: str
    value: Any
    evidence_kind: str
    state: DecisionState = DecisionState.SUGGESTED
    def __post_init__(self):
        if self.state not in (DecisionState.SUGGESTED, DecisionState.REVIEWABLE):
            raise ValueError("proposal cannot be confirmed")


@dataclass(frozen=True)
class SemanticDecision:
    decision_id: str
    run_id: str
    subject_id: str
    value: Any
    state: DecisionState
    actor: str | None
    reviewed_at: str | None
    reason: str | None
    parent_decision_ids: tuple[str, ...]
    rule_id: str | None
    rule_version: str | None
    source_bundle_hash: str
    revision: int
    action: str
    def __post_init__(self):
        if self.state is DecisionState.USER_CONFIRMED:
            if self.action != "APPLY" or not self.actor or not self.reviewed_at or not self.reason:
                raise ValueError("USER_CONFIRMED needs explicit actor/action/reason")
        if self.state is DecisionState.DERIVED_FROM_CONFIRMED:
            if self.action != "DERIVE" or not self.parent_decision_ids or not self.rule_id or not self.rule_version:
                raise ValueError("derived decision needs parents and deterministic rule")


@dataclass(frozen=True)
class ContextSpec:
    entity_scheme: str
    entity_identifier: str
    period_kind: str
    start: str | None
    end: str
    dimensions: tuple[tuple[str, str], ...] = ()
    context_element: str | None = None


@dataclass(frozen=True)
class UnitSpec:
    numerator: tuple[str, ...]
    denominator: tuple[str, ...] = ()
    display_scale: int | None = None
    def __post_init__(self):
        if not self.numerator:
            raise ValueError("unit numerator required")


@dataclass(frozen=True)
class ValueSpec:
    raw: str
    kind: str
    nil: bool = False
    accuracy: str | None = None


@dataclass(frozen=True)
class FactSemanticKey:
    entity: str
    entity_scheme: str
    qname: ExpandedQName
    period: tuple[str, ...]
    dimensions: tuple[tuple[str, str], ...]
    unit: str | None
    language: str | None = None
    def __post_init__(self):
        if not self.entity or not self.entity_scheme or not self.period:
            raise ValueError("fact entity scheme, identifier and period required")
        if self.dimensions != tuple(sorted(self.dimensions)):
            raise ValueError("dimensions must be canonically ordered")
    @property
    def key(self) -> str:
        return stable_id("fact", (self.entity_scheme, self.entity, self.qname.key, self.period,
                                  self.dimensions, self.unit, self.language))


@dataclass(frozen=True)
class FactBinding:
    binding_id: str
    run_id: str
    semantic_key: FactSemanticKey
    value: ValueSpec
    subject_id: str
    role_occurrence_id: str | None = None
    decision_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class OutputOccurrence:
    occurrence_id: str
    fact_key: str
    role_occurrence_id: str
    output_path: tuple[str, ...]
    @classmethod
    def identity(cls, fact_key: str, role_occurrence_id: str,
                 output_path: tuple[str, ...]) -> "OutputOccurrence":
        return cls(stable_id("output-occurrence", (fact_key, role_occurrence_id, output_path)),
                   fact_key, role_occurrence_id, output_path)


@dataclass(frozen=True)
class ValidationIssue:
    issue_id: str
    run_id: str
    code: str
    detail: str
    subject_id: str | None = None


@dataclass(frozen=True)
class GateResult:
    ready: bool
    scope: OutputScope
    denominator_id: str
    issues: tuple[ValidationIssue, ...] = ()


@dataclass(frozen=True)
class Run:
    run_id: str
    bundle_hash: str
    entity: str
    entity_scheme: str
    scope: str
    report_period: str
    revision: int
    status: str


@dataclass(frozen=True)
class ArtifactSet:
    artifact_set_id: str
    run_id: str
    revision: int
    status: str
    manifest_hash: str | None = None
