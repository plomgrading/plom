# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2024-2025 Colin B. Macdonald
# Copyright (C) 2024 Aidan Murphy

import tempfile
from pathlib import Path

from django.core.files import File
import pymupdf

from plom.create.mergeAndCodePages import (
    create_QR_codes,
    pdf_page_add_labels_QRs,
    pdf_page_add_name_id_box,
    make_PDF,
)

from plom_server.Papers.services import SpecificationService
from .preparation_dependency_service import assert_can_modify_prenaming_config


class ExamMockerService:
    """Take an uploaded source file and stamp dummy QR codes/text."""

    def mock_exam(
        self,
        version: int,
        source_path: str | Path | File,
        n_pages: int,
        short_name: str,
    ) -> bytes:
        """Create the mock exam.

        Returns: a bytes object containing the document.
        """
        spec = SpecificationService.get_the_spec()
        num_questions = SpecificationService.get_n_questions()
        # ensure mocked papers won't scan by using wrong public code
        if spec["publicCode"] == "00000":
            spec["publicCode"] = "99999"
        else:
            spec["publicCode"] = "00000"

        with tempfile.TemporaryDirectory() as tmpdirname:
            tmpdir = Path(tmpdirname)
            qvmap_row = {n: version for n in range(1, num_questions + 1)}
            qvmap_row["id"] = version
            qvmap_row["dnm"] = version
            f = make_PDF(
                spec,
                0,
                qvmap_row,
                where=tmpdir,
                source_versions={version: source_path},
            )
            with pymupdf.open(f) as pdf_doc:
                return pdf_doc.tobytes()

    def mock_ID_page(
        self,
        version: int,
        xcoord: float,
        ycoord: float,
    ) -> bytes:
        """Mock the ID page of a prenamed exam.

        Returns: a bytes object containing the PDF document.
        """
        assert_can_modify_prenaming_config()
        # TODO: refactor to delocalize this import, SourceService and mocker are circular
        from .SourceService import _get_source_file

        short_name = SpecificationService.get_short_name_slug()
        # TODO: Issue #3888, local path access may fail on remote file storage
        source_path = Path(_get_source_file(version).path)
        id_page_number = SpecificationService.get_id_page_number()
        return self._make_prename_box_page(
            version,
            source_path,
            id_page_number,
            short_name,
            xcoord,
            ycoord,
            extra={"name": "McMockFace, Mocky", "id": "00000001"},
        )

    # TODO: unit tests
    def _make_prename_box_page(
        self,
        version: int,
        source_path: str | Path | File,
        page_num: int,
        short_name: str,
        xcoord: float,
        ycoord: float,
        extra: dict = {"name": "", "id": ""},
        return_pdf: bool = False,
    ) -> bytes:
        """Mock an prenamed ID page on the specified page.

        Returns: a bytes object containing the id page as a png or pdf, depending on `return_pdf`.
        """
        with tempfile.TemporaryDirectory() as tmpdirname:
            with pymupdf.open(source_path) as pdf_doc:
                pdf_doc.select([page_num - 1])
                ID_page = pdf_doc[0]
                qr_codes = create_QR_codes(
                    1, 1, version, "00000", Path(tmpdirname)
                )  # dummy values
                odd = page_num % 2 != 0
                pdf_page_add_labels_QRs(
                    ID_page,
                    short_name,
                    f"Mock exam v {version} pg {page_num}",
                    qr_codes,
                    odd=odd,
                )

                pdf_page_add_name_id_box(
                    ID_page, extra["name"], extra["id"], xcoord, ycoord
                )
                if not return_pdf:
                    return ID_page.get_pixmap().tobytes()

                return pdf_doc.tobytes()
