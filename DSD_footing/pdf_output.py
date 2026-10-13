"""Write offline tickmark overlays without changing source pages or judgments."""
import io
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject


def write_tickmark_pdf(source, overlays, output):
    reader = PdfReader(source)
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
    with open(output, 'wb') as stream:
        writer.write(stream)
