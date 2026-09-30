"""Current-source recommendation only; never creates decisions or XBRL facts."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import date
import re
import unicodedata
from .model import stable_id
from .dsd import DsdReportContext, DsdMetadata, DsdCoverage, parse_dsd
from .taxonomy import TaxonomyMetadata, NamespaceBinding, WorkbookLocation, TaxonomyReference, parse_taxonomy_workbook

RULE_VERSION = 'current-first-workbook-recommendation/1'
MAX_CANDIDATES = 50
MAX_REJECTIONS = 50


@dataclass(frozen=True)
class RecommendationConstraint:
    subject_id: str
    source_snapshot_id: str
    role_uri: str | None = None
    period_type: str | None = None
    type_name: str | None = None
    dimensions: tuple[tuple[str, str], ...] = ()

    def __post_init__(self):
        if isinstance(self.dimensions, (str, bytes)):
            raise ValueError('Invalid dimensions')
        object.__setattr__(self, 'dimensions', tuple(tuple(d) for d in self.dimensions))


@dataclass(frozen=True)
class ReferenceEvidence:
    evidence_id: str
    source_kind: str
    source_sha256: str
    entity_scheme: str
    entity_identifier: str
    scope: str
    period_end: str
    qname: str
    role_uri: str
    label: str
    type_name: str
    period_type: str
    path: tuple[str, ...]

    def __post_init__(self):
        if isinstance(self.path, (str, bytes)) or not all(isinstance(p, str) for p in self.path):
            raise ValueError('Invalid occurrence path')
        object.__setattr__(self, 'path', tuple(self.path))


@dataclass(frozen=True)
class ReferenceValidation:
    evidence: ReferenceEvidence
    state: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class Candidate:
    qname: str
    role_uri: str
    path: tuple[str, ...]
    occurrence_id: str
    label: str
    label_resource_id: str
    current_score: float
    current_validation: str
    reference_resource_ids: tuple[str, ...]
    unverified: tuple[str, ...]
    occurrence_source: WorkbookLocation
    label_source: WorkbookLocation
    reference_resources: tuple[TaxonomyReference, ...]
    evidence_reasons: tuple[str, ...]


@dataclass(frozen=True)
class RejectedCandidate:
    qname: str
    role_uri: str
    path: tuple[str, ...]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class RoleProposal:
    role_uri: str
    definition: str
    source: WorkbookLocation
    evidence_reasons: tuple[str, ...]


@dataclass(frozen=True)
class SubjectRecommendation:
    subject_id: str
    state: str
    candidates: tuple[Candidate, ...]
    rejected: tuple[RejectedCandidate, ...]
    references: tuple[ReferenceValidation, ...]
    ambiguous: bool
    source_text: str
    source_value_state: str
    diagnostics: tuple[str, ...]
    source_span: tuple[int, int]
    table_id: str | None
    row: int | None
    column: int | None
    role_candidates: tuple[RoleProposal, ...]
    evaluated_occurrences: int
    excluded_role_count: int
    candidate_total: int
    rejection_total: int


@dataclass(frozen=True)
class RecommendationCoverage:
    total: int
    suggested: int
    unresolved: int
    conflicts: int


@dataclass(frozen=True)
class RecommendationResult:
    request_fingerprint: str
    rule_version: str
    source_snapshot_id: str
    taxonomy_snapshot_id: str | None
    subjects: tuple[SubjectRecommendation, ...]
    coverage: RecommendationCoverage
    diagnostics: tuple[str, ...]
    source_sha256: str
    taxonomy_sha256: str | None
    report_metadata: DsdMetadata
    taxonomy_metadata: TaxonomyMetadata | None
    source_coverage: DsdCoverage
    current_validation: str = 'PARTIAL'


def _fingerprint(document, taxonomy, constraints, references, rule_version):
    return stable_id('recommendation-request', (asdict(document), asdict(taxonomy) if taxonomy else None,
                     [asdict(c) for c in constraints], [asdict(r) for r in references], rule_version))


def assert_fresh(result, document, taxonomy, *, constraints=(), references=(), rule_version=RULE_VERSION):
    """Caller supplies the latest complete source set, including manual inputs."""
    if result.request_fingerprint != _fingerprint(document, taxonomy, constraints, references, rule_version):
        raise ValueError('STALE: recommendation sources, metadata, rules or review inputs changed')


def _normal(text):
    return ''.join(c for c in unicodedata.normalize('NFKC', text).casefold() if c.isalnum())


def _score(source, target):
    a, b = _normal(source), _normal(target)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if a in b or b in a:
        return min(len(a), len(b)) / max(len(a), len(b))
    return 0.0


def _iso(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('ISO date required')
    return date.fromisoformat(value)


def _source_status(document, taxonomy):
    diagnostics = list(document.diagnostics)
    conflict = any(d.startswith('CONFLICT:') for d in document.diagnostics)
    missing = False
    if document.source_role != 'CURRENT_DSD':
        diagnostics.append('CURRENT_DSD_SOURCE_REQUIRED'); missing = True
    requested = document.metadata.requested
    for field in ('entity_scheme', 'entity_identifier', 'scope', 'period_start', 'period_end'):
        if not getattr(requested, field):
            diagnostics.append('REPORT_CONTEXT_MISSING:' + field); missing = True
        observed = getattr(document.metadata.observed, field)
        if not observed:
            diagnostics.append('CURRENT_OBSERVATION_UNKNOWN:' + field)
        if observed and getattr(requested, field) and observed != getattr(requested, field):
            diagnostics.append('CONFLICT:' + field); conflict = True
    if taxonomy is None:
        diagnostics.append('CURRENT_TAXONOMY_MISSING'); missing = True
    else:
        diagnostics.extend('TAXONOMY:' + d.code for d in taxonomy.diagnostics)
        meta = taxonomy.metadata
        if (not taxonomy.current_applicable or any(d.severity == 'ERROR' for d in taxonomy.diagnostics)
                or meta.source_role != 'CURRENT_TAXONOMY' or meta.content_sha256 != taxonomy.content_sha256
                or not meta.applicability_evidence.strip() or not meta.version.strip()):
            diagnostics.append('CURRENT_TAXONOMY_UNVERIFIED'); missing = True
        try:
            if not _iso(meta.applicable_from) <= _iso(meta.report_period) <= _iso(meta.applicable_to):
                diagnostics.append('TAXONOMY_APPLICABILITY_CONFLICT'); conflict = True
            if requested.period_end and meta.report_period != requested.period_end:
                diagnostics.append('TAXONOMY_REPORT_PERIOD_CONFLICT'); conflict = True
        except (ValueError, TypeError):
            diagnostics.append('TAXONOMY_APPLICABILITY_UNKNOWN'); missing = True
    return ('CONFLICT' if conflict else ('UNRESOLVED' if missing else None)), tuple(diagnostics)


def _validate_reference(reference, candidates, concepts, requested, blocked=False):
    reasons = []
    if blocked:
        return ReferenceValidation(reference, 'UNVERIFIED', ('CURRENT_SOURCE_UNAVAILABLE',))
    if reference.source_kind == 'PRIOR_COMPANY_XBRL':
        for key in ('entity_scheme', 'entity_identifier', 'scope'):
            if not getattr(reference, key) or getattr(reference, key) != getattr(requested, key):
                reasons.append('PRIOR_' + key.upper() + '_MISMATCH')
        try:
            if _iso(reference.period_end) >= _iso(requested.period_start):
                reasons.append('PRIOR_PERIOD_NOT_EARLIER')
        except (ValueError, TypeError):
            reasons.append('PRIOR_PERIOD_UNKNOWN')
    # A corpus can be from another entity, but is never authoritative for it.
    matches = [c for c in candidates if (c.qname, c.role_uri, c.path) == (reference.qname, reference.role_uri, reference.path)]
    if not matches:
        reasons.append('CURRENT_QNAME_ROLE_PATH_NOT_ELIGIBLE')
    concept = concepts.get(reference.qname)
    if concept is None:
        reasons.append('CURRENT_CONCEPT_MISSING')
    else:
        if not reference.type_name or not concept.type_name:
            reasons.append('TYPE_UNKNOWN')
        elif reference.type_name != concept.type_name:
            reasons.append('TYPE_MISMATCH')
        if not reference.period_type or not concept.period_type:
            reasons.append('PERIOD_TYPE_UNKNOWN')
        elif reference.period_type != concept.period_type:
            reasons.append('PERIOD_TYPE_MISMATCH')
    invalid = bool(reasons)
    if matches and reference.label not in {c.label for c in matches}:
        reasons.append('LABEL_CHANGED')
    reasons.append('CURRENT_VALIDATION_PARTIAL')
    if reference.source_kind == 'REFERENCE_CORPUS':
        reasons.append('SUPPLEMENTAL_CORPUS_ONLY')
    return ReferenceValidation(reference, 'UNVERIFIED' if invalid else 'REVALIDATED', tuple(reasons))


def recommend(document, taxonomy, *, constraints=(), references=(), rule_version=RULE_VERSION):
    constraints, references = tuple(constraints), tuple(references)
    subject_ids = {s.subject_id for s in document.subjects}
    if len(subject_ids) != len(document.subjects):
        raise ValueError('Duplicate source subject identity')
    by_subject = {}
    for c in constraints:
        if c.subject_id not in subject_ids or c.subject_id in by_subject or c.source_snapshot_id != document.snapshot_id:
            raise ValueError('Constraint requires unique current snapshot and subject identity')
        if c.period_type not in (None, 'instant', 'duration'):
            raise ValueError('Invalid period constraint')
        if any(len(d) != 2 or not all(isinstance(v, str) and v for v in d) for d in c.dimensions):
            raise ValueError('Invalid dimensions constraint')
        by_subject[c.subject_id] = c
    ref_ids = set()
    for r in references:
        if r.source_kind not in ('PRIOR_COMPANY_XBRL', 'REFERENCE_CORPUS'):
            raise ValueError('Unsupported reference evidence kind')
        if not r.evidence_id or r.evidence_id in ref_ids or not re.fullmatch('[a-fA-F0-9]{64}', r.source_sha256):
            raise ValueError('Reference requires unique identity and source hash')
        ref_ids.add(r.evidence_id)
    if not rule_version:
        raise ValueError('Rule version required')
    if len(references) > 2000 or len(references) * len(document.subjects) > 100000:
        raise ValueError('Reference review workload limit exceeded')
    blocked, diagnostics = _source_status(document, taxonomy)
    concepts = {c.qname.key: c for c in taxonomy.concepts if c.qname} if taxonomy else {}
    labels, role_occurrences, role_definitions, resources = {}, {}, {}, {}
    if taxonomy:
        role_definitions = {r.role_uri: r for r in taxonomy.roles}
        for occurrence in taxonomy.occurrences:
            role_occurrences.setdefault(occurrence.role_uri, []).append(occurrence)
        for label in taxonomy.labels:
            if label.qname:
                labels.setdefault(label.qname.key, []).append(label)
        for resource in taxonomy.references:
            if resource.qname:
                resources.setdefault(resource.qname.key, []).append(resource)
    role_cache, label_cache = {}, {}
    results = []
    total_evaluated = 0
    for subject in document.subjects:
        constraint = by_subject.get(subject.subject_id)
        candidates, rejected, subject_diagnostics, proposals = [], [], [], []
        evaluated = excluded = rejection_total = 0
        def reject(occurrence, reasons):
            nonlocal rejection_total
            rejection_total += 1
            if len(rejected) < MAX_REJECTIONS:
                rejected.append(RejectedCandidate(occurrence.qname.key, occurrence.role_uri, occurrence.path, tuple(reasons)))
        if not blocked:
            if constraint and constraint.role_uri:
                roles = {constraint.role_uri} if constraint.role_uri in role_definitions else set()
                role_reason = 'CURRENT_SNAPSHOT_MANUAL_ROLE_CONSTRAINT'
            else:
                title = subject.table_title or (subject.text if subject.kind == 'TITLE' else '')
                if title not in role_cache:
                    role_cache[title] = {r.role_uri for r in taxonomy.roles if _score(title, r.definition) > 0}
                roles = role_cache[title]
                role_reason = 'CURRENT_DSD_TITLE_MATCHES_ROLE_DEFINITION'
            compatible_roles = set()
            for uri in roles:
                definition = role_definitions[uri].definition
                observed_scope = 'CONNECTED' if '연결' in definition else ('SEPARATE' if ('별도' in definition or '개별' in definition) else None)
                if observed_scope and observed_scope != document.metadata.requested.scope:
                    subject_diagnostics.append('ROLE_SCOPE_MISMATCH')
                else:
                    compatible_roles.add(uri)
            roles = compatible_roles
            proposals = [RoleProposal(uri, role_definitions[uri].definition, role_definitions[uri].source, (role_reason,)) for uri in sorted(roles)]
            if not roles:
                subject_diagnostics.append('NO_ROLE_CANDIDATE')
            evaluated = sum(len(role_occurrences.get(uri, ())) for uri in roles)
            total_evaluated += evaluated
            if total_evaluated > 2000000:
                raise ValueError('Recommendation structural workload limit exceeded')
            excluded = len(taxonomy.occurrences) - evaluated
            if excluded:
                subject_diagnostics.append('OUTSIDE_CANDIDATE_ROLES_EXCLUDED')
            source_labels = subject.row_headers or (subject.text,)
            for role_uri in sorted(roles):
                for occurrence in role_occurrences.get(role_uri, ()):
                    if not occurrence.qname:
                        subject_diagnostics.append('UNRESOLVED_OCCURRENCE_QNAME')
                        continue
                    qname = occurrence.qname.key
                    concept = concepts.get(qname)
                    reasons = []
                    if concept is None:
                        reasons.append('CONCEPT_UNRESOLVED')
                    else:
                        if concept.abstract is True:
                            reasons.append('ABSTRACT_CONCEPT')
                        if constraint and constraint.period_type and concept.period_type and constraint.period_type != concept.period_type:
                            reasons.append('PERIOD_TYPE_MISMATCH')
                        if constraint and constraint.type_name and concept.type_name and constraint.type_name != concept.type_name:
                            reasons.append('TYPE_MISMATCH')
                    if reasons:
                        reject(occurrence, reasons)
                        continue
                    cache_key = (source_labels, qname)
                    if cache_key not in label_cache:
                        options = [(max(_score(source, l.text) for source in source_labels), l) for l in labels.get(qname, ())]
                        options.sort(key=lambda x: (-x[0], x[1].language != 'ko', x[1].role, x[1].text, x[1].resource_id))
                        label_cache[cache_key] = options[0] if options and options[0][0] > 0 else None
                    selected = label_cache[cache_key]
                    if selected is None:
                        reject(occurrence, ('NO_CURRENT_LABEL_EVIDENCE',))
                        continue
                    score, label = selected
                    unverified = ['WORKBOOK_ONLY_PARTIAL', 'DIMENSIONS_UNVERIFIED', 'UNIT_UNVERIFIED', 'SCALE_UNVERIFIED', 'SIGN_UNVERIFIED', 'HUMAN_REVIEW_REQUIRED']
                    evidence = [role_reason, 'CURRENT_LABEL_EXACT_MATCH' if score == 1 else 'CURRENT_LABEL_SUBSTRING_MATCH', 'CURRENT_PRESENTATION_PATH_OBSERVED']
                    if not constraint or not constraint.period_type or not concept.period_type:
                        unverified.append('PERIOD_TYPE_UNKNOWN')
                    else:
                        evidence.append('KNOWN_PERIOD_TYPE_MATCH')
                    if not constraint or not constraint.type_name or not concept.type_name:
                        unverified.append('TYPE_UNKNOWN')
                    else:
                        evidence.append('KNOWN_TYPE_MATCH')
                    if concept.abstract is None:
                        unverified.append('ABSTRACT_UNKNOWN')
                    if not occurrence.path:
                        unverified.append('PATH_UNKNOWN')
                    refs = tuple(sorted(resources.get(qname, ()), key=lambda r: r.resource_id))
                    candidates.append(Candidate(qname, occurrence.role_uri, occurrence.path, occurrence.occurrence_id,
                                                label.text, label.resource_id, score, 'PARTIAL', tuple(r.resource_id for r in refs), tuple(unverified),
                                                occurrence.source, label.source, refs, tuple(evidence)))
        checked = tuple(_validate_reference(r, candidates, concepts, document.metadata.requested, bool(blocked)) for r in references)
        support = {}
        for r in checked:
            if r.state == 'REVALIDATED':
                identity = (r.evidence.qname, r.evidence.role_uri, r.evidence.path)
                support[identity] = support.get(identity, 0) + 1
        def key(candidate):
            return (-candidate.current_score, -support.get((candidate.qname, candidate.role_uri, candidate.path), 0),
                    candidate.qname, candidate.role_uri, candidate.path, candidate.occurrence_id)
        candidates.sort(key=key)
        candidate_total = len(candidates)
        if candidate_total > MAX_CANDIDATES:
            subject_diagnostics.append('CANDIDATES_TRUNCATED:' + str(candidate_total))
        if rejection_total > MAX_REJECTIONS:
            subject_diagnostics.append('REJECTIONS_TRUNCATED:' + str(rejection_total))
        if not candidates and not blocked:
            subject_diagnostics.append('NO_CURRENT_CANDIDATE')
        state = blocked or ('SUGGESTED' if candidates else 'UNRESOLVED')
        results.append(SubjectRecommendation(subject.subject_id, state, tuple(candidates[:MAX_CANDIDATES]), tuple(rejected), checked,
                       candidate_total > 1, subject.text, subject.value_state, tuple(dict.fromkeys(subject_diagnostics)),
                       subject.source_span, subject.table_id, subject.row, subject.column, tuple(proposals), evaluated, excluded,
                       candidate_total, rejection_total))
    coverage = RecommendationCoverage(len(results), sum(s.state == 'SUGGESTED' for s in results),
                                       sum(s.state == 'UNRESOLVED' for s in results), sum(s.state == 'CONFLICT' for s in results))
    return RecommendationResult(_fingerprint(document, taxonomy, constraints, references, rule_version), rule_version,
                                 document.snapshot_id, taxonomy.snapshot_id if taxonomy else None, tuple(results), coverage, diagnostics,
                                 document.source_sha256, taxonomy.content_sha256 if taxonomy else None, document.metadata,
                                 taxonomy.metadata if taxonomy else None, document.coverage)


def analyze(dsd_bytes, tax_bytes, *, report: DsdReportContext, metadata: TaxonomyMetadata,
            namespaces: tuple[NamespaceBinding, ...], constraints=(), references=(), rule_version=RULE_VERSION):
    document = parse_dsd(dsd_bytes, report=report)
    taxonomy = parse_taxonomy_workbook(tax_bytes, logical_uri='urn:auditdesk:current-taxonomy', metadata=metadata,
                                       namespaces=namespaces) if tax_bytes is not None else None
    return recommend(document, taxonomy, constraints=constraints, references=references, rule_version=rule_version)
