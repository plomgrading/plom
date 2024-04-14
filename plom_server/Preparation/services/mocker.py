# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2024 Colin B. Macdonald

from __future__ import annotations

import pathlib
import shutil

from django.core.files import File
from django.conf import settings
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
    ) -> pathlib.Path:
        """Create the mock exam.

        Returns: path to the exam on disk.
        Side effect: saves a temp directory that needs to be removed later.
        """
        sources_dir = settings.MEDIA_ROOT / "sourceVersions"
        qr_code_temp_dir = sources_dir / "qr_temp"
        if qr_code_temp_dir.exists():
            shutil.rmtree(qr_code_temp_dir)
        qr_code_temp_dir.mkdir()

        qr_codes = create_QR_codes(1, 1, 1, "11111", qr_code_temp_dir)  # dummy values
        pdf_doc = fitz.open(source_path)
        for i in range(n_pages):
            page = pdf_doc[i]
            odd = i % 2 == 0
            pdf_page_add_labels_QRs(
                page, short_name, f"Mock exam version {version}", qr_codes, odd=odd
            )
        pdf_doc.save(qr_code_temp_dir / "mocked.pdf")
        pdf_doc.close()

        return qr_code_temp_dir / "mocked.pdf"
