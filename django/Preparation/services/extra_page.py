from django.conf import settings
from django.core.files import File
from django.db import transaction

from Preparation.models import ExtraPagePDF

import logging
from pathlib import Path
from tempfile import NamedTemporaryFile

log = logging.getLogger("ExtraPageService")


class ExtraPageService:
    base_dir = settings.BASE_DIR
    papers_to_print = base_dir / "papersToPrint"

    @transaction.atomic()
    def is_there_an_extra_page_pdf(self):
        return ExtraPagePDF.objects.exists()

    @transaction.atomic()
    def get_extra_page_pdf_filepath(self):
        return ExtraPagePDF.objects.get().extra_page_pdf.path

    @transaction.atomic()
    def delete_extra_page_pdf(self):
        # explicitly delete the file, since it is not done automagically by django
        # TODO - make this a bit cleaner.
        if ExtraPagePDF.objects.exists():
            Path(ExtraPagePDF.objects.get().extra_page_pdf.path).unlink()
            ExtraPagePDF.objects.filter().delete()

    @transaction.atomic()
    def build_extra_page_pdf(self):
        if self.is_there_an_extra_page_pdf():
            return
        from plom.create import build_extra_page_pdf
        # TODO - make non-blocking via a huey task
        build_extra_page_pdf()
        epp_path = Path("extra_page.pdf")
        epp_obj = ExtraPagePDF()
        with epp_path.open(mode="rb") as fh:
            epp_obj.extra_page_pdf = File(fh, name=epp_path.name)
            epp_obj.save()
        # TODO - work out better file wrangling so we don't have to delete this leftover.
        epp_path.unlink()
