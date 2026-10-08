"""Immutable provenance types shared by V2 domain and adapters."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re


class EvidenceKind(str, Enum):
    CURRENT_SOURCE = "CURRENT_SOURCE"
    USER_DECISION = "USER_DECISION"
    PRIOR_CANDIDATE = "PRIOR_CANDIDATE"
    PEER_CANDIDATE = "PEER_CANDIDATE"
    AI_PROPOSAL = "AI_PROPOSAL"


@dataclass(frozen=True)
class EvidenceRef:
    source_snapshot_id: str
    logical_uri: str
    locator: str
    raw_sha256: str
    parser_version: str
    rule_version: str
    member_uri: str | None = None
    kind: EvidenceKind = EvidenceKind.CURRENT_SOURCE

    def __post_init__(self) -> None:
        if not all((self.source_snapshot_id, self.logical_uri, self.locator,
                    self.parser_version, self.rule_version)):
            raise ValueError("evidence requires source, locator and versions")
        if re.fullmatch(r"[0-9a-f]{64}", self.raw_sha256) is None:
            raise ValueError("evidence raw SHA-256 must be lowercase hex")


@dataclass(frozen=True)
class DecisionLineage:
    actor: str | None
    reviewed_at: str | None
    reason: str | None
    parent_decision_ids: tuple[str, ...]
    rule_id: str | None
    rule_version: str | None
    source_bundle_hash: str
    revision: int
    evidence_kind: EvidenceKind

    @property
    def user_confirmed_evidence(self) -> bool:
        return (self.evidence_kind is EvidenceKind.USER_DECISION
                and bool(self.actor and self.reviewed_at and self.reason))

    @property
    def derived_evidence(self) -> bool:
        return (bool(self.parent_decision_ids and self.rule_id and self.rule_version)
                and self.evidence_kind is EvidenceKind.CURRENT_SOURCE)
