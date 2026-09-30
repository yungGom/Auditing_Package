"""Isolated SQLite stores for V2-1. Initialization is the only DDL path."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Callable, Iterator

from .model import (
    ArtifactSet, DecisionState, FactBinding, FactSemanticKey, ResolutionProposal, Run,
    SemanticDecision, SourceBundle, SourceRef, SourceSnapshot, ValidationIssue,
    ValueSpec, stable_id,
)
from .rules import verify_derivation

SCHEMA_VERSION = 1


class ConflictError(ValueError):
    """Revision, idempotency, or semantic conflict."""


def default_v2_root() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "xbrl_v2"


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


class _SQLiteStore:
    db_name = ""

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root) if root is not None else default_v2_root()
        self.db_path = self.root / self.db_name

    @contextmanager
    def read_connection(self, trace: Callable[[str], None] | None = None) -> Iterator[sqlite3.Connection]:
        uri = self.db_path.resolve().as_uri() + "?mode=ro"
        con = sqlite3.connect(uri, uri=True, timeout=30)
        try:
            con.row_factory = sqlite3.Row
            if trace is not None:
                con.set_trace_callback(trace)
            con.execute("PRAGMA busy_timeout=30000")
            con.execute("PRAGMA query_only=ON")
            yield con
        finally:
            con.close()

    @contextmanager
    def write_transaction(self) -> Iterator[sqlite3.Connection]:
        con = sqlite3.connect(self.db_path, timeout=30)
        try:
            con.row_factory = sqlite3.Row
            con.execute("PRAGMA busy_timeout=30000")
            con.execute("BEGIN IMMEDIATE")
            try:
                yield con
            except BaseException:
                con.rollback()
                raise
            else:
                con.commit()
        finally:
            con.close()

    def _initialize(self, ddl: str) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(self.db_path, timeout=30)
        try:
            con.execute("PRAGMA busy_timeout=30000")
            version = int(con.execute("PRAGMA user_version").fetchone()[0])
            if version not in (0, SCHEMA_VERSION):
                raise RuntimeError(f"unsupported V2 schema version: {version}")
            con.execute("PRAGMA journal_mode=WAL")
            con.executescript(ddl)
            if version == 0:
                con.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
            con.commit()
        finally:
            con.close()


class SourceStore(_SQLiteStore):
    """Owns immutable source bytes, snapshot metadata, and storage locations."""

    db_name = "sources.sqlite"

    def initialize(self) -> None:
        self._initialize("""
        CREATE TABLE IF NOT EXISTS source_objects(
            content_id TEXT PRIMARY KEY, bytes BLOB NOT NULL, byte_length INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS source_snapshots(
            snapshot_id TEXT PRIMARY KEY, content_id TEXT NOT NULL,
            kind TEXT NOT NULL, logical_uri TEXT NOT NULL, parser_profile TEXT NOT NULL,
            FOREIGN KEY(content_id) REFERENCES source_objects(content_id));
        CREATE TABLE IF NOT EXISTS source_locations(
            snapshot_id TEXT NOT NULL, storage_location TEXT NOT NULL,
            PRIMARY KEY(snapshot_id, storage_location));
        """)

    def register(self, *, kind: str, logical_uri: str, data: bytes,
                 storage_location: str, parser_profile: str) -> SourceSnapshot:
        snapshot = SourceSnapshot.from_bytes(kind=kind, logical_uri=logical_uri,
                                             data=data, parser_profile=parser_profile)
        if not storage_location:
            raise ValueError("storage location required")
        with self.write_transaction() as con:
            con.execute("INSERT OR IGNORE INTO source_objects VALUES(?,?,?)",
                        (snapshot.content_id, data, snapshot.byte_length))
            con.execute("INSERT OR IGNORE INTO source_snapshots VALUES(?,?,?,?,?)",
                        (snapshot.snapshot_id, snapshot.content_id, kind, logical_uri, parser_profile))
            con.execute("INSERT OR IGNORE INTO source_locations VALUES(?,?)",
                        (snapshot.snapshot_id, storage_location))
        return snapshot

    def get(self, snapshot_id: str) -> SourceSnapshot | None:
        with self.read_connection() as con:
            row = con.execute("""
                SELECT s.*, o.byte_length FROM source_snapshots s
                JOIN source_objects o ON o.content_id=s.content_id WHERE snapshot_id=?
                """, (snapshot_id,)).fetchone()
        return None if row is None else SourceSnapshot(
            row["snapshot_id"], row["content_id"], row["kind"], row["logical_uri"],
            row["byte_length"], row["parser_profile"])

    def locations(self, snapshot_id: str) -> tuple[str, ...]:
        with self.read_connection() as con:
            rows = con.execute("SELECT storage_location FROM source_locations WHERE snapshot_id=? ORDER BY storage_location",
                               (snapshot_id,)).fetchall()
        return tuple(row[0] for row in rows)

    def read_bytes(self, snapshot_id: str) -> bytes | None:
        with self.read_connection() as con:
            row = con.execute("""
                SELECT o.bytes FROM source_snapshots s JOIN source_objects o
                ON o.content_id=s.content_id WHERE s.snapshot_id=?""", (snapshot_id,)).fetchone()
        return None if row is None else bytes(row[0])


class RunStore(_SQLiteStore):
    """Owns run events and reconstructible projections; source IDs are references."""

    db_name = "engine.sqlite"

    def initialize(self) -> None:
        self._initialize("""
        CREATE TABLE IF NOT EXISTS bundles(bundle_hash TEXT PRIMARY KEY, members_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS runs(
            run_id TEXT PRIMARY KEY, bundle_hash TEXT NOT NULL, entity TEXT NOT NULL,
            entity_scheme TEXT NOT NULL, scope TEXT NOT NULL, report_period TEXT NOT NULL,
            revision INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS source_refs(
            run_id TEXT NOT NULL, role TEXT NOT NULL, snapshot_id TEXT, missing_reason TEXT,
            PRIMARY KEY(run_id,role));
        CREATE TABLE IF NOT EXISTS semantic_subjects(
            run_id TEXT NOT NULL, subject_id TEXT NOT NULL, source_snapshot_id TEXT NOT NULL,
            facet TEXT NOT NULL, parser_version TEXT NOT NULL,
            schema_version TEXT NOT NULL, PRIMARY KEY(run_id,subject_id));
        CREATE TABLE IF NOT EXISTS decision_events(
            event_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, decision_id TEXT NOT NULL,
            kind TEXT NOT NULL, payload_json TEXT NOT NULL, revision INTEGER NOT NULL,
            occurred_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS decision_projection(
            decision_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, subject_id TEXT NOT NULL,
            state TEXT NOT NULL, value_json TEXT NOT NULL, actor TEXT, reviewed_at TEXT,
            reason TEXT, parent_ids_json TEXT NOT NULL, rule_id TEXT, rule_version TEXT,
            bundle_hash TEXT NOT NULL, revision INTEGER NOT NULL, action TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS decision_dependencies(
            decision_id TEXT NOT NULL, dependency_type TEXT NOT NULL, dependency_id TEXT NOT NULL,
            PRIMARY KEY(decision_id,dependency_type,dependency_id));
        CREATE TABLE IF NOT EXISTS idempotency(
            run_id TEXT NOT NULL, key TEXT NOT NULL, command_hash TEXT NOT NULL,
            decision_id TEXT NOT NULL, PRIMARY KEY(run_id,key));
        CREATE TABLE IF NOT EXISTS fact_bindings(
            run_id TEXT NOT NULL, fact_key TEXT NOT NULL, key_json TEXT NOT NULL,
            value_json TEXT NOT NULL, subject_id TEXT NOT NULL, role_occurrence_id TEXT,
            decision_ids_json TEXT NOT NULL, status TEXT NOT NULL,
            PRIMARY KEY(run_id,fact_key));
        CREATE TABLE IF NOT EXISTS fact_status_events(
            event_seq INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT UNIQUE NOT NULL,
            run_id TEXT NOT NULL, fact_key TEXT NOT NULL, status TEXT NOT NULL,
            reason TEXT NOT NULL, revision INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS output_occurrences(
            occurrence_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, fact_key TEXT NOT NULL,
            role_occurrence_id TEXT NOT NULL, output_path_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS validation_issues(
            issue_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, code TEXT NOT NULL,
            detail TEXT NOT NULL, subject_id TEXT);
        CREATE TABLE IF NOT EXISTS artifact_sets(
            artifact_set_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, revision INTEGER NOT NULL,
            status TEXT NOT NULL, manifest_hash TEXT);
        """)
        # Startup recovery is a write lifecycle action, never a GET/read side effect.
        with self.write_transaction() as con:
            con.execute("UPDATE runs SET status='INTERRUPTED' WHERE status='RUNNING'")

    def create_run(self, *, bundle: SourceBundle, entity: str, entity_scheme: str,
                   scope: str, report_period: str) -> Run:
        if not entity or not entity_scheme or not scope or not report_period:
            raise ValueError("run identity fields required")
        from .model import OutputScope
        OutputScope(scope)
        # A pure bundle is an unverified identity shell. Verify each source ID at
        # the run boundary so an answer snapshot cannot be relabeled as current.
        source_store = SourceStore(self.root)
        for member in bundle.members:
            if member.snapshot_id is None:
                continue
            try:
                snapshot = source_store.get(member.snapshot_id)
            except sqlite3.OperationalError as exc:
                raise ConflictError("source store is not initialized") from exc
            if snapshot is None or snapshot.kind != member.role:
                raise ConflictError("unregistered or misclassified source snapshot")
        run_id = stable_id("run", (bundle.bundle_hash, entity_scheme, entity,
                                   scope, report_period))
        with self.write_transaction() as con:
            con.execute("INSERT OR IGNORE INTO bundles VALUES(?,?)",
                        (bundle.bundle_hash, _json([(m.role, m.snapshot_id, m.missing_reason)
                                                    for m in bundle.members])))
            con.execute("INSERT OR IGNORE INTO runs VALUES(?,?,?,?,?,?,0,'NEW')",
                        (run_id, bundle.bundle_hash, entity, entity_scheme,
                         scope, report_period))
            for member in bundle.members:
                con.execute("INSERT OR IGNORE INTO source_refs VALUES(?,?,?,?)",
                            (run_id, member.role, member.snapshot_id, member.missing_reason))
        return self.get_run(run_id)

    def get_run(self, run_id: str) -> Run:
        with self.read_connection() as con:
            row = con.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(run_id)
        return Run(row["run_id"], row["bundle_hash"], row["entity"],
                   row["entity_scheme"], row["scope"], row["report_period"],
                   row["revision"], row["status"])

    def mark_running(self, run_id: str) -> None:
        with self.write_transaction() as con:
            if not con.execute("UPDATE runs SET status='RUNNING' WHERE run_id=?", (run_id,)).rowcount:
                raise KeyError(run_id)

    def add_subject(self, *, run_id: str, subject_id: str,
                    source_snapshot_id: str, facet: str,
                    parser_version: str = "identity-shell-v1",
                    schema_version: str = "domain-v1") -> None:
        with self.write_transaction() as con:
            member = con.execute("SELECT 1 FROM source_refs WHERE run_id=? AND snapshot_id=?",
                                 (run_id, source_snapshot_id)).fetchone()
            if member is None:
                raise ValueError("subject source is not a run input")
            if not parser_version or not schema_version:
                raise ValueError("parser and schema versions required")
            con.execute("INSERT OR IGNORE INTO semantic_subjects VALUES(?,?,?,?,?,?)",
                        (run_id, subject_id, source_snapshot_id, facet,
                         parser_version, schema_version))

    def suggest(self, *, run_id: str, subject_id: str,
                value: object, evidence_kind: str) -> ResolutionProposal:
        with self.read_connection() as con:
            subject = con.execute("SELECT facet FROM semantic_subjects WHERE run_id=? AND subject_id=?",
                                  (run_id, subject_id)).fetchone()
            if subject is None:
                raise KeyError(subject_id)
        return ResolutionProposal(stable_id("proposal", (run_id, subject_id, value, evidence_kind)),
                                  subject_id, subject["facet"], value, evidence_kind)

    @staticmethod
    def _check_revision(con: sqlite3.Connection, run_id: str, expected: int) -> sqlite3.Row:
        row = con.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(run_id)
        if row["revision"] != expected:
            raise ConflictError("run revision changed")
        return row

    @staticmethod
    def _subject(con: sqlite3.Connection, run_id: str, subject_id: str) -> sqlite3.Row:
        row = con.execute("SELECT * FROM semantic_subjects WHERE run_id=? AND subject_id=?",
                          (run_id, subject_id)).fetchone()
        if row is None:
            raise KeyError(subject_id)
        return row

    @staticmethod
    def _insert_decision(con: sqlite3.Connection, d: SemanticDecision,
                         event_kind: str) -> None:
        payload = dict(decision_id=d.decision_id, run_id=d.run_id,
                       subject_id=d.subject_id, value=d.value, state=d.state.value,
                       actor=d.actor, reviewed_at=d.reviewed_at, reason=d.reason,
                       parent_decision_ids=d.parent_decision_ids, rule_id=d.rule_id,
                       rule_version=d.rule_version, source_bundle_hash=d.source_bundle_hash,
                       revision=d.revision, action=d.action)
        con.execute("INSERT INTO decision_events VALUES(?,?,?,?,?,?,?)",
                    (stable_id("event", (d.decision_id, event_kind, d.revision)),
                     d.run_id, d.decision_id, event_kind, _json(payload), d.revision, _utc()))
        con.execute("INSERT INTO decision_projection VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (d.decision_id, d.run_id, d.subject_id, d.state.value, _json(d.value),
                     d.actor, d.reviewed_at, d.reason, _json(d.parent_decision_ids),
                     d.rule_id, d.rule_version, d.source_bundle_hash, d.revision, d.action))

    def apply_user_decision(self, *, run_id: str, subject_id: str, value: object,
                            actor: str, reason: str, idempotency_key: str,
                            expected_revision: int) -> SemanticDecision:
        if not actor or not reason or not idempotency_key:
            raise ValueError("explicit actor, reason, idempotency key required")
        command_hash = stable_id("command", (run_id, subject_id, value, actor, reason, expected_revision))
        with self.write_transaction() as con:
            prior = con.execute("SELECT * FROM idempotency WHERE run_id=? AND key=?",
                                (run_id, idempotency_key)).fetchone()
            if prior is not None:
                if prior["command_hash"] != command_hash:
                    raise ConflictError("idempotency key used for a different command")
                decision_id = prior["decision_id"]
            else:
                run = self._check_revision(con, run_id, expected_revision)
                subject = self._subject(con, run_id, subject_id)
                decision_id = stable_id("decision", (run_id, subject_id, idempotency_key))
                d = SemanticDecision(decision_id, run_id, subject_id, value,
                                     DecisionState.USER_CONFIRMED, actor, _utc(), reason,
                                     (), None, None, run["bundle_hash"],
                                     expected_revision + 1, "APPLY")
                self._insert_decision(con, d, "APPLY")
                self._add_dependencies(con, d, subject)
                con.execute("INSERT INTO idempotency VALUES(?,?,?,?)",
                            (run_id, idempotency_key, command_hash, decision_id))
                con.execute("UPDATE runs SET revision=revision+1 WHERE run_id=?", (run_id,))
        return self.decision(decision_id)

    @staticmethod
    def _add_dependencies(con: sqlite3.Connection, d: SemanticDecision,
                          subject: sqlite3.Row) -> None:
        deps = [("SOURCE_SNAPSHOT", subject["source_snapshot_id"]),
                ("SOURCE_BUNDLE", d.source_bundle_hash),
                ("PARSER_VERSION", subject["parser_version"]),
                ("SCHEMA_VERSION", subject["schema_version"])]
        deps += [("PARENT_DECISION", pid) for pid in d.parent_decision_ids]
        if d.rule_id:
            deps.append(("RULE", d.rule_id + "@" + (d.rule_version or "")))
        for kind, key in deps:
            con.execute("INSERT OR IGNORE INTO decision_dependencies VALUES(?,?,?)",
                        (d.decision_id, kind, key))

    @staticmethod
    def _subject_has_blocker(con: sqlite3.Connection, run_id: str,
                             subject_id: str) -> bool:
        issue = con.execute(
            "SELECT 1 FROM validation_issues WHERE run_id=? AND subject_id=? AND code='VALUE_CONFLICT'",
            (run_id, subject_id)).fetchone()
        fact = con.execute(
            "SELECT 1 FROM fact_bindings WHERE run_id=? AND subject_id=? AND status!='DRAFT'",
            (run_id, subject_id)).fetchone()
        return issue is not None or fact is not None

    def derive_decision(self, *, run_id: str, subject_id: str, value: object,
                        parent_ids: tuple[str, ...], rule_id: str, rule_version: str,
                        expected_revision: int) -> SemanticDecision:
        if not parent_ids or not rule_id or not rule_version:
            raise ValueError("derived decision needs confirmed parents and deterministic rule")
        with self.write_transaction() as con:
            run = self._check_revision(con, run_id, expected_revision)
            subject = self._subject(con, run_id, subject_id)
            current_roles = {"CURRENT_DSD", "CURRENT_TAXONOMY",
                             "CURRENT_EXTENSION", "CURRENT_INSTANCE"}
            target_role = con.execute(
                "SELECT role FROM source_refs WHERE run_id=? AND snapshot_id=?",
                (run_id, subject["source_snapshot_id"])).fetchone()
            if target_role is None or target_role["role"] not in current_roles:
                raise ConflictError("derived target lacks current-source evidence")
            if self._subject_has_blocker(con, run_id, subject_id):
                raise ConflictError("target subject has a stale or conflicting fact")
            parent_values = []
            for parent_id in parent_ids:
                parent = con.execute("SELECT * FROM decision_projection WHERE decision_id=? AND run_id=?",
                                     (parent_id, run_id)).fetchone()
                if parent is None or parent["state"] not in (
                    DecisionState.USER_CONFIRMED.value, DecisionState.DERIVED_FROM_CONFIRMED.value
                ) or parent["bundle_hash"] != run["bundle_hash"]:
                    raise ConflictError("parent is not current confirmed evidence")
                parent_source = con.execute("""
                    SELECT r.role FROM semantic_subjects s JOIN source_refs r
                    ON r.run_id=s.run_id AND r.snapshot_id=s.source_snapshot_id
                    WHERE s.run_id=? AND s.subject_id=?""",
                    (run_id, parent["subject_id"])).fetchone()
                parent_subject = self._subject(con, run_id, parent["subject_id"])
                if parent_source is None or parent_source["role"] not in current_roles:
                    raise ConflictError("prior-only parent is not current confirmed evidence")
                if parent_subject["facet"] != subject["facet"]:
                    raise ConflictError("derived facet differs from parent facet")
                if self._subject_has_blocker(con, run_id, parent["subject_id"]):
                    raise ConflictError("parent subject has a stale or conflicting fact")
                parent_values.append(json.loads(parent["value_json"]))
            if not verify_derivation(rule_id, rule_version, tuple(parent_values), value):
                raise ConflictError("unregistered rule or non-deterministic derivation")
            decision_id = stable_id("derived-decision", (run_id, subject_id, value,
                                                         sorted(parent_ids), rule_id, rule_version,
                                                         run["bundle_hash"]))
            existing = con.execute("SELECT decision_id FROM decision_projection WHERE decision_id=?",
                                   (decision_id,)).fetchone()
            if existing is None:
                d = SemanticDecision(decision_id, run_id, subject_id, value,
                                     DecisionState.DERIVED_FROM_CONFIRMED, None, None,
                                     "deterministic rule", tuple(parent_ids), rule_id,
                                     rule_version, run["bundle_hash"],
                                     expected_revision + 1, "DERIVE")
                self._insert_decision(con, d, "DERIVE")
                self._add_dependencies(con, d, subject)
                con.execute("UPDATE runs SET revision=revision+1 WHERE run_id=?", (run_id,))
        return self.decision(decision_id)

    def decision(self, decision_id: str) -> SemanticDecision:
        with self.read_connection() as con:
            row = con.execute("SELECT * FROM decision_projection WHERE decision_id=?",
                              (decision_id,)).fetchone()
        if row is None:
            raise KeyError(decision_id)
        return SemanticDecision(row["decision_id"], row["run_id"], row["subject_id"],
                                json.loads(row["value_json"]), DecisionState(row["state"]),
                                row["actor"], row["reviewed_at"], row["reason"],
                                tuple(json.loads(row["parent_ids_json"])), row["rule_id"],
                                row["rule_version"], row["bundle_hash"], row["revision"],
                                row["action"])

    @staticmethod
    def _set_fact_status(con: sqlite3.Connection, run_id: str, fact_key: str,
                         status: str, reason: str, revision: int) -> bool:
        row = con.execute("SELECT status FROM fact_bindings WHERE run_id=? AND fact_key=?",
                          (run_id, fact_key)).fetchone()
        if row is None or row["status"] == status:
            return False
        if row["status"] == "CONFLICT" and status == "STALE":
            return False
        con.execute("UPDATE fact_bindings SET status=? WHERE run_id=? AND fact_key=?",
                    (status, run_id, fact_key))
        con.execute("""
            INSERT OR IGNORE INTO fact_status_events
            (event_id,run_id,fact_key,status,reason,revision) VALUES(?,?,?,?,?,?)""",
            (stable_id("fact-status", (run_id, fact_key, status, reason, revision)),
             run_id, fact_key, status, reason, revision))
        return True

    @classmethod
    def _stale_facts_for_decisions(cls, con: sqlite3.Connection, run_id: str,
                                   decision_ids: set[str], reason: str,
                                   revision: int) -> bool:
        changed = False
        if not decision_ids:
            return changed
        rows = con.execute("SELECT fact_key,decision_ids_json FROM fact_bindings WHERE run_id=?",
                           (run_id,)).fetchall()
        for row in rows:
            if decision_ids.intersection(json.loads(row["decision_ids_json"])):
                changed |= cls._set_fact_status(con, run_id, row["fact_key"],
                                                "STALE", reason, revision)
        return changed

    @classmethod
    def _invalidate(cls, con: sqlite3.Connection, run_id: str, seed_ids: set[str],
                    reason: str, revision: int, actor: str = "SYSTEM") -> set[str]:
        pending = list(seed_ids)
        seen: set[str] = set()
        while pending:
            decision_id = pending.pop()
            if decision_id in seen:
                continue
            seen.add(decision_id)
            row = con.execute("SELECT state FROM decision_projection WHERE decision_id=? AND run_id=?",
                              (decision_id, run_id)).fetchone()
            if row is None:
                continue
            if row["state"] != DecisionState.STALE.value:
                con.execute("UPDATE decision_projection SET state='STALE' WHERE decision_id=?",
                            (decision_id,))
                payload = _json({"decision_id": decision_id, "state": "STALE",
                                 "reason": reason, "actor": actor})
                con.execute("INSERT INTO decision_events VALUES(?,?,?,?,?,?,?)",
                            (stable_id("event", (decision_id, "INVALIDATE", revision, reason)),
                             run_id, decision_id, "INVALIDATE", payload, revision, _utc()))
            children = con.execute("""
                SELECT decision_id FROM decision_dependencies
                WHERE dependency_type='PARENT_DECISION' AND dependency_id=?""",
                (decision_id,)).fetchall()
            pending.extend(row[0] for row in children)
        cls._stale_facts_for_decisions(con, run_id, seen, reason, revision)
        return seen

    def invalidate_dependency(self, *, run_id: str, dependency_type: str,
                              dependency_id: str, reason: str) -> None:
        with self.write_transaction() as con:
            run = con.execute("SELECT revision FROM runs WHERE run_id=?", (run_id,)).fetchone()
            if run is None:
                raise KeyError(run_id)
            ids = {row[0] for row in con.execute("""
                SELECT d.decision_id FROM decision_dependencies d
                JOIN decision_projection p ON p.decision_id=d.decision_id
                WHERE p.run_id=? AND d.dependency_type=? AND d.dependency_id=?""",
                (run_id, dependency_type, dependency_id))}
            changed = False
            if ids:
                self._invalidate(con, run_id, ids, reason, run["revision"] + 1)
                changed = True
            fact_keys: list[str] = []
            if dependency_type == "SOURCE_BUNDLE":
                bundle = con.execute("SELECT bundle_hash FROM runs WHERE run_id=?",
                                     (run_id,)).fetchone()[0]
                if bundle == dependency_id:
                    fact_keys = [row[0] for row in con.execute(
                        "SELECT fact_key FROM fact_bindings WHERE run_id=?", (run_id,))]
            elif dependency_type in ("SOURCE_SNAPSHOT", "PARSER_VERSION", "SCHEMA_VERSION"):
                column = {"SOURCE_SNAPSHOT": "source_snapshot_id",
                          "PARSER_VERSION": "parser_version",
                          "SCHEMA_VERSION": "schema_version"}[dependency_type]
                fact_keys = [row[0] for row in con.execute(f"""
                    SELECT f.fact_key FROM fact_bindings f
                    JOIN semantic_subjects s ON s.run_id=f.run_id AND s.subject_id=f.subject_id
                    WHERE f.run_id=? AND s.{column}=?""",
                    (run_id, dependency_id))]
            for fact_key in fact_keys:
                changed |= self._set_fact_status(
                    con, run_id, fact_key, "STALE", reason, run["revision"] + 1)
            if changed:
                con.execute("UPDATE runs SET revision=revision+1 WHERE run_id=?", (run_id,))

    def invalidate_source(self, snapshot_id: str, *, reason: str) -> None:
        with self.read_connection() as con:
            run_ids = [row[0] for row in con.execute(
                "SELECT DISTINCT run_id FROM source_refs WHERE snapshot_id=?", (snapshot_id,))]
        for run_id in run_ids:
            self.invalidate_dependency(run_id=run_id, dependency_type="SOURCE_SNAPSHOT",
                                       dependency_id=snapshot_id, reason=reason)

    def undo_decision(self, decision_id: str, *, actor: str, reason: str,
                      expected_revision: int) -> None:
        if not actor or not reason:
            raise ValueError("undo needs actor and reason")
        with self.write_transaction() as con:
            parent = con.execute("SELECT * FROM decision_projection WHERE decision_id=?",
                                 (decision_id,)).fetchone()
            if parent is None:
                raise KeyError(decision_id)
            run_id = parent["run_id"]
            self._check_revision(con, run_id, expected_revision)
            self._invalidate(con, run_id, {decision_id}, "UNDO:" + reason,
                             expected_revision + 1, actor=actor)
            con.execute("UPDATE runs SET revision=revision+1 WHERE run_id=?", (run_id,))

    def bind_fact(self, run_id: str, key: FactSemanticKey, value: ValueSpec,
                  subject_id: str, *, role_occurrence_id: str | None = None,
                  decision_ids: tuple[str, ...] = ()) -> FactBinding | ValidationIssue:
        if value.kind == "numeric" and not key.unit:
            raise ValueError("numeric fact requires a unit")
        value_json = _json(value.__dict__)
        with self.write_transaction() as con:
            run_entity = con.execute(
                "SELECT entity,entity_scheme FROM runs WHERE run_id=?", (run_id,)).fetchone()
            if run_entity is None:
                raise KeyError(run_id)
            if (key.entity, key.entity_scheme) != (
                run_entity["entity"], run_entity["entity_scheme"]
            ):
                raise ConflictError("fact entity does not match run identity")
            self._subject(con, run_id, subject_id)
            prior = con.execute("SELECT * FROM fact_bindings WHERE run_id=? AND fact_key=?",
                                (run_id, key.key)).fetchone()
            if prior is not None and prior["value_json"] != value_json:
                issue_id = stable_id("issue", (run_id, key.key, prior["value_json"], value_json))
                detail = _json({"fact_key": key.key,
                                "existing_subject_id": prior["subject_id"],
                                "incoming_subject_id": subject_id,
                                "existing": json.loads(prior["value_json"]),
                                "incoming": value.__dict__})
                con.execute("INSERT OR IGNORE INTO validation_issues VALUES(?,?,?,?,?)",
                            (issue_id, run_id, "VALUE_CONFLICT", detail, subject_id))
                revision = con.execute("SELECT revision FROM runs WHERE run_id=?",
                                       (run_id,)).fetchone()[0]
                self._set_fact_status(con, run_id, key.key, "CONFLICT",
                                      "VALUE_CONFLICT", revision)
                return ValidationIssue(issue_id, run_id, "VALUE_CONFLICT", detail, subject_id)
            if prior is None:
                con.execute("INSERT INTO fact_bindings VALUES(?,?,?,?,?,?,?,?)",
                            (run_id, key.key, _json({"entity": key.entity, "entity_scheme": key.entity_scheme,
                             "qname": key.qname.key,
                             "period": key.period, "dimensions": key.dimensions, "unit": key.unit,
                             "language": key.language}), value_json, subject_id,
                             role_occurrence_id, _json(decision_ids), "DRAFT"))
        if prior is not None:
            if prior["status"] != "DRAFT":
                raise ConflictError("fact binding is stale or conflicting")
            return FactBinding(stable_id("binding", (run_id, key.key)), run_id, key,
                               ValueSpec(**json.loads(prior["value_json"])),
                               prior["subject_id"], prior["role_occurrence_id"],
                               tuple(json.loads(prior["decision_ids_json"])))
        return FactBinding(stable_id("binding", (run_id, key.key)), run_id, key,
                           value, subject_id, role_occurrence_id, decision_ids)

    def fact_value(self, run_id: str, key: FactSemanticKey) -> ValueSpec | None:
        with self.read_connection() as con:
            row = con.execute("SELECT value_json,status FROM fact_bindings WHERE run_id=? AND fact_key=?",
                              (run_id, key.key)).fetchone()
        if row is None:
            return None
        if row["status"] != "DRAFT":
            raise ConflictError("fact binding is stale or conflicting")
        return ValueSpec(**json.loads(row["value_json"]))

    def plan_artifact_set(self, *, run_id: str, expected_revision: int,
                          manifest_hash: str) -> ArtifactSet:
        # Identity shell only: V2-7 writer and Golden gate do not exist here.
        if len(manifest_hash) != 64 or any(c not in "0123456789abcdef" for c in manifest_hash):
            raise ValueError("manifest SHA-256 required")
        artifact_set_id = stable_id("artifact-set", (run_id, expected_revision, manifest_hash))
        with self.write_transaction() as con:
            self._check_revision(con, run_id, expected_revision)
            con.execute("INSERT OR IGNORE INTO artifact_sets VALUES(?,?,?,?,?)",
                        (artifact_set_id, run_id, expected_revision, "PLANNED", manifest_hash))
        return self.artifact_set(artifact_set_id)

    def artifact_set(self, artifact_set_id: str) -> ArtifactSet:
        with self.read_connection() as con:
            row = con.execute("SELECT * FROM artifact_sets WHERE artifact_set_id=?",
                              (artifact_set_id,)).fetchone()
        if row is None:
            raise KeyError(artifact_set_id)
        return ArtifactSet(row["artifact_set_id"], row["run_id"], row["revision"],
                           row["status"], row["manifest_hash"])

    def event_count(self, run_id: str) -> int:
        with self.read_connection() as con:
            return con.execute("SELECT count(*) FROM decision_events WHERE run_id=?",
                               (run_id,)).fetchone()[0]

    def issue_count(self, run_id: str) -> int:
        with self.read_connection() as con:
            return con.execute("SELECT count(*) FROM validation_issues WHERE run_id=?",
                               (run_id,)).fetchone()[0]

    def rebuild_projection(self, run_id: str) -> None:
        """Replay immutable events; the projection itself is never authoritative."""
        with self.write_transaction() as con:
            events = con.execute("SELECT * FROM decision_events WHERE run_id=? ORDER BY revision, occurred_at, event_id",
                                 (run_id,)).fetchall()
            con.execute("DELETE FROM decision_projection WHERE run_id=?", (run_id,))
            for event in events:
                payload = json.loads(event["payload_json"])
                if event["kind"] in ("APPLY", "DERIVE"):
                    con.execute("INSERT INTO decision_projection VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                (payload["decision_id"], payload["run_id"], payload["subject_id"],
                                 payload["state"], _json(payload["value"]), payload["actor"],
                                 payload["reviewed_at"], payload["reason"],
                                 _json(payload["parent_decision_ids"]), payload["rule_id"],
                                 payload["rule_version"], payload["source_bundle_hash"],
                                 payload["revision"], payload["action"]))
                elif event["kind"] == "INVALIDATE":
                    con.execute("UPDATE decision_projection SET state='STALE' WHERE decision_id=?",
                                (payload["decision_id"],))
            con.execute("UPDATE fact_bindings SET status='DRAFT' WHERE run_id=?", (run_id,))
            status_events = con.execute("""
                SELECT fact_key,status FROM fact_status_events WHERE run_id=?
                ORDER BY event_seq""", (run_id,)).fetchall()
            for event in status_events:
                con.execute("UPDATE fact_bindings SET status=? WHERE run_id=? AND fact_key=?",
                            (event["status"], run_id, event["fact_key"]))


class TaxonomyGraphStore:
    """V2-2 port shell. No graph parser or implicit persistent data."""

    def graph_snapshot(self, source_bundle_hash: str) -> object:
        raise NotImplementedError("taxonomy graph storage begins in V2-2")
