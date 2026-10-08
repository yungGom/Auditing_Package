"""V2-1 failure-first contracts. This file imports no legacy engine module."""
import gc
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest

from auditdesk.xbrl_v2.model import (
    DecisionState, ExpandedQName, FactSemanticKey, SourceBundle, SourceRef,
    SourceSnapshot, ValueSpec,
)
from auditdesk.xbrl_v2.storage import (
    ConflictError, RunStore, SourceStore, default_v2_root,
)


class CoreContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup_temp)
        self.root = Path(self.temp.name) / "xbrl_v2"
        self.sources = SourceStore(self.root)
        self.runs = RunStore(self.root)
        self.sources.initialize()
        self.runs.initialize()
        self.dsd = self.sources.register(
            kind="CURRENT_DSD", logical_uri="urn:report:dsd", data=b"first",
            storage_location="C:/input/current.dsd", parser_profile="raw-v1",
        )
        self.tax = self.sources.register(
            kind="CURRENT_TAXONOMY", logical_uri="urn:dart:2026", data=b"tax",
            storage_location="C:/input/tax.xlsx", parser_profile="raw-v1",
        )
        self.bundle = SourceBundle.create((
            SourceRef("CURRENT_DSD", self.dsd.snapshot_id),
            SourceRef("CURRENT_TAXONOMY", self.tax.snapshot_id),
        ))
        self.run = self.runs.create_run(
            bundle=self.bundle, entity_scheme="urn:dart:corpcode", entity="00126380", scope="CONNECTED",
            report_period="2026-06-30",
        )
        self.runs.add_subject(
            run_id=self.run.run_id, subject_id="subject-1",
            source_snapshot_id=self.dsd.snapshot_id, facet="LINE_ITEM",
        )

    def _cleanup_temp(self):
        # Windows can retain SQLite WAL shared-memory handles briefly after close.
        for attempt in range(20):
            try:
                self.temp.cleanup()
                return
            except OSError:
                gc.collect()
                time.sleep(0.1)
        self.temp.cleanup()

    def test_changed_bytes_same_path_new_snapshot(self):
        changed = self.sources.register(
            kind="CURRENT_DSD", logical_uri="urn:report:dsd", data=b"second",
            storage_location="C:/input/current.dsd", parser_profile="raw-v1",
        )
        self.assertNotEqual(self.dsd.snapshot_id, changed.snapshot_id)
        self.assertNotEqual(self.dsd.content_id, changed.content_id)

    def test_moved_path_same_bytes_preserves_content_identity(self):
        moved = self.sources.register(
            kind="CURRENT_DSD", logical_uri="urn:report:dsd", data=b"first",
            storage_location="D:/moved/current.dsd", parser_profile="raw-v1",
        )
        self.assertEqual(self.dsd.content_id, moved.content_id)
        self.assertEqual(self.dsd.snapshot_id, moved.snapshot_id)
        self.assertEqual(len(self.sources.locations(self.dsd.snapshot_id)), 2)

    def test_expanded_qname_namespace_identity(self):
        a = ExpandedQName("urn:company:a", "Cash")
        b = ExpandedQName("urn:company:b", "Cash")
        self.assertNotEqual(a, b)
        self.assertNotEqual(a.key, b.key)

    def test_deterministic_ids(self):
        again = SourceBundle.create(tuple(reversed(self.bundle.members)))
        self.assertEqual(self.bundle.bundle_hash, again.bundle_hash)
        self.assertEqual(self.run.run_id, self.runs.create_run(
            bundle=again, entity_scheme="urn:dart:corpcode", entity="00126380", scope="CONNECTED",
            report_period="2026-06-30").run_id)

    def test_proposal_cannot_implicitly_confirm(self):
        proposal = self.runs.suggest(
            run_id=self.run.run_id, subject_id="subject-1",
            value={"qname": "{urn:dart}Cash"}, evidence_kind="AI",
        )
        self.assertEqual(proposal.state, DecisionState.SUGGESTED)
        with self.assertRaises(ValueError):
            self.runs.apply_user_decision(
                run_id=self.run.run_id, subject_id="subject-1",
                value={"qname": "{urn:dart}Cash"}, actor="", reason="",
                idempotency_key="implicit", expected_revision=self.run.revision,
            )

    def _apply(self, key="k1", value=None, revision=None):
        return self.runs.apply_user_decision(
            run_id=self.run.run_id, subject_id="subject-1",
            value=value or {"qname": "{urn:dart}Cash"},
            actor="reviewer-1", reason="current source reviewed",
            idempotency_key=key,
            expected_revision=self.run.revision if revision is None else revision,
        )

    def test_idempotency_same_key_same_command(self):
        a = self._apply()
        b = self._apply()
        self.assertEqual(a.decision_id, b.decision_id)
        self.assertEqual(self.runs.event_count(self.run.run_id), 1)

    def test_idempotency_same_key_different_command_conflicts(self):
        self._apply()
        with self.assertRaises(ConflictError):
            self._apply(value={"qname": "{urn:dart}Other"})

    def test_stale_source_invalidates_dependent_projection(self):
        decision = self._apply()
        self.runs.invalidate_source(self.dsd.snapshot_id, reason="SOURCE_CHANGED")
        self.assertEqual(self.runs.decision(decision.decision_id).state, DecisionState.STALE)

    def test_parent_undo_invalidates_derived_child(self):
        parent = self._apply()
        self.runs.add_subject(
            run_id=self.run.run_id, subject_id="subject-2",
            source_snapshot_id=self.dsd.snapshot_id, facet="LINE_ITEM",
        )
        child = self.runs.derive_decision(
            run_id=self.run.run_id, subject_id="subject-2",
            value={"qname": "{urn:dart}Cash"}, parent_ids=(parent.decision_id,),
            rule_id="share-line-item", rule_version="1",
            expected_revision=self.runs.get_run(self.run.run_id).revision,
        )
        self.assertEqual(child.state, DecisionState.DERIVED_FROM_CONFIRMED)
        self.runs.undo_decision(
            parent.decision_id, actor="reviewer-1", reason="wrong mapping",
            expected_revision=self.runs.get_run(self.run.run_id).revision,
        )
        self.assertEqual(self.runs.decision(child.decision_id).state, DecisionState.STALE)

    def test_conflicting_fact_value_creates_issue(self):
        key = FactSemanticKey(
            entity_scheme="urn:dart:corpcode", entity="00126380", qname=ExpandedQName("urn:dart", "Cash"),
            period=("INSTANT", "2026-06-30"), dimensions=(), unit="iso4217:KRW",
        )
        self.runs.bind_fact(self.run.run_id, key, ValueSpec("100", "numeric"), "subject-1")
        issue = self.runs.bind_fact(
            self.run.run_id, key, ValueSpec("200", "numeric"), "subject-1")
        self.assertEqual(issue.code, "VALUE_CONFLICT")
        with self.assertRaises(ConflictError):
            self.runs.fact_value(self.run.run_id, key)

    def test_missing_source_explicit(self):
        bundle = SourceBundle.create((
            SourceRef("CURRENT_DSD", self.dsd.snapshot_id),
            SourceRef("CURRENT_TAXONOMY", None, missing_reason="NOT_PROVIDED"),
        ))
        self.assertEqual(bundle.missing[0].missing_reason, "NOT_PROVIDED")
        self.assertNotEqual(bundle.bundle_hash, self.bundle.bundle_hash)

    def test_restart_interrupts_running(self):
        self.runs.mark_running(self.run.run_id)
        reopened = RunStore(self.root)
        reopened.initialize()
        self.assertEqual(reopened.get_run(self.run.run_id).status, "INTERRUPTED")

    def test_legacy_db_untouched(self):
        legacy = self.root.parent / "app.sqlite"
        legacy.write_bytes(b"legacy marker")
        before = hashlib.sha256(legacy.read_bytes()).hexdigest()
        self.sources.register(
            kind="OTHER", logical_uri="urn:other", data=b"data",
            storage_location="X:/file", parser_profile="raw-v1",
        )
        self.assertEqual(hashlib.sha256(legacy.read_bytes()).hexdigest(), before)

    def test_v2_root_separate(self):
        self.assertEqual(default_v2_root().name, "xbrl_v2")
        self.assertNotEqual(self.sources.db_path, self.runs.db_path)
        self.assertTrue(self.root in self.sources.db_path.parents)
        self.assertTrue(self.root in self.runs.db_path.parents)

    def test_read_paths_do_not_execute_ddl(self):
        statements = []
        with self.runs.read_connection(trace=statements.append) as con:
            con.execute("SELECT run_id FROM runs WHERE run_id=?", (self.run.run_id,)).fetchone()
        self.assertFalse(any("CREATE " in s.upper() or "ALTER " in s.upper()
                             for s in statements))

    def test_transaction_rollback_preserves_committed_state(self):
        self._apply()
        before = self.runs.event_count(self.run.run_id)
        with self.assertRaises(RuntimeError):
            with self.runs.write_transaction() as con:
                con.execute("INSERT INTO validation_issues(run_id, code, detail) VALUES(?,?,?)",
                            (self.run.run_id, "TEST", "{}"))
                raise RuntimeError("abort")
        self.assertEqual(self.runs.event_count(self.run.run_id), before)
        self.assertEqual(self.runs.issue_count(self.run.run_id), 0)


    def test_answer_role_cannot_enter_bundle(self):
        with self.assertRaises(ValueError):
            SourceBundle.create((
                SourceRef("CURRENT_DSD", self.dsd.snapshot_id),
                SourceRef("CURRENT_TAXONOMY", self.tax.snapshot_id),
                SourceRef("ANSWER_GOLDEN", "answer-snapshot"),
            ))

    def test_prior_only_cannot_derive(self):
        with self.assertRaises(ConflictError):
            self.runs.derive_decision(
                run_id=self.run.run_id, subject_id="subject-1",
                value={"qname": "{urn:dart}Cash"}, parent_ids=("prior-answer",),
                rule_id="copy-prior", rule_version="1",
                expected_revision=self.run.revision,
            )

    def test_event_projection_rebuild_preserves_stale(self):
        decision = self._apply()
        self.runs.invalidate_source(self.dsd.snapshot_id, reason="SOURCE_CHANGED")
        self.runs.rebuild_projection(self.run.run_id)
        self.assertEqual(self.runs.decision(decision.decision_id).state, DecisionState.STALE)

    def test_rule_version_invalidation(self):
        parent = self._apply()
        child = self.runs.derive_decision(
            run_id=self.run.run_id, subject_id="subject-1",
            value={"qname": "{urn:dart}Cash"}, parent_ids=(parent.decision_id,),
            rule_id="share-line-item", rule_version="1",
            expected_revision=self.runs.get_run(self.run.run_id).revision,
        )
        self.runs.invalidate_dependency(
            run_id=self.run.run_id, dependency_type="RULE",
            dependency_id="share-line-item@1", reason="RULE_CHANGED",
        )
        self.assertEqual(self.runs.decision(child.decision_id).state, DecisionState.STALE)

    def test_numeric_fact_requires_unit(self):
        key = FactSemanticKey(
            entity_scheme="urn:dart:corpcode", entity="00126380", qname=ExpandedQName("urn:dart", "Cash"),
            period=("INSTANT", "2026-06-30"), dimensions=(), unit=None,
        )
        with self.assertRaises(ValueError):
            self.runs.bind_fact(self.run.run_id, key, ValueSpec("100", "numeric"), "subject-1")

    def test_unknown_v2_schema_does_not_migrate(self):
        other = self.root.parent / "unknown-v2"
        other.mkdir()
        path = other / "engine.sqlite"
        con = sqlite3.connect(path)
        try:
            con.execute("CREATE TABLE sentinel(value TEXT)")
            con.execute("INSERT INTO sentinel VALUES('preserved')")
            con.execute("PRAGMA user_version=99")
            con.commit()
        finally:
            con.close()
        before = path.read_bytes()
        with self.assertRaises(RuntimeError):
            RunStore(other).initialize()
        con = sqlite3.connect(path)
        try:
            self.assertEqual(con.execute("SELECT value FROM sentinel").fetchone()[0], "preserved")
            self.assertEqual(con.execute("PRAGMA user_version").fetchone()[0], 99)
            self.assertIsNone(con.execute(
                "SELECT name FROM sqlite_master WHERE name='runs'").fetchone())
        finally:
            con.close()
    def test_suggestion_preserves_facet(self):
        proposal = self.runs.suggest(
            run_id=self.run.run_id, subject_id="subject-1",
            value={"qname": "{urn:dart}Cash"}, evidence_kind="CURRENT_SOURCE",
        )
        self.assertEqual(proposal.facet, "LINE_ITEM")

    def test_parser_schema_version_impact_edges(self):
        self.runs.add_subject(
            run_id=self.run.run_id, subject_id="versioned",
            source_snapshot_id=self.dsd.snapshot_id, facet="LINE_ITEM",
            parser_version="lexical-v1", schema_version="domain-v1",
        )
        decision = self.runs.apply_user_decision(
            run_id=self.run.run_id, subject_id="versioned",
            value={"qname": "{urn:dart}Cash"}, actor="reviewer-1",
            reason="reviewed", idempotency_key="versioned",
            expected_revision=self.run.revision,
        )
        self.runs.invalidate_dependency(
            run_id=self.run.run_id, dependency_type="PARSER_VERSION",
            dependency_id="lexical-v1", reason="PARSER_CHANGED",
        )
        self.assertEqual(self.runs.decision(decision.decision_id).state, DecisionState.STALE)

    def test_undo_event_retains_actor(self):
        decision = self._apply()
        self.runs.undo_decision(
            decision.decision_id, actor="reviewer-2", reason="incorrect",
            expected_revision=self.runs.get_run(self.run.run_id).revision,
        )
        with self.runs.read_connection() as con:
            row = con.execute(
                "SELECT payload_json FROM decision_events WHERE decision_id=? AND kind='INVALIDATE'",
                (decision.decision_id,),
            ).fetchone()
        self.assertEqual(json.loads(row[0])["actor"], "reviewer-2")

    def test_same_value_duplicate_preserves_original_binding(self):
        key = FactSemanticKey(
            entity_scheme="urn:dart:corpcode", entity="00126380", qname=ExpandedQName("urn:dart", "Cash"),
            period=("INSTANT", "2026-06-30"), dimensions=(), unit="iso4217:KRW",
        )
        self.runs.add_subject(
            run_id=self.run.run_id, subject_id="subject-2",
            source_snapshot_id=self.dsd.snapshot_id, facet="LINE_ITEM",
        )
        first = self.runs.bind_fact(self.run.run_id, key, ValueSpec("100", "numeric"), "subject-1")
        repeated = self.runs.bind_fact(self.run.run_id, key, ValueSpec("100", "numeric"), "subject-2")
        self.assertEqual(repeated.subject_id, first.subject_id)

    def test_run_rejects_unregistered_or_mislabeled_source(self):
        fake = SourceBundle.create((
            SourceRef("CURRENT_DSD", "answer-golden-snapshot"),
            SourceRef("CURRENT_TAXONOMY", self.tax.snapshot_id),
        ))
        with self.assertRaises(ConflictError):
            self.runs.create_run(
                bundle=fake, entity_scheme="urn:dart:corpcode", entity="00126380", scope="CONNECTED",
                report_period="2026-06-30",
            )
        answer = self.sources.register(
            kind="ANSWER_GOLDEN", logical_uri="urn:answer", data=b"answer",
            storage_location="X:/golden.xls", parser_profile="raw-v1",
        )
        mislabeled = SourceBundle.create((
            SourceRef("CURRENT_DSD", answer.snapshot_id),
            SourceRef("CURRENT_TAXONOMY", self.tax.snapshot_id),
        ))
        with self.assertRaises(ConflictError):
            self.runs.create_run(
                bundle=mislabeled, entity_scheme="urn:dart:corpcode", entity="00126380", scope="CONNECTED",
                report_period="2026-06-30",
            )

    def test_prior_only_parent_cannot_derive_current(self):
        prior = self.sources.register(
            kind="PRIOR_COMPANY_XBRL", logical_uri="urn:prior", data=b"prior",
            storage_location="X:/prior.xbrl", parser_profile="raw-v1",
        )
        bundle = SourceBundle.create((
            SourceRef("CURRENT_DSD", self.dsd.snapshot_id),
            SourceRef("CURRENT_TAXONOMY", self.tax.snapshot_id),
            SourceRef("PRIOR_COMPANY_XBRL", prior.snapshot_id),
        ))
        run = self.runs.create_run(
            bundle=bundle, entity_scheme="urn:dart:corpcode", entity="00126380", scope="CONNECTED",
            report_period="2026-06-30",
        )
        self.runs.add_subject(
            run_id=run.run_id, subject_id="prior-subject",
            source_snapshot_id=prior.snapshot_id, facet="LINE_ITEM",
        )
        self.runs.add_subject(
            run_id=run.run_id, subject_id="current-subject",
            source_snapshot_id=self.dsd.snapshot_id, facet="LINE_ITEM",
        )
        parent = self.runs.apply_user_decision(
            run_id=run.run_id, subject_id="prior-subject",
            value={"qname": "{urn:prior}Cash"}, actor="reviewer-1",
            reason="prior inspected", idempotency_key="prior-confirm",
            expected_revision=0,
        )
        with self.assertRaises(ConflictError):
            self.runs.derive_decision(
                run_id=run.run_id, subject_id="current-subject",
                value={"qname": "{urn:prior}Cash"},
                parent_ids=(parent.decision_id,), rule_id="reuse",
                rule_version="1", expected_revision=1,
            )

    def test_stale_source_fact_cannot_be_read_as_normal(self):
        key = FactSemanticKey(
            entity_scheme="urn:dart:corpcode", entity="00126380", qname=ExpandedQName("urn:dart", "Cash"),
            period=("INSTANT", "2026-06-30"), dimensions=(), unit="iso4217:KRW",
        )
        self.runs.bind_fact(self.run.run_id, key, ValueSpec("100", "numeric"), "subject-1")
        self.runs.invalidate_source(self.dsd.snapshot_id, reason="SOURCE_CHANGED")
        with self.assertRaises(ConflictError):
            self.runs.fact_value(self.run.run_id, key)

    def test_parent_undo_invalidates_bound_fact(self):
        parent = self._apply()
        key = FactSemanticKey(
            entity_scheme="urn:dart:corpcode", entity="00126380", qname=ExpandedQName("urn:dart", "Cash"),
            period=("INSTANT", "2026-06-30"), dimensions=(), unit="iso4217:KRW",
        )
        self.runs.bind_fact(
            self.run.run_id, key, ValueSpec("100", "numeric"),
            "subject-1", decision_ids=(parent.decision_id,),
        )
        self.runs.undo_decision(
            parent.decision_id, actor="reviewer-1", reason="wrong",
            expected_revision=self.runs.get_run(self.run.run_id).revision,
        )
        with self.assertRaises(ConflictError):
            self.runs.fact_value(self.run.run_id, key)

    def test_unregistered_derivation_rule_rejected(self):
        parent = self._apply()
        with self.assertRaises(ConflictError):
            self.runs.derive_decision(
                run_id=self.run.run_id, subject_id="subject-1",
                value={"qname": "{urn:dart}Cash"},
                parent_ids=(parent.decision_id,), rule_id="arbitrary-rule",
                rule_version="1",
                expected_revision=self.runs.get_run(self.run.run_id).revision,
            )

    def test_registered_rule_rejects_non_deterministic_output(self):
        parent = self._apply()
        with self.assertRaises(ConflictError):
            self.runs.derive_decision(
                run_id=self.run.run_id, subject_id="subject-1",
                value={"qname": "{urn:dart}Other"},
                parent_ids=(parent.decision_id,), rule_id="share-line-item",
                rule_version="1",
                expected_revision=self.runs.get_run(self.run.run_id).revision,
            )

    def test_conflict_blocks_derived_decision(self):
        parent = self._apply()
        key = FactSemanticKey(
            entity_scheme="urn:dart:corpcode", entity="00126380", qname=ExpandedQName("urn:dart", "Cash"),
            period=("INSTANT", "2026-06-30"), dimensions=(), unit="iso4217:KRW",
        )
        self.runs.bind_fact(self.run.run_id, key, ValueSpec("100", "numeric"), "subject-1")
        self.runs.bind_fact(self.run.run_id, key, ValueSpec("200", "numeric"), "subject-1")
        with self.assertRaises(ConflictError):
            self.runs.derive_decision(
                run_id=self.run.run_id, subject_id="subject-1",
                value=parent.value, parent_ids=(parent.decision_id,),
                rule_id="share-line-item", rule_version="1",
                expected_revision=self.runs.get_run(self.run.run_id).revision,
            )

    def test_fact_status_rebuild_retains_conflict(self):
        key = FactSemanticKey(
            entity_scheme="urn:dart:corpcode", entity="00126380", qname=ExpandedQName("urn:dart", "Cash"),
            period=("INSTANT", "2026-06-30"), dimensions=(), unit="iso4217:KRW",
        )
        self.runs.bind_fact(self.run.run_id, key, ValueSpec("100", "numeric"), "subject-1")
        self.runs.bind_fact(self.run.run_id, key, ValueSpec("200", "numeric"), "subject-1")
        self.runs.rebuild_projection(self.run.run_id)
        with self.assertRaises(ConflictError):
            self.runs.fact_value(self.run.run_id, key)

    def test_evidence_ref_requires_raw_hash_and_versions(self):
        from auditdesk.xbrl_v2.provenance import EvidenceRef
        ref = EvidenceRef(
            source_snapshot_id=self.dsd.snapshot_id, logical_uri="urn:report:dsd",
            locator="contents.xml#16385:16393", raw_sha256=self.dsd.content_id,
            parser_version="raw-v1", rule_version="identity-v1",
        )
        self.assertEqual(ref.source_snapshot_id, self.dsd.snapshot_id)
        with self.assertRaises(ValueError):
            EvidenceRef(
                source_snapshot_id=self.dsd.snapshot_id, logical_uri="urn:report:dsd",
                locator="contents.xml#1:2", raw_sha256="bad",
                parser_version="raw-v1", rule_version="identity-v1",
            )

    def test_parser_schema_bundle_changes_stale_fact_without_decision(self):
        for dependency_type, dependency_id in (
            ("PARSER_VERSION", "identity-shell-v1"),
            ("SCHEMA_VERSION", "domain-v1"),
            ("SOURCE_BUNDLE", self.bundle.bundle_hash),
        ):
            with self.subTest(dependency_type=dependency_type):
                key = FactSemanticKey(
                    entity_scheme="urn:dart:corpcode", entity="00126380",
                    qname=ExpandedQName("urn:dart", dependency_type),
                    period=("INSTANT", "2026-06-30"),
                    dimensions=(), unit="iso4217:KRW",
                )
                self.runs.bind_fact(
                    self.run.run_id, key, ValueSpec("100", "numeric"), "subject-1")
                self.runs.invalidate_dependency(
                    run_id=self.run.run_id,
                    dependency_type=dependency_type,
                    dependency_id=dependency_id,
                    reason="VERSION_CHANGED",
                )
                with self.assertRaises(ConflictError):
                    self.runs.fact_value(self.run.run_id, key)

    def test_original_subject_conflict_blocks_derivation(self):
        parent = self._apply()
        self.runs.add_subject(
            run_id=self.run.run_id, subject_id="subject-2",
            source_snapshot_id=self.dsd.snapshot_id, facet="LINE_ITEM",
        )
        key = FactSemanticKey(
            entity_scheme="urn:dart:corpcode", entity="00126380", qname=ExpandedQName("urn:dart", "Cash"),
            period=("INSTANT", "2026-06-30"), dimensions=(), unit="iso4217:KRW",
        )
        self.runs.bind_fact(self.run.run_id, key, ValueSpec("100", "numeric"), "subject-1")
        self.runs.bind_fact(self.run.run_id, key, ValueSpec("200", "numeric"), "subject-2")
        with self.assertRaises(ConflictError):
            self.runs.derive_decision(
                run_id=self.run.run_id, subject_id="subject-1",
                value=parent.value, parent_ids=(parent.decision_id,),
                rule_id="share-line-item", rule_version="1",
                expected_revision=self.runs.get_run(self.run.run_id).revision,
            )

    def test_artifact_manifest_shell_is_planned_only(self):
        planned = self.runs.plan_artifact_set(
            run_id=self.run.run_id, expected_revision=self.run.revision,
            manifest_hash="a" * 64,
        )
        self.assertEqual(planned.status, "PLANNED")
        self.assertEqual(self.runs.artifact_set(planned.artifact_set_id), planned)
        self.assertFalse((self.root / "artifacts").exists())

    def test_entity_scheme_is_part_of_fact_identity(self):
        common = dict(
            entity="00126380", qname=ExpandedQName("urn:dart", "Cash"),
            period=("INSTANT", "2026-06-30"), dimensions=(), unit="iso4217:KRW",
        )
        a = FactSemanticKey(entity_scheme="urn:scheme:a", **common)
        b = FactSemanticKey(entity_scheme="urn:scheme:b", **common)
        self.assertNotEqual(a.key, b.key)

    def test_fact_cannot_cross_run_entity_or_scheme(self):
        for scheme, entity in (
            ("urn:other:scheme", "00126380"),
            ("urn:dart:corpcode", "different-company"),
        ):
            with self.subTest(scheme=scheme, entity=entity):
                key = FactSemanticKey(
                    entity_scheme=scheme, entity=entity,
                    qname=ExpandedQName("urn:dart", "Cash"),
                    period=("INSTANT", "2026-06-30"),
                    dimensions=(), unit="iso4217:KRW",
                )
                with self.assertRaises(ConflictError):
                    self.runs.bind_fact(
                        self.run.run_id, key, ValueSpec("100", "numeric"), "subject-1")

if __name__ == "__main__":
    unittest.main()
