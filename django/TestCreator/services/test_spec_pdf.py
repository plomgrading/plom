import pathlib
import fitz
from django.core.exceptions import MultipleObjectsReturned
from .. import models
from ..services import TestSpecService


class ReferencePDFService:
    """Keep track of the reference PDF"""
    def __init__(self, spec_service: TestSpecService):
        self.spec = spec_service

    def create_pdf(self, slug: str, pages: int, pdf) -> models.ReferencePDF:
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

    def delete_pdf(self):
        """
        Clear the ReferencePDF table
        """
        pdfs = models.ReferencePDF.objects.all()
        pdfs.delete()

    def new_pdf(self, slug, pages, file_bytes):
        """Create and save a new PDF given an opened file"""
        # print(type(file_bytes))
        # pdf_doc = fitz.open(stream=file_bytes)
        # if 'PDF' not in pdf_doc.metadata['format']:
        #     raise ValueError('File is not a valid PDF.')
        # if pdf_doc.page_count != pages:
        #     raise ValueError('Specification and PDF document have different number of pages.')
        
        self.delete_pdf()
        self.spec.clear_questions()  # clear questions from the test specification
        pdf = self.create_pdf(slug, pages, file_bytes)
        self.get_and_save_pdf_images()
        self.spec.set_pages(pdf)

        return pdf

    def get_pdf(self):
        """
        Get the reference PDF

        Raises:
            RuntimeError: if there is no PDF uploaded yet.
            MultipleObjectsReturned: if there is more than one Reference PDF saved to the database

        Returns:
            models.ReferencePDF: PDF object
        """
        pdfs = models.ReferencePDF.objects.all()
        if len(pdfs) == 0:
            raise RuntimeError('No Reference PDF found.')
        if len(pdfs) > 1:
            raise MultipleObjectsReturned('More than one Reference PDF saved.')

        return pdfs[0]

    def get_and_save_pdf_images(self) -> None:
        """
        Get raster image of each PDF page, and save them to disk for displaying

        Raises:
            RuntimeError: if the ReferencePDF's path doesn't point to a PDF
        """
        pdf = self.get_pdf()
        slug = pdf.filename_slug
        pathname = pathlib.Path('TestCreator') / 'media' / f'{slug}.pdf'
        if pathname.exists():
            pdf_doc = fitz.Document(pathname)

            thumbnail_dir = pathlib.Path('TestCreator') / 'static' / 'thumbnails'
            if not thumbnail_dir.exists():
                thumbnail_dir.mkdir()

            slug_dir = thumbnail_dir / slug
            if not slug_dir.exists():
                slug_dir.mkdir()

            for i in range(pdf_doc.page_count):
                page_pixmap = pdf_doc[i].get_pixmap()
                save_path = slug_dir / f'{slug}-thumbnail{i}.png'
                page_pixmap.save(save_path)

        else:
            raise RuntimeError(f'Document at {pathname} does not exist.')

    def create_page_thumbnail_list(self):
        """
        Create list of image paths to send to frontend for pdf thumbnail rendering

        Returns:
            list: page thumbnail paths
        """
        pdf = self.get_pdf()
        pages = []
        thumbnail_folder = pathlib.Path('thumbnails') / pdf.filename_slug
        for i in range(pdf.num_pages):
            thumbnail = thumbnail_folder / f'{pdf.filename_slug}-thumbnail{i}.png'
            pages.append(thumbnail)

        return pages


# """
# Service functions for models.ReferencePDF
# """

# def create_pdf(slug: str, pages: int, pdf) -> models.ReferencePDF:
#     """
#     Create a PDF in the database and save the file on disk

#     Args:
#         slug: url-safe filename (w/o extension)
#         pages: number of pages in the pdf
#         pdf: in-memory PDF file

#     Returns:
#         models.ReferencePDF: the reference PDF object
#     """
#     pdf = models.ReferencePDF(filename_slug=slug, num_pages=pages, pdf=pdf)
#     pdf.save()
#     return pdf


# def delete_pdf():
#     """
#     Clear the ReferencePDF table
#     """
#     pdfs = models.ReferencePDF.objects.all()
#     pdfs.delete()


# def get_and_save_pdf_images(pdf: models.ReferencePDF) -> None:
#     """
#     Get raster image of each PDF page, and save them to disk for displaying

#     Args:
#         pdf: ReferencePDF object
#     """
#     slug = pdf.filename_slug
#     pathname = pathlib.Path('TestCreator') / 'media' / f'{slug}.pdf'
#     if pathname.exists():
#         pdf_doc = fitz.Document(pathname)

#         thumbnail_dir = pathlib.Path('TestCreator') / 'static' / 'thumbnails'
#         if not thumbnail_dir.exists():
#             thumbnail_dir.mkdir()

#         slug_dir = thumbnail_dir / slug
#         if not slug_dir.exists():
#             slug_dir.mkdir()

#         for i in range(pdf_doc.page_count):
#             page_pixmap = pdf_doc[i].get_pixmap()
#             save_path = slug_dir / f'{slug}-thumbnail{i}.png'
#             page_pixmap.save(save_path)

#     else:
#         raise RuntimeError(f'Document at {pathname} does not exist.')


# def create_page_thumbnail_list(pdf: models.ReferencePDF):
#     """
#     Create list of image paths to send to frontend for pdf thumbnail rendering

#     Args:
#         pdf: ReferencePDF object

#     Returns:
#         list: page thumbnail paths
#     """

#     pages = []
#     thumbnail_folder = pathlib.Path('thumbnails') / pdf.filename_slug
#     for i in range(pdf.num_pages):
#         thumbnail = thumbnail_folder / f'{pdf.filename_slug}-thumbnail{i}.png'
#         pages.append(thumbnail)

#     return pages
