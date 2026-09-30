"""Local-only raw DSD/workbook recommendation entry point."""
from __future__ import annotations
import argparse
from dataclasses import asdict, fields
import json
import os
import re
from pathlib import Path
import sys
import tempfile
from .dsd import DsdReportContext
from .taxonomy import TaxonomyMetadata, NamespaceBinding
from .recommendation import analyze, RecommendationConstraint, ReferenceEvidence


def _object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('Duplicate JSON key')
        value[key] = item
    return value


def _record(cls, value):
    if not isinstance(value, dict) or set(value) - {f.name for f in fields(cls)}:
        raise ValueError('Unknown context record field')
    kwargs = dict(value)
    for key, item in kwargs.items():
        if key == 'dimensions':
            if not isinstance(item, list) or any(not isinstance(p, list) or len(p) != 2 or not all(isinstance(v, str) for v in p) for p in item):
                raise ValueError('Invalid dimensions')
            kwargs[key] = tuple(tuple(p) for p in item)
        elif key == 'path':
            if not isinstance(item, list) or not all(isinstance(v, str) for v in item):
                raise ValueError('Invalid occurrence path')
            kwargs[key] = tuple(item)
        elif item is not None and not isinstance(item, str):
            raise ValueError('Context fields require strings')
        elif item is None and cls not in (DsdReportContext, RecommendationConstraint):
            raise ValueError('Null required context field')
    return cls(**kwargs)


def _read(path, limit):
    with path.open('rb') as handle:
        data = handle.read(limit + 1)
    if len(data) > limit:
        raise ValueError('Input exceeds size limit')
    return data


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's default message may echo a private path or argument value.
        print('Invalid arguments; use --help for required options.', file=sys.stderr)
        raise SystemExit(2)


def main(argv=None):
    parser = _Parser(description='Create local, partial current-first XBRL recommendations')
    for name in ('dsd', 'taxonomy', 'context', 'out'):
        parser.add_argument('--' + name, required=True)
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)
    temporary = None
    try:
        inputs = tuple(Path(p) for p in (args.dsd, args.taxonomy, args.context))
        output = Path(args.out)
        for source in inputs:
            if output.resolve() == source.resolve() or (output.exists() and os.path.samefile(output, source)):
                raise ValueError('Output would overwrite an input')
        context = json.loads(_read(inputs[2], 1024 * 1024).decode('utf-8-sig'), object_pairs_hook=_object)
        required = {'report', 'taxonomy', 'namespaces'}
        if (not isinstance(context, dict) or not required.issubset(context)
                or set(context) - required - {'constraints', 'references'}):
            raise ValueError('Unknown or missing context fields')
        for key in ('namespaces', 'constraints', 'references'):
            if key in context and not isinstance(context[key], list):
                raise ValueError('Context collection required')
        report = _record(DsdReportContext, context['report'])
        metadata = _record(TaxonomyMetadata, context['taxonomy'])
        namespaces = tuple(_record(NamespaceBinding, n) for n in context['namespaces'])
        constraints = tuple(_record(RecommendationConstraint, c) for c in context.get('constraints', []))
        references = tuple(_record(ReferenceEvidence, r) for r in context.get('references', []))
        result = analyze(_read(inputs[0], 16 * 1024 * 1024), _read(inputs[1], 32 * 1024 * 1024),
                         report=report, metadata=metadata, namespaces=namespaces,
                         constraints=constraints, references=references)
        if 'CURRENT_TAXONOMY_UNVERIFIED' in result.diagnostics:
            codes = sorted({d for d in result.diagnostics if re.fullmatch(r'TAXONOMY:[A-Z_]+', d)})
            if codes:
                print('Taxonomy diagnostic codes: ' + ', '.join(codes), file=sys.stderr)
            raise ValueError('Malformed or unsupported taxonomy declaration/workbook')
        encoded = json.dumps(asdict(result), ensure_ascii=False, sort_keys=True, indent=2).encode('utf-8')
        with tempfile.NamedTemporaryFile(mode='wb', prefix='.recommendations-', suffix='.tmp', dir=output.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output)
        temporary = None
        return 0
    except (OSError, ValueError, TypeError, AttributeError, KeyError):
        print('Recommendation input or local output is invalid; existing output was preserved.', file=sys.stderr)
        return 2
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                print('Temporary output cleanup failed.', file=sys.stderr)


if __name__ == '__main__':
    raise SystemExit(main())
