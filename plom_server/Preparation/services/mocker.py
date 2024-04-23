# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2024 Colin B. Macdonald

from __future__ import annotations

import pathlib
import tempfile

from django.core.files import File
import fitz

from plom.create.mergeAndCodePages import create_QR_codes, pdf_page_add_labels_QRs


class ExamMockerService:
    """Take an uploaded source file and stamp dummy QR codes/text."""

    def mock_exam(
        self,
        version: int,
        source_path: str | pathlib.Path | File,
        n_pages: int,
        short_name: str,
    ) -> bytes:
        """Create the mock exam.

        Returns: a bytes object containing the document.
        """
        with tempfile.TemporaryDirectory() as tmpdirname:
            pdf_doc = fitz.open(source_path)
            for i in range(n_pages):
                qr_codes = create_QR_codes(
                    1, i + 1, version, "00000", pathlib.Path(tmpdirname)
                )  # dummy values
                page = pdf_doc[i]
                odd = i % 2 == 0
                pdf_page_add_labels_QRs(
                    page, short_name, f"Mock exam version {version}", qr_codes, odd=odd
                )
        return pdf_doc.tobytes()
