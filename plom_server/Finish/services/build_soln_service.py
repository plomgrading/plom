# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

import fitz
from pathlib import Path
import tempfile

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from .soln_source import SolnSourceService
from .reassemble_service import ReassembleService


from Papers.models import (
    SolnSpecQuestion,
    Paper,
    QuestionPage,
)
from Finish.models import SolutionSourcePDF


class BuildSolutionService:
    """Class that contains helper functions for sending data to plom-finish."""

    base_dir = settings.MEDIA_ROOT
    reassemble_dir = base_dir / "reassemble"

    def watermark_pages(self, doc, watermark_text):
        margin = 10
        for pg in doc:
            h = pg.rect.height
            wm_rect = fitz.Rect(margin, h - margin - 32, margin + 200, h - margin)
            excess = pg.insert_textbox(
                wm_rect,
                watermark_text,
                fontsize=18,
                color=(0, 0, 0),
                align=1,
                stroke_opacity=0.33,
                fill_opacity=0.33,
                overlay=True,
            )
            assert (
                excess > 0
            ), f"Text didn't fit: is SID label too long? {watermark_text}"
            pg.draw_rect(wm_rect, color=[0, 0, 0], stroke_opacity=0.25)

    def assemble_solution_for_paper(self, paper_number, watermark=False):
        try:
            paper_obj = Paper.objects.get(paper_number=paper_number)
        except ObjectDoesNotExist:
            raise ValueError(f"Cannot find paper {paper_number}")

        if not SolnSourceService().are_all_solution_pdf_present():
            raise ValueError(
                "Cannot assemble solutions until all source solution pdfs uploaded"
            )
        # get the version of each question
        qv_map = {}
        for qp_obj in QuestionPage.objects.filter(paper=paper_obj):
            qv_map[qp_obj.question_number] = qp_obj.version
        # get the solution pdfs
        soln_doc = {}
        for spdf_obj in SolutionSourcePDF.objects.all():
            soln_doc[spdf_obj.version] = fitz.open(spdf_obj.source_pdf.path)

        # build the solution coverpage in a tempdir
        # open it as a fitz doc and then append the soln pages to it.
        reas = ReassembleService()
        with tempfile.TemporaryDirectory() as tmpdir:
            cp_path = reas.build_paper_cover_page(
                Path(tmpdir), paper_obj, solution=True
            )
            dest_doc = fitz.open(cp_path)
        # now append required soln pages.
        for qn, v in qv_map.items():
            pg_list = SolnSpecQuestion.objects.get(solution_number=qn).pages
            dest_doc.insert_pdf(
                soln_doc[v], pg_list[0] - 1, pg_list[-1] - 1
            )  # pymupdf pages are 0-indexed

        if watermark:
            sid_sname_pair = reas.get_paper_id_or_none(paper_obj)
            if sid_sname_pair:
                self.watermark_pages(dest_doc, f"Solutions for {sid_sname_pair[0]}")

        return dest_doc.tobytes()
