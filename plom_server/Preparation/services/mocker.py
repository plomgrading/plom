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
        # TODO: refactor to delocalize this import, SourceService and mocker are circular
        from .SourceService import _get_source_file

        # TODO: Issue #3888 this does direct file access, fails for remote storage?
        __, abstract_django_file = _get_source_file(version)
        source_path = Path(abstract_django_file.path)

        try:
            return cls._mock_exam_with_spec(source_path, version)
        except ObjectDoesNotExist:
            return cls._mock_exam_without_spec(source_path, version)

    @staticmethod
    def _mock_exam_with_spec(source_path: Path, version: int) -> bytes:
        """Fetch the exam spec and create the mock exam.

        Args:
            source_path: the path to the exam sourcefile
            version: the version to mock

        Returns:
            A bytes object containing the document.
        """
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
            with pymupdf.open(f) as pdf_doc:
                return pdf_doc.tobytes()

    @staticmethod
    def _mock_exam_without_spec(source_path: Path, version: int) -> bytes:
        """Create a mock exam without the spec.

        This is a bit lower-level than the preferred
        :method:`_mock_exam_with_spec`.

        Args:
            source_path: the path to the exam sourcefile.
            version: the version to mock.

        Returns:
            A bytes object containing the document.
        """
        example_code = _make_example_public_code()
        papernum = 1

        with tempfile.TemporaryDirectory() as tmpdirname:
            with pymupdf.open(source_path) as pdf_doc:
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

                return pdf_doc.tobytes()

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
