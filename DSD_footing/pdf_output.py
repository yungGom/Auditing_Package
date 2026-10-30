"""Write offline tickmark overlays without changing source pages or judgments."""
import io
from contextlib import contextmanager
import hashlib
import math
import os
from pathlib import Path
import sys
import tempfile
import warnings
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject


def _identity(stat):
    return stat.st_dev, stat.st_ino


def _cleanup_problem(problem, error):
    message = f'PDF 임시 파일 정리 실패: {problem}'
    if error is not None:
        try:
            error.add_note(message)
        except Exception:
            pass
    else:
        # Publication already succeeded. Warning filters/handlers must not
        # turn a valid published PDF into an apparent save failure.
        try:
            warnings.warn(message, RuntimeWarning, stacklevel=3)
        except Exception:
            pass


def _cleanup_owned(path, identity, error):
    """Never delete another call's files or hide the original failure."""
    try:
        try:
            current = os.stat(path, follow_symlinks=False)
        except FileNotFoundError:
            return
        if identity is None or _identity(current) != identity:
            raise OSError(f'임시 파일 소유를 확인할 수 없어 정리하지 않았습니다: {path}')
        os.unlink(path)
    except OSError as cleanup_error:
        _cleanup_problem(cleanup_error, error)


def _close_owned(descriptor, error):
    try:
        os.close(descriptor)
    except OSError as cleanup_error:
        _cleanup_problem(cleanup_error, error)


@contextmanager
def _claim_output(output):
    claim = _claim_path(output)
    try:
        descriptor = os.open(claim, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as error:
        raise RuntimeError(f'이 PDF의 저장이 진행 중이거나 이전 저장 확인이 필요합니다: {output} / 확인 파일: {claim}') from error
    identity = None
    try:
        identity = _identity(os.fstat(descriptor))
        yield
    finally:
        error = sys.exc_info()[1]
        _close_owned(descriptor, error)
        _cleanup_owned(claim, identity, error)


def _claim_path(output):
    canonical = os.path.normcase(str(output.resolve()))
    if os.name == 'nt':
        # Extended-path and ordinary spellings address the same Windows file.
        if canonical.startswith('\\\\?\\unc\\'):
            canonical = '\\\\' + canonical[8:]
        elif canonical.startswith('\\\\?\\'):
            canonical = canonical[4:]
    key = hashlib.sha256(os.fsencode(canonical)).hexdigest()
    return output.with_name('.dsd-pdf-' + key + '.saving')


def _stream_stat(stream):
    try:
        descriptor = stream.fileno()
    except (AttributeError, io.UnsupportedOperation):
        return None
    return os.fstat(descriptor)


def _snapshot_stream(stream, output):
    initial = _stream_stat(stream)
    if initial is not None and output.exists() and _identity(initial) == _identity(os.stat(output)):
        raise ValueError('원본 PDF와 출력 경로가 같습니다. 원본을 덮어쓰지 않았습니다.')
    position = stream.tell()
    try:
        # Seeking a writable buffered input flushes its caller's pending data,
        # as PdfReader did before this change. Compare stats around the read,
        # after that normal stream preparation, not around the seek itself.
        stream.seek(0)
        before = _stream_stat(stream)
        if initial is not None and (before is None or _identity(initial) != _identity(before)):
            raise ValueError('원본 PDF의 파일 식별자가 변경되었습니다.')
        data = stream.read()
    finally:
        stream.seek(position)
    after = _stream_stat(stream)
    if before is not None and (after is None or
            (_identity(before), before.st_size, before.st_mtime_ns) !=
            (_identity(after), after.st_size, after.st_mtime_ns)):
        raise ValueError('원본 PDF가 읽는 중 변경되었습니다.')
    return data


def _source_reader(source, output):
    source_path = None
    if isinstance(source, (str, bytes, os.PathLike)):
        source_path = Path(os.fsdecode(source)).absolute()
        if source_path.resolve() == output.resolve() or (output.exists() and os.path.samefile(source_path, output)):
            raise ValueError('원본 PDF와 출력 경로가 같습니다. 원본을 덮어쓰지 않았습니다.')
        with source_path.open('rb') as stream:
            data = _snapshot_stream(stream, output)
    else:
        # Read the supplied handle, including Windows NamedTemporaryFile and
        # descriptor-backed streams whose .name is an integer. Never reopen it.
        data = _snapshot_stream(source, output)
    expected = hashlib.sha256(data).digest()

    def verify_source():
        if source_path is not None:
            with source_path.open('rb') as stream:
                current = hashlib.sha256(_snapshot_stream(stream, output)).digest()
        else:
            current = hashlib.sha256(_snapshot_stream(source, output)).digest()
        if current != expected:
            raise ValueError('원본 PDF가 저장 도중 변경되어 출력을 교체하지 않았습니다.')
    return PdfReader(io.BytesIO(data)), verify_source


def _validate_pdf(path, expected_pages):
    with open(path, 'rb') as stream:
        reader = PdfReader(stream, strict=True)
        if reader.is_encrypted or expected_pages < 1 or len(reader.pages) != expected_pages:
            raise ValueError('작성된 PDF의 페이지 수 또는 암호화 상태가 올바르지 않습니다.')
        for page in reader.pages:
            dimensions = (float(page.mediabox.width), float(page.mediabox.height))
            if not all(math.isfinite(value) and value > 0 for value in dimensions):
                raise ValueError('작성된 PDF의 페이지 크기가 올바르지 않습니다.')
            contents = page.get_contents()
            if contents is not None:
                contents.get_data()
                contents.operations


def _publish_pdf(writer, output, expected_pages, verify_source):
    descriptor, name = tempfile.mkstemp(prefix='.dsd-pdf-', suffix='.tmp.pdf', dir=output.parent)
    stage = Path(name)
    identity = None
    try:
        identity = _identity(os.fstat(descriptor))
        with os.fdopen(descriptor, 'wb') as stream:
            descriptor = None
            writer.write(stream)
            stream.flush()
            os.fsync(stream.fileno())
        _validate_pdf(stage, expected_pages)
        verify_source()
        if _identity(os.stat(stage, follow_symlinks=False)) != identity:
            raise OSError('검증한 임시 PDF가 교체되어 출력을 게시하지 않았습니다.')
        os.replace(stage, output)
    finally:
        error = sys.exc_info()[1]
        if descriptor is not None:
            _close_owned(descriptor, error)
        _cleanup_owned(stage, identity, error)


def _write_claimed(source, overlays, output):
    reader, verify_source = _source_reader(source, output)
    writer = PdfWriter()
    for number, page in enumerate(reader.pages, 1):
        # Clone first: source contents may already be in the writer's cache
        # through a shared stream or an internal page link. Merge into the
        # writer-owned page so its new marks cannot be replaced by that cache.
        marked = writer.add_page(page)
        if number in overlays:
            # A source stream can belong to several pages. Give this page its
            # own stream before merging, so marks cannot leak to its siblings.
            contents = marked.get_contents()
            if contents is not None:
                detached = DecodedStreamObject()
                detached.set_data(contents.get_data())
                marked[NameObject('/Contents')] = detached
            marked.merge_page(PdfReader(io.BytesIO(overlays[number])).pages[0])
    _publish_pdf(writer, output, len(reader.pages), verify_source)


def write_tickmark_pdf(source, overlays, output):
    """Publish one complete PDF; fail closed on aliases and concurrent saves.

    A foreign/stale claim is never removed automatically. A killed process may
    leave owned staging/claim files for explicit inspection. This guarantees a
    single PDF's failure preservation, not a PDF/XLSX transaction or GUI state.
    """
    output = Path(os.fsdecode(os.fspath(output))).absolute()
    if output.is_symlink():
        raise ValueError('출력 경로가 심볼릭 링크여서 PDF를 저장하지 않았습니다.')
    with _claim_output(output):
        _write_claimed(source, overlays, output)
