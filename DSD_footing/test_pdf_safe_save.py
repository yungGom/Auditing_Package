"""Synthetic single-PDF preservation controls; never use company/source outputs."""
import io
import os
from pathlib import Path
import tempfile
import subprocess
import sys
import threading
import time
import unittest
import warnings
from unittest.mock import patch

from pypdf import PdfReader, PdfWriter
from pypdf.generic import EncodedStreamObject, NameObject, RectangleObject
import pdf_output


def pdf_bytes(pages=1, width=300):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=width, height=400)
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()


class PreviousPDFPreservation(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='pdf_safe_synthetic_')
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / 'synthetic-source.pdf'
        self.output = self.root / 'synthetic-complete.pdf'
        self.original = pdf_bytes(2, 500)
        self.source_bytes = pdf_bytes()
        self.source.write_bytes(self.source_bytes)
        self.output.write_bytes(self.original)

    def assert_preserved(self):
        self.assertEqual(self.original, self.output.read_bytes())
        self.assertEqual(self.source_bytes, self.source.read_bytes())
        self.assertEqual({self.source.name, self.output.name},
                         {p.name for p in self.root.iterdir()})

    def test_partial_write_fault_preserves_previous_pdf(self):
        def fail(writer, stream):
            stream.write(b'%PDF-1.7\nPARTIAL\n')
            raise OSError('synthetic disk failure')
        with patch.object(PdfWriter, 'write', fail):
            with self.assertRaisesRegex(OSError, 'synthetic disk failure'):
                pdf_output.write_tickmark_pdf(self.source, {}, self.output)
        self.assert_preserved()

    def test_invalid_complete_bytes_are_not_published(self):
        def invalid(writer, stream):
            stream.write(b'not a PDF')
        with patch.object(PdfWriter, 'write', invalid):
            with self.assertRaises(Exception):
                pdf_output.write_tickmark_pdf(self.source, {}, self.output)
        self.assert_preserved()

    def test_wrong_page_count_is_not_published(self):
        wrong = pdf_bytes(3)
        with patch.object(PdfWriter, 'write', lambda writer, stream: stream.write(wrong)):
            with self.assertRaises(ValueError):
                pdf_output.write_tickmark_pdf(self.source, {}, self.output)
        self.assert_preserved()

    def test_source_equals_output_is_rejected_before_write(self):
        with self.assertRaises(ValueError):
            pdf_output.write_tickmark_pdf(self.source, {}, self.source)
        self.assert_preserved()

    def test_source_hardlink_output_is_rejected(self):
        self.output.unlink()
        os.link(self.source, self.output)
        before = self.output.read_bytes()
        with self.assertRaises(ValueError):
            pdf_output.write_tickmark_pdf(self.source, {}, self.output)
        self.assertEqual(before, self.output.read_bytes())
        self.assertEqual(self.source_bytes, self.source.read_bytes())

    def test_bad_source_keeps_previous_pdf(self):
        self.source.write_bytes(b'invalid synthetic source')
        with self.assertRaises(Exception):
            pdf_output.write_tickmark_pdf(self.source, {}, self.output)
        self.assertEqual(self.original, self.output.read_bytes())
        self.assertEqual(b'invalid synthetic source', self.source.read_bytes())
        self.assertEqual(2, len(list(self.root.iterdir())))

    def test_success_changes_only_output_and_keeps_no_temp_files(self):
        pdf_output.write_tickmark_pdf(self.source, {}, self.output)
        self.assertEqual(1, len(PdfReader(self.output).pages))
        self.assertEqual(300, float(PdfReader(self.output).pages[0].mediabox.width))
        self.assertEqual(self.source_bytes, self.source.read_bytes())
        self.assertEqual(2, len(list(self.root.iterdir())))

    def test_new_destination_failure_does_not_leave_partial_pdf(self):
        self.output.unlink()
        def fail(writer, stream):
            stream.write(b'PARTIAL')
            raise OSError('synthetic first save failure')
        with patch.object(PdfWriter, 'write', fail):
            with self.assertRaises(OSError):
                pdf_output.write_tickmark_pdf(self.source, {}, self.output)
        self.assertFalse(self.output.exists())
        self.assertEqual([self.source.name], [p.name for p in self.root.iterdir()])

    def test_fsync_failure_preserves_previous_pdf(self):
        with patch.object(pdf_output.os, 'fsync', side_effect=OSError('synthetic fsync failure')):
            with self.assertRaisesRegex(OSError, 'fsync failure'):
                pdf_output.write_tickmark_pdf(self.source, {}, self.output)
        self.assert_preserved()

    def test_replace_failure_preserves_previous_pdf_and_allows_retry(self):
        with patch.object(pdf_output.os, 'replace', side_effect=PermissionError('synthetic locked destination')):
            with self.assertRaises(PermissionError):
                pdf_output.write_tickmark_pdf(self.source, {}, self.output)
        self.assert_preserved()
        pdf_output.write_tickmark_pdf(self.source, {}, self.output)
        self.assertEqual(1, len(PdfReader(self.output).pages))

    def test_zero_page_geometry_is_rejected(self):
        actual = PdfWriter.write
        def invalid(writer, stream):
            writer.pages[0].mediabox = RectangleObject([0, 0, 0, 400])
            return actual(writer, stream)
        with patch.object(PdfWriter, 'write', invalid):
            with self.assertRaises(ValueError):
                pdf_output.write_tickmark_pdf(self.source, {}, self.output)
        self.assert_preserved()

    def test_lazy_content_decoding_failure_is_not_published(self):
        actual = PdfWriter.write
        def invalid(writer, stream):
            bad = EncodedStreamObject()
            bad._data = b'synthetic unreadable encoded stream'
            bad[NameObject('/Filter')] = NameObject('/SyntheticUnsupportedDecode')
            writer.pages[0][NameObject('/Contents')] = writer._add_object(bad)
            return actual(writer, stream)
        with patch.object(PdfWriter, 'write', invalid):
            with self.assertRaises(NotImplementedError):
                pdf_output.write_tickmark_pdf(self.source, {}, self.output)
        self.assert_preserved()

    def test_source_replaced_during_write_blocks_publication(self):
        replacement = pdf_bytes(3, 700)
        actual = PdfWriter.write
        def change_source(writer, stream):
            self.source.write_bytes(replacement)
            return actual(writer, stream)
        with patch.object(PdfWriter, 'write', change_source):
            with self.assertRaises(ValueError):
                pdf_output.write_tickmark_pdf(self.source, {}, self.output)
        self.assertEqual(self.original, self.output.read_bytes())
        self.assertEqual(replacement, self.source.read_bytes())
        self.assertEqual(2, len(list(self.root.iterdir())))

    def test_missing_parent_is_not_created(self):
        destination = self.root / 'missing' / 'output.pdf'
        with self.assertRaises(FileNotFoundError):
            pdf_output.write_tickmark_pdf(self.source, {}, destination)
        self.assertFalse(destination.parent.exists())
        self.assert_preserved()

    def test_output_directory_is_preserved_on_replace_failure(self):
        destination = self.root / 'existing-directory'
        destination.mkdir()
        marker = destination / 'do-not-touch'
        marker.write_bytes(b'unrelated')
        with self.assertRaises(OSError):
            pdf_output.write_tickmark_pdf(self.source, {}, destination)
        self.assertEqual(b'unrelated', marker.read_bytes())
        self.assertEqual(self.original, self.output.read_bytes())
        self.assertEqual(3, len(list(self.root.iterdir())))

    def test_relative_source_output_alias_is_rejected(self):
        folder = self.root / 'subfolder'
        folder.mkdir()
        alias = folder / '..' / self.source.name
        with self.assertRaises(ValueError):
            pdf_output.write_tickmark_pdf(self.source, {}, alias)
        self.assertEqual(self.source_bytes, self.source.read_bytes())
        self.assertEqual(self.original, self.output.read_bytes())
        self.assertEqual(3, len(list(self.root.iterdir())))

    def test_symlink_destination_guard_precedes_claim_and_source_read(self):
        with patch.object(pdf_output.Path, 'is_symlink', return_value=True), \
             patch.object(pdf_output, '_claim_output') as claim, \
             patch.object(pdf_output, '_source_reader') as source_reader:
            with self.assertRaises(ValueError):
                pdf_output.write_tickmark_pdf(self.source, {}, self.output)
        claim.assert_not_called()
        source_reader.assert_not_called()
        self.assert_preserved()

    def test_foreign_or_stale_claim_is_not_deleted(self):
        claim = pdf_output._claim_path(self.output)
        claim.write_bytes(b'foreign claim; no auto recovery')
        with self.assertRaises(RuntimeError):
            pdf_output.write_tickmark_pdf(self.source, {}, self.output)
        self.assertEqual(b'foreign claim; no auto recovery', claim.read_bytes())
        self.assertEqual(self.original, self.output.read_bytes())
        self.assertEqual(self.source_bytes, self.source.read_bytes())

    def test_unrelated_temp_is_not_deleted(self):
        unrelated = self.root / '.unrelated.tmp.pdf'
        unrelated.write_bytes(b'foreign temporary data')
        with patch.object(PdfWriter, 'write', side_effect=OSError('synthetic failure')):
            with self.assertRaises(OSError):
                pdf_output.write_tickmark_pdf(self.source, {}, self.output)
        self.assertEqual(b'foreign temporary data', unrelated.read_bytes())
        self.assertEqual(self.original, self.output.read_bytes())
        self.assertEqual(3, len(list(self.root.iterdir())))

    def test_cleanup_failure_adds_note_without_hiding_write_error(self):
        unlink = pdf_output.os.unlink
        def block_stage(path, *args, **kwargs):
            if str(path).endswith('.tmp.pdf'):
                raise PermissionError('synthetic stage cleanup failure')
            return unlink(path, *args, **kwargs)
        with patch.object(pdf_output.os, 'unlink', block_stage), \
             patch.object(PdfWriter, 'write', side_effect=OSError('synthetic primary write failure')):
            with self.assertRaisesRegex(OSError, 'primary write failure') as caught:
                pdf_output.write_tickmark_pdf(self.source, {}, self.output)
        self.assertTrue(any('cleanup failure' in n for n in caught.exception.__notes__))
        self.assertEqual(self.original, self.output.read_bytes())
        self.assertFalse(pdf_output._claim_path(self.output).exists())
        self.assertEqual(1, len(list(self.root.glob('*.tmp.pdf'))))

    def test_postpublish_cleanup_failure_warns_without_failure(self):
        unlink = pdf_output.os.unlink
        def block_claim(path, *args, **kwargs):
            if str(path).endswith('.saving'):
                raise PermissionError('synthetic claim cleanup failure')
            return unlink(path, *args, **kwargs)
        with patch.object(pdf_output.os, 'unlink', block_claim):
            with self.assertWarns(RuntimeWarning):
                pdf_output.write_tickmark_pdf(self.source, {}, self.output)
        self.assertEqual(1, len(PdfReader(self.output).pages))
        self.assertEqual(self.source_bytes, self.source.read_bytes())

    def test_warning_filter_error_cannot_reverse_success(self):
        unlink = pdf_output.os.unlink
        def block_claim(path, *args, **kwargs):
            if str(path).endswith('.saving'):
                raise PermissionError('synthetic claim cleanup failure')
            return unlink(path, *args, **kwargs)
        with patch.object(pdf_output.os, 'unlink', block_claim), warnings.catch_warnings():
            warnings.simplefilter('error', RuntimeWarning)
            pdf_output.write_tickmark_pdf(self.source, {}, self.output)
        self.assertEqual(1, len(PdfReader(self.output).pages))

    def test_warning_handler_error_cannot_reverse_success(self):
        unlink = pdf_output.os.unlink
        def block_claim(path, *args, **kwargs):
            if str(path).endswith('.saving'):
                raise PermissionError('synthetic claim cleanup failure')
            return unlink(path, *args, **kwargs)
        with patch.object(pdf_output.os, 'unlink', block_claim), \
             patch.object(pdf_output.warnings, 'warn', side_effect=RuntimeError('synthetic warning handler')):
            pdf_output.write_tickmark_pdf(self.source, {}, self.output)
        self.assertEqual(1, len(PdfReader(self.output).pages))

    def test_cleanup_never_deletes_file_with_foreign_identity(self):
        foreign = self.root / 'foreign.tmp.pdf'
        foreign.write_bytes(b'foreign')
        identity = pdf_output._identity(os.stat(foreign))
        with self.assertWarns(RuntimeWarning):
            pdf_output._cleanup_owned(foreign, (identity[0], identity[1] + 1), None)
        self.assertEqual(b'foreign', foreign.read_bytes())

    def test_same_target_thread_and_relative_alias_are_busy(self):
        entered = threading.Event()
        release = threading.Event()
        outcome = []
        publish = pdf_output._publish_pdf
        def held(*args):
            entered.set()
            if not release.wait(5):
                raise RuntimeError('synthetic test release timeout')
            return publish(*args)
        def first():
            try:
                pdf_output.write_tickmark_pdf(self.source, {}, self.output)
                outcome.append('OK')
            except Exception as error:
                outcome.append(error)
        folder = self.root / 'subfolder'
        folder.mkdir()
        with patch.object(pdf_output, '_publish_pdf', held):
            thread = threading.Thread(target=first)
            thread.start()
            try:
                self.assertTrue(entered.wait(5))
                self.assertEqual(self.original, self.output.read_bytes())
                destinations = [self.output, folder / '..' / self.output.name]
                if os.name == 'nt':
                    destinations.append(Path('\\\\?\\' + str(self.output)))
                for destination in destinations:
                    with self.assertRaises(RuntimeError):
                        pdf_output.write_tickmark_pdf(self.source, {}, destination)
            finally:
                release.set()
                thread.join(6)
        self.assertFalse(thread.is_alive())
        self.assertEqual(['OK'], outcome)
        self.assertEqual(1, len(PdfReader(self.output).pages))
        self.assertEqual(3, len(list(self.root.iterdir())))

    def test_same_target_other_process_is_busy(self):
        entered = self.root / 'child-entered'
        release = self.root / 'child-release'
        program = '''
import pathlib,sys,time
sys.path.insert(0,sys.argv[1])
import pdf_output
original=pdf_output._publish_pdf
def held(*args):
    pathlib.Path(sys.argv[4]).write_bytes(b'ready')
    deadline=time.monotonic()+8
    while not pathlib.Path(sys.argv[5]).exists():
        if time.monotonic()>deadline:raise RuntimeError('synthetic release timeout')
        time.sleep(0.01)
    return original(*args)
pdf_output._publish_pdf=held
pdf_output.write_tickmark_pdf(sys.argv[2],{},sys.argv[3])
'''
        process = subprocess.Popen([sys.executable, '-B', '-c', program,
                                    str(Path(pdf_output.__file__).parent), str(self.source),
                                    str(self.output), str(entered), str(release)],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 5
            while not entered.exists() and process.poll() is None and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertTrue(entered.exists())
            with self.assertRaises(RuntimeError):
                pdf_output.write_tickmark_pdf(self.source, {}, self.output)
            self.assertEqual(self.original, self.output.read_bytes())
        finally:
            release.write_bytes(b'release')
            try:
                stdout, stderr = process.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
                raise
        self.assertEqual(0, process.returncode, stderr.decode('utf-8', errors='replace'))
        self.assertEqual(1, len(PdfReader(self.output).pages))
        self.assertEqual(self.source_bytes, self.source.read_bytes())
        self.assertFalse(pdf_output._claim_path(self.output).exists())

    def test_unicode_spaces_and_long_filename_keep_staging_names_short(self):
        folder = self.root / '합성 결과 폴더'
        folder.mkdir()
        # Windows' extended path spelling permits a long component in this
        # synthetic control even when the test runner has a deep temp root.
        long_folder = Path('\\\\?\\' + str(folder)) if os.name == 'nt' else folder
        output = long_folder / ('a' * 240 + '.pdf')
        output.write_bytes(self.original)
        # Remove this one owned file using its extended spelling before the
        # ordinary TemporaryDirectory cleanup reaches Windows' path limit.
        self.addCleanup(output.unlink, missing_ok=True)
        pdf_output.write_tickmark_pdf(self.source, {}, output)
        self.assertEqual(1, len(PdfReader(output).pages))
        self.assertEqual([output.name], [p.name for p in folder.iterdir()])
        self.assertEqual(self.source_bytes, self.source.read_bytes())

    def test_staging_creation_failure_preserves_previous_pdf(self):
        with patch.object(pdf_output.tempfile, 'mkstemp', side_effect=PermissionError('synthetic staging denial')):
            with self.assertRaises(PermissionError):
                pdf_output.write_tickmark_pdf(self.source, {}, self.output)
        self.assert_preserved()

    def test_encrypted_staged_pdf_is_not_published(self):
        actual = PdfWriter.write
        def invalid(writer, stream):
            writer.encrypt('synthetic-password')
            return actual(writer, stream)
        with patch.object(PdfWriter, 'write', invalid):
            with self.assertRaises(ValueError):
                pdf_output.write_tickmark_pdf(self.source, {}, self.output)
        self.assert_preserved()

    def test_in_memory_source_remains_supported(self):
        source = io.BytesIO(self.source_bytes)
        pdf_output.write_tickmark_pdf(source, {}, self.output)
        self.assertEqual(self.source_bytes, source.getvalue())
        self.assertEqual(1, len(PdfReader(self.output).pages))
        self.assertEqual(2, len(list(self.root.iterdir())))

    def test_named_temporary_source_handle_is_not_reopened(self):
        with tempfile.NamedTemporaryFile(mode='w+b', dir=self.root) as source:
            source.write(self.source_bytes)
            source.flush()
            position = source.tell()
            pdf_output.write_tickmark_pdf(source, {}, self.output)
            self.assertFalse(source.closed)
            self.assertEqual(position, source.tell())
            source.seek(0)
            self.assertEqual(self.source_bytes, source.read())
        self.assertEqual(1, len(PdfReader(self.output).pages))

    def test_buffered_source_pending_data_remains_supported(self):
        with tempfile.NamedTemporaryFile(mode='w+b', dir=self.root) as source:
            source.write(self.source_bytes)
            # The old PdfReader accepts this buffered source without requiring
            # the caller to flush it. Its seek prepares the input for reading.
            position = source.tell()
            pdf_output.write_tickmark_pdf(source, {}, self.output)
            self.assertFalse(source.closed)
            self.assertEqual(position, source.tell())
            source.seek(0)
            self.assertEqual(self.source_bytes, source.read())
        self.assertEqual(1, len(PdfReader(self.output).pages))

    def test_descriptor_source_alias_is_rejected_before_writer(self):
        with os.fdopen(os.open(self.source, os.O_RDONLY), 'rb') as source:
            with patch.object(PdfWriter, 'write') as write:
                with self.assertRaises(ValueError):
                    pdf_output.write_tickmark_pdf(source, {}, self.source)
            write.assert_not_called()
        self.assert_preserved()

    def test_descriptor_source_remains_supported_and_open(self):
        with os.fdopen(os.open(self.source, os.O_RDONLY), 'rb') as source:
            pdf_output.write_tickmark_pdf(source, {}, self.output)
            self.assertFalse(source.closed)
            self.assertEqual(0, source.tell())
            self.assertEqual(self.source_bytes, source.read())
        self.assertEqual(1, len(PdfReader(self.output).pages))

    def test_in_memory_source_changed_during_write_blocks_publication(self):
        source = io.BytesIO(self.source_bytes)
        replacement = pdf_bytes(3, 700)
        actual = PdfWriter.write
        def change_source(writer, stream):
            source.seek(0)
            source.truncate()
            source.write(replacement)
            return actual(writer, stream)
        with patch.object(PdfWriter, 'write', change_source):
            with self.assertRaises(ValueError):
                pdf_output.write_tickmark_pdf(source, {}, self.output)
        self.assertEqual(self.original, self.output.read_bytes())
        self.assertEqual(replacement, source.getvalue())
        self.assertEqual(2, len(list(self.root.iterdir())))


if __name__ == '__main__':
    unittest.main()
