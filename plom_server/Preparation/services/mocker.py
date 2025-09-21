# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2024-2025 Colin B. Macdonald
# Copyright (C) 2024 Aidan Murphy

import tempfile
from pathlib import Path

import pymupdf

from plom.create.mergeAndCodePages import make_PDF
from plom_server.Papers.services import SpecificationService
from .preparation_dependency_service import assert_can_modify_prenaming_config


class ExamMockerService:
    """Take an uploaded source file and stamp dummy QR codes/text."""

    @staticmethod
    def mock_exam(version: int) -> bytes:
        """Create the mock exam.

        Args:
            version: which version to mock.

        Returns:
            A bytes object containing the document.
        """
        spec = SpecificationService.get_the_spec()
        num_questions = SpecificationService.get_n_questions()

        # TODO: refactor to delocalize this import, SourceService and mocker are circular
        from .SourceService import _get_source_file

        # TODO: Issue #3888 this does direct file access, fails for remote storage?
        source_path = Path(_get_source_file(version).path)

        if spec.get("publicCode"):
            # ensure mocked papers won't scan by using wrong public code
            assert len(spec["publicCode"]) == 6
            if spec["publicCode"] == "000000":
                spec["publicCode"] = "999999"
            else:
                spec["publicCode"] = "000000"
        else:
            spec["publicCode"] = "000000"

        with tempfile.TemporaryDirectory() as tmpdirname:
            tmpdir = Path(tmpdirname)

            _keys = ["id", "dnm", *range(1, num_questions + 1)]
            qvmap_row = {k: version for k in _keys}

            f = make_PDF(
                spec,
                0,
                qvmap_row,
                where=tmpdir,
                source_versions={version: source_path},
                paperstr="<Mock>",
            )
            with pymupdf.open(f) as pdf_doc:
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

        # TODO: refactor to delocalize this import, SourceService and mocker are circular
        from .SourceService import _get_source_file

        # TODO: Issue #3888, local path access may fail on remote file storage
        source_path = Path(_get_source_file(version).path)

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
                where=tmpdir,
                source_versions={version: source_path},
                paperstr="<Mock>",
            )
            with pymupdf.open(f) as pdf_doc:
                # id_page_number is indexed from 1
                return pdf_doc[id_page_number - 1].get_pixmap().tobytes()
