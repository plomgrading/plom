# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

import os
from pathlib import Path
from plom.create.demotools import buildDemoSourceFiles
from plom.create.buildDatabaseAndPapers import check_equal_page_count

def test_equal_page_count(tmpdir):
    """Checks that the page counts of each source version pdf are equal.

    Arguments:
        tmpdir (dir): The directory holding the source version pdfs.

    Raises:
        ValueError: The page counts are not equal.
    """

    tmp = Path(tmpdir)
    # build the source version pdfs in sourceVersions/
    buildDemoSourceFiles(tmp, solutions=True)
    check_true = check_equal_page_count(tmp / "sourceVersions")
    print(check_true)
    assert check_true
    print(x for x in (tmp / "sourceVersions").glob("*.pdf"))
    # change the name of one of the solution pdfs to make the page counts unequal
    os.rename(tmp / "sourceVersions" / "solutions1.pdf", tmp / "sourceVersions" / "version3.pdf")
    # check that the page counts are no longer equal
    check_false = check_equal_page_count(tmp / "sourceVersions")
    print(check_false)
    assert not check_false
    print(x for x in (tmp / "sourceVersions").glob("*.pdf"))
    # change the name of the solution pdf back to solutions1.pdf
    os.rename(tmp / "sourceVersions" / "version3.pdf", tmp / "sourceVersions" / "solutions1.pdf")
