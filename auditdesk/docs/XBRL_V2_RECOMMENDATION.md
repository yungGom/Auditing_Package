# Current-first recommendation preview

Issues: [#9](https://github.com/yungGom/Auditing_Package/issues/9), [#11](https://github.com/yungGom/Auditing_Package/issues/11), [#12](https://github.com/yungGom/Auditing_Package/issues/12).

## Purpose and supported scope

The offline V2 preview reads current DSD ZIP bytes and a current DART taxonomy workbook, preserves source locations and proposes current concept occurrences with reasons. It never creates an approval event, fact binding or submission workbook. Existing AuditDesk screens, rollforward, databases, thresholds and writers are unchanged.

This is the bounded workbook-only path of the approved A scope. It implements raw-input ingestion and recommendation, not full V2-2 effective DTS/DRS validation or full V2-3 interpretation of arbitrary document structures. `PARTIAL` is a capability limit, not a confidence score or an accounting verdict.

The imported V2-1 domain/storage source and two tests were copied byte-for-byte from the existing V2 worktree and reviewed as dependencies. The recommendation path is stateless and does not instantiate or migrate those stores.

## Inputs and evidence

- Current DSD: `contents.xml` in a bounded ZIP, preserved raw XML, subject/table IDs, original character spans, header clues and requested versus observed report context.
- Current workbook: `Concepts`, `RoleTypes`, `Presentation Link`, optional `Label Link` and `Reference Link`. Missing or ambiguous identity is visible and cannot become a verified candidate.
- Report context: entity scheme/identifier, connected/separate scope and explicit reporting dates. Comparative columns inside the current DSD remain part of the current source and are separately labelled.
- Taxonomy metadata: version, `CURRENT_TAXONOMY`, reporting date, applicability start/end, applicability evidence identifier and the SHA-256 of the exact workbook bytes.
- Namespace declarations: prefix, namespace URI and declaration evidence. The workbook does not supply full XSD declarations; prefixes and filenames are never used to guess a namespace.
- Optional subject constraints and prior/reference evidence: each is explicitly identified and bound to its source. Prior source metadata and approvals do not grant current authority.

An applicability declaration is supplied evidence checked for internal consistency with these bytes and dates. It is not independent proof that a regulator has approved a release for this report. That business assertion and any uncertain report identity still require the user's review.

## Local use

From the `auditdesk` directory, with the existing project dependencies installed:

```text
python -m auditdesk.xbrl_v2 --dsd current.dsd --taxonomy current.xlsx --context context.json --out recommendations.json
```

The context JSON has `report`, `taxonomy`, and `namespaces` keys matching the `DsdReportContext`, `TaxonomyMetadata`, and `NamespaceBinding` fields. Optional constraints/references use the recommendation dataclasses. Unknown fields are rejected; Golden/evaluation inputs are not supported. Use actual source hashes and evidence identifiers, not guessed namespace mappings or arbitrary applicability dates.

The Python entrypoints are `dsd.parse_dsd`, `taxonomy.parse_taxonomy_workbook`, `recommendation.recommend`, and `recommendation.analyze` under `auditdesk.xbrl_v2`. `analyze` connects both raw inputs. `recommend` is an internal boundary accepting trusted parser-produced snapshots for repeat analysis; arbitrary externally assembled snapshots require separate provenance validation.

The command writes local JSON with input identity, coverage, candidate occurrences, rejected alternatives, prior/reference reassessment and unresolved diagnostics. Successful JSON generation does not mean the report is valid or ready to file. Malformed input returns a failure without replacing a previous output. Output paths may not alias input paths.

## Reading the result

- `SUGGESTED`: a candidate has current supporting evidence. Even a single candidate remains a suggestion.
- `UNRESOLVED`: input, structural evidence or a compatible candidate is missing. An unknown is not silently interpreted as either a match or a mismatch.
- `CONFLICT`: current evidence disagrees. Resolve the source context before relying on a recommendation.
- `PARTIAL`: workbook preview only. Dimension/default/closed/targetRole/typed-domain and full schema-closure proofs are unavailable.

The engine first limits by current structural evidence and explicit constraints, then ranks lexical evidence. Reference popularity or old labels cannot defeat a current incompatibility. A prior occurrence is checked against current expanded QName, Role/path, type and period and keeps its original source label. A missing current concept is not automatically a deprecated concept or a requirement to create an extension.

Blank, nil and original numeric text/signs are retained. Unit, scale, unknown periods and comparative-column semantics are not converted into invented values or approved facts. Subject coverage includes unresolved items; removing them from the denominator is not permitted.

Freshness must be checked against the latest document, taxonomy, rule and any supplied constraint/reference snapshots. A stored result does not prove that a file at the same path still has the same contents.

## Current limitations

- DSD date observations are currently limited to explicit `PERIODSTART`/`PERIODEND`; entity evidence uses `COMPANY-NAME@AREGCIK`; scope evidence uses explicit document-name terms. Other evidence remains unknown rather than using an arbitrary date in the narrative.
- Row-major table topology and merges are preserved. Nested or malformed tables are rejected; continuation/transposition meaning, units and scale remain unresolved. Unclassified source text remains in raw XML with coverage diagnostics.
- Full DTS, current company extension package ingestion, typed dimensions, effective relationship overrides and DART editor conformance are not implemented by this preview. Prior company extensions remain reference candidates only.
- A read-only structural probe of the available public 2026 DART workbook detected one duplicate concept with different lexical type names and sixteen labels without concept identity. Six parent diagnostics cascade from the unresolved duplicate. Equivalence of type prefixes and implicit label continuation are not inferred without evidence. The parser fails closed for that file. It has not been accepted as ready for current-report production use. The probe used test declarations and did not establish official namespace or period applicability.
- No UI rollout, final Excel/XBRL export, accountant ground truth, precision threshold or production release is included.

## Verification

New behavior tests are in `tests/test_xbrl_v2_taxonomy.py`, `test_xbrl_v2_dsd.py`, `test_xbrl_v2_recommendation.py` and `test_xbrl_v2_recommendation_integration.py`. Run these directly together with the V2-1 core/offline tests: the current Harness script does not collect the `auditdesk/tests` folder. Required legacy Python, Node, protected-artifact and full Harness checks remain additional requirements, not substitutes for these tests.

Repository fixture gaps and inherited protected differences against `origin/main` are reported separately from the task diff against its recorded starting commit. Neither skips nor inherited failures become Technical PASS. See [the verification report](XBRL_V2_RECOMMENDATION_VERIFICATION.md) for final evidence and remaining gaps.
