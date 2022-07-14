import pathlib
import fitz
from .. import models
from . import *

"""
Service functions for models.ReferencePDF
"""

def create_pdf(slug: str, pages: int, pdf) -> models.ReferencePDF:
    """
    Create a PDF in the database and save the file on disk

    Args:
        slug: url-safe filename (w/o extension)
        pages: number of pages in the pdf
        pdf: in-memory PDF file

    Returns:
        models.ReferencePDF: the reference PDF object
    """
    pdf = models.ReferencePDF(filename_slug=slug, num_pages=pages, pdf=pdf)
    pdf.save()
    return pdf


def delete_pdf():
    """
    Clear the ReferencePDF table
    """
    pdfs = models.ReferencePDF.objects.all()
    pdfs.delete()


def get_and_save_pdf_images(pdf: models.ReferencePDF) -> None:
    """
    Get raster image of each PDF page, and save them to disk for displaying

    Args:
        pdf: ReferencePDF object
    """
    slug = pdf.filename_slug
    pathname = pathlib.Path('TestCreator') / 'media' / f'{slug}.pdf'
    # TODO: use pathlib
    if pathname.exists():
        pdf_doc = fitz.Document(pathname)

        thumbnail_dir = pathlib.Path('TestCreator') / 'static' / 'thumbnails' / slug
        if not thumbnail_dir.exists():
            thumbnail_dir.mkdir()

        for i in range(pdf_doc.page_count):
            page_pixmap = pdf_doc[i].get_pixmap()
            save_path = thumbnail_dir / f'{slug}-thumbnail{i}.png'
            page_pixmap.save(save_path)

    else:
        raise RuntimeError(f'Document at {pathname} does not exist.')


def create_page_thumbnail_list(pdf: models.ReferencePDF):
    """
    Create list of image paths to send to frontend for pdf thumbnail rendering

    Args:
        pdf: ReferencePDF object

    Returns:
        list: page thumbnail paths
    """

    pages = []
    thumbnail_folder = pathlib.Path('thumbnails') / pdf.filename_slug
    for i in range(pdf.num_pages):
        thumbnail = thumbnail_folder / f'{pdf.filename_slug}-thumbnail{i}.png'
        pages.append(thumbnail)

    return pages
