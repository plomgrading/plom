# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2024-2026 Colin B. Macdonald
# Copyright (C) 2024, 2026 Aidan Murphy

import tempfile
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
import pymupdf

from plom.create import make_PDF, create_QR_codes
from plom.create.mergeAndCodePages import pdf_page_add_labels_QRs
from plom_server.Base.services import Settings
from plom_server.Papers.services import SpecificationService
from .preparation_dependency_service import assert_can_modify_prenaming_config


def _make_example_public_code() -> str:
    code = "000000"
    public_code = Settings.get_public_code()
    if public_code is not None:
        assert len(public_code) == 6
    # ensure mocked papers won't scan by using wrong public code
    if code == public_code:
        code = "999999"
    return code


class ExamMockerService:
    """Take an uploaded source file and stamp dummy QR codes/text."""

    @classmethod
    def mock_exam(cls, version: int) -> bytes:
        """Create the mock exam.

        Args:
            version: which version to mock.

        Returns:
            A bytes object containing the document.
        """
        try:
            pdf_doc = cls._mock_exam_with_spec(version)
        except ObjectDoesNotExist:
            pdf_doc = cls._mock_exam_without_spec(version)
        b = pdf_doc.tobytes()
        pdf_doc.close()
        return b

    @staticmethod
    def _mock_exam_with_spec(version: int) -> pymupdf.Document:
        """Fetch the exam spec and create the mock exam.

        Args:
            source_path: the path to the exam sourcefile
            version: the version to mock

        Returns:
            An open PDF document: careful, you must close it.
        """
        # TODO: refactor to delocalize this import, SourceService and mocker are circular
        from .SourceService import _get_source_file

        # TODO: Issue #3888 this does direct file access, fails for remote storage?
        __, abstract_django_file = _get_source_file(version)
        source_path = Path(abstract_django_file.path)

        example_code = _make_example_public_code()
        spec = SpecificationService.get_the_spec()
        num_questions = SpecificationService.get_n_questions()

        with tempfile.TemporaryDirectory() as tmpdirname:
            tmpdir = Path(tmpdirname)

            _keys = ["id", "dnm", *range(1, num_questions + 1)]
            qvmap_row = {k: version for k in _keys}

            f = make_PDF(
                spec,
                0,
                qvmap_row,
                public_code=example_code,
                where=tmpdir,
                source_versions={version: source_path},
                paperstr="<Mock>",
                qr_code_size=settings.PLOM_QR_CODE_SIZE,
            )
            return pymupdf.open(f)

    @staticmethod
    def _mock_exam_without_spec(source_path: Path, version: int) -> pymupdf.Document:
        """Create a mock exam without the spec.

        This is a bit lower-level than the preferred
        :method:`_mock_exam_with_spec`.

        Args:
            source_path: the path to the exam sourcefile.
            version: the version to mock.

        Returns:
            An open PDF document: careful, you must close it.
        """
        # TODO: refactor to delocalize this import, SourceService and mocker are circular
        from .SourceService import _get_source_file

        # TODO: Issue #3888 this does direct file access, fails for remote storage?
        __, abstract_django_file = _get_source_file(version)
        source_path = Path(abstract_django_file.path)

        example_code = _make_example_public_code()
        papernum = 1

        with tempfile.TemporaryDirectory() as tmpdirname:
            pdf_doc = pymupdf.open(source_path)
            if True:
                for index, page in enumerate(pdf_doc):
                    qr_codes = create_QR_codes(
                        papernum, index + 1, version, example_code, Path(tmpdirname)
                    )
                    page = pdf_doc[index]
                    odd = index % 2 == 0
                    pdf_page_add_labels_QRs(
                        page,
                        "mock_shortname",
                        f"Mock label pg. {index+1}",
                        qr_codes,
                        odd=odd,
                    )
                return pdf_doc

    @staticmethod
    def mock_ID_page(
        version: int,
        xcoord: float,
        ycoord: float,
    ) -> bytes:
        """Mock the ID page of a prenamed exam.

        Returns: a bytes object containing the PDF document.
        """
        assert_can_modify_prenaming_config()

        spec = SpecificationService.get_the_spec()
        num_questions = SpecificationService.get_n_questions()
        id_page_number = SpecificationService.get_id_page_number()
        example_code = _make_example_public_code()

        # TODO: refactor to delocalize this import, SourceService and mocker are circular
        from .SourceService import _get_source_file

        # TODO: Issue #3888, local path access may fail on remote file storage
        __, abstract_django_file = _get_source_file(version)
        source_path = Path(abstract_django_file.path)

        with tempfile.TemporaryDirectory() as tmpdirname:
            tmpdir = Path(tmpdirname)

            _keys = ["id", "dnm", *range(1, num_questions + 1)]
            qvmap_row = {k: version for k in _keys}

            # we build the entire paper even though we only want the ID page
            f = make_PDF(
                spec,
                0,
                qvmap_row,
                {"name": "McMockFace, Mocky", "id": "00000001"},
                xcoord,
                ycoord,
                public_code=example_code,
                where=tmpdir,
                source_versions={version: source_path},
                paperstr="<Mock>",
                qr_code_size=settings.PLOM_QR_CODE_SIZE,
            )
            with pymupdf.open(f) as pdf_doc:
                # id_page_number is indexed from 1
                return pdf_doc[id_page_number - 1].get_pixmap().tobytes()

    @classmethod
    def get_temp_rendered_regions_page(
        cls,
        pg: int,
        version: int,
        regions,
    ) -> bytes:
        """Render a mock up of some regions on a particular page.

        Args:
            pg: which page, indexed from 1
            version: which version.
            regions: list of regions to draw,

        Returns:
            The bytes of a png image of that page, rendered with regions
            shown translucently.
        """
        try:
            pdf_doc = cls._mock_exam_with_spec(version)
        except ObjectDoesNotExist:
            pdf_doc = cls._mock_exam_without_spec(version)
        page = pdf_doc[pg - 1]
        # borrowed from GNU Octave's defaults ("help lines")
        colour_choices = (
            (0, 0.447, 0.741),
            (0.850, 0.325, 0.098),
            (0.929, 0.694, 0.125),
            (0.494, 0.184, 0.556),
            (0.466, 0.674, 0.188),
            (0.301, 0.745, 0.933),
            (0.635, 0.078, 0.184),
        )

        i = 0
        for qidx_str, region in regions.items():
            print(region)
            if not region:
                continue
            if len(region) != 1:
                raise NotImplementedError("multiple regions per question")
            rect = region[0]["rect"]
            colour = colour_choices[i % len(colour_choices)]
            w = page.rect.width
            h = page.rect.height
            s = 4  # stroke width
            pg_unit_rect = [
                rect[0] * w + s / 2,
                rect[1] * h + s / 2,
                (rect[0] + rect[2]) * w - s / 2,
                (rect[1] + rect[3]) * h - s / 2,
            ]
            # clarify overly by offset even/odd horizontally (maybe distracting?)
            pg_unit_rect[0] += (i % 2) * s
            pg_unit_rect[2] -= ((i + 1) % 2) * s
            i += 1
            page.draw_rect(
                pg_unit_rect,
                color=colour,
                fill=colour,
                fill_opacity=0.15,
                stroke_opacity=0.65,
                width=s,
            )
            page.insert_text(
                (pg_unit_rect[0] + 1.5 * s, (pg_unit_rect[1] + pg_unit_rect[3]) / 2),
                "Q" + qidx_str,  # TODO need question label
                fontsize=24,
                color=colour,
            )

        b = page.get_pixmap().tobytes()
        pdf_doc.close()
        return b
