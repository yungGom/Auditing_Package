"""Check delivered marks on every page, beyond financial gate counts."""
import io
from pathlib import Path
import tempfile
import unittest

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject
from reportlab.pdfgen import canvas
from pdf_output import write_tickmark_pdf


class DeliveredMarks(unittest.TestCase):
    def test_forward_page_link_does_not_drop_destination_mark(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/'linked.pdf'
            output = Path(directory)/'marked.pdf'
            c = canvas.Canvas(str(source), pagesize=(300, 400), invariant=1)
            c.drawString(20, 380, 'SOURCE_FIRST')
            c.linkAbsolute('jump', 'last', Rect=(20, 340, 120, 370))
            c.showPage()
            c.bookmarkPage('last')
            c.drawString(20, 380, 'SOURCE_LAST')
            c.save()
            mark = io.BytesIO()
            c = canvas.Canvas(mark, pagesize=(300, 400), invariant=1)
            c.drawString(20, 200, 'DESTINATION_REVIEW ? candidate only')
            c.save()
            write_tickmark_pdf(source, {2: mark.getvalue()}, output)
            result = PdfReader(output)
            self.assertNotIn('DESTINATION_REVIEW', result.pages[0].extract_text())
            self.assertIn('SOURCE_LAST', result.pages[1].extract_text())
            self.assertIn('DESTINATION_REVIEW ? candidate only', result.pages[1].extract_text())
            destination = result.pages[0]['/Annots'][0].get_object()['/Dest'][0]
            self.assertEqual(result.pages[1].indirect_reference, destination)

    def test_shared_source_stream_keeps_each_pages_own_mark(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/'shared.pdf'
            output = Path(directory)/'marked.pdf'
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=(300, 400), invariant=1)
            for _ in range(3):
                c.drawString(20, 380, 'SHARED_SOURCE')
                c.showPage()
            c.save()
            source_writer = PdfWriter(clone_from=PdfReader(io.BytesIO(buffer.getvalue())))
            shared = source_writer.pages[0].raw_get('/Contents')
            for page in source_writer.pages[1:]:
                page[NameObject('/Contents')] = shared
            with source.open('wb') as stream:
                source_writer.write(stream)
            overlays = {}
            for number in (1, 3):
                mark = io.BytesIO()
                c = canvas.Canvas(mark, pagesize=(300, 400), invariant=1)
                c.drawString(20, 200, f'REVIEW_{number} ? candidate only')
                c.save()
                overlays[number] = mark.getvalue()
            write_tickmark_pdf(source, overlays, output)
            for number, page in enumerate(PdfReader(output).pages, 1):
                with self.subTest(page=number):
                    text = page.extract_text()
                    self.assertIn('SHARED_SOURCE', text)
                    if number in overlays:
                        self.assertIn(f'REVIEW_{number} ? candidate only', text)
                        self.assertNotIn(f'REVIEW_{4-number} ? candidate only', text)
                    else:
                        self.assertNotIn('REVIEW_', text)

    def test_distinct_marks_survive_many_page_write(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/'source.pdf'
            output = Path(directory)/'marked.pdf'
            c = canvas.Canvas(str(source), pagesize=(300, 400), invariant=1)
            overlays = {}
            for number in range(1, 169):
                c.drawString(20, 380, f'SOURCE_{number:03}')
                c.showPage()
                if number % 11 == 0:
                    continue
                buffer = io.BytesIO()
                overlay = canvas.Canvas(buffer, pagesize=(300, 400), invariant=1)
                overlay.drawString(20, 200, f'REVIEW_{number:03} ? candidate only')
                overlay.save()
                overlays[number] = buffer.getvalue()
            c.save()
            write_tickmark_pdf(source, overlays, output)
            result = PdfReader(output)
            self.assertEqual(168, len(result.pages))
            for number, page in enumerate(result.pages, 1):
                with self.subTest(page=number):
                    text = page.extract_text()
                    self.assertIn(f'SOURCE_{number:03}', text)
                    self.assertEqual([0, 0, 300, 400], list(page.mediabox))
                    if number in overlays:
                        self.assertIn(f'REVIEW_{number:03} ? candidate only', text)
                    else:
                        self.assertNotIn('REVIEW_', text)

    def test_no_overlay_preserves_source(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/'source.pdf'
            output = Path(directory)/'marked.pdf'
            c = canvas.Canvas(str(source), pagesize=(300, 400), invariant=1)
            c.drawString(20, 380, 'SOURCE without checks')
            c.save()
            write_tickmark_pdf(source, {}, output)
            self.assertEqual(PdfReader(source).pages[0].extract_text(),
                             PdfReader(output).pages[0].extract_text())


if __name__ == '__main__':
    unittest.main()
