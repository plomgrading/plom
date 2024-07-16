# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024 Colin B. Macdonald

from pathlib import Path

from .build_extra_page_with_qrcodes import build_extra_page_pdf
from ..misc_utils import working_directory


def test_extra_page_pdf_no_dir(tmpdir) -> None:
    """Builds the extra_page pdf with no directory specified and confirms it works.

    Arguments:
        tmpdir (dir): The directory that we are building the files in.
    """
    with working_directory(tmpdir):
        build_extra_page_pdf()
        assert Path("extra_page.pdf").exists()


def test_extra_page_pdf_with_dir(tmpdir) -> None:
    """Builds the extra_page pdf with a directory specified and confirms it works.

    Arguments:
        tmpdir (dir): The directory that we are building the files in.
    """
    with working_directory(tmpdir):
        path_foo = Path(tmpdir) / "Foo"
        path_foo.mkdir()
        build_extra_page_pdf(destination_dir=path_foo)
        assert (path_foo / "extra_page.pdf").exists()
