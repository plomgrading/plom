# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2023 Colin B. Macdonald
# Copyright (C) 2021 Jed Yeo

from plom.misc_utils import format_int_list_with_runs
from plom.scan import with_scanner_messenger
from plom.scan.listBundles import print_bundle_list


@with_scanner_messenger
def check_and_print_scan_status(papers, unknowns, bundles, *, msgr):
    """Prints summary of test/hw uploads.

    What is printed is controlled by some boolean switches except that
    if all switches are false, we print everything.

    Args:
        papers (bool): print info on test papers.
        unknowns (bool): print info on unknown pages.
        bundles (bool): print info about bundles.

    Keyword Args:
        msgr (plom.Messenger/tuple): either a connected Messenger or a
            tuple appropriate for credientials.

    Returns:
        None
    """
    if not any((papers, unknowns, bundles)):
        papers = unknowns = bundles = True
    dirty = False
    if papers:
        check_and_print_scan_status_papers(msgr=msgr)
        dirty = True
    if unknowns:
        if dirty:
            print("\n" + "- " * 44 + "\n")
        check_and_print_scan_status_unknowns(msgr=msgr)
        dirty = True
    if bundles:
        if dirty:
            print("\n" + "- " * 44 + "\n")
        print_bundle_list(table_width=88, msgr=msgr)


@with_scanner_messenger
def check_and_print_scan_status_papers(*, msgr):
    """Prints summary of test/hw uploads.

    More precisely. Prints lists
    * which tests have been used (ie at least one uploaded page)
    * which tests completely scanned (both tpages and hwpage)
    * incomplete tests (missing one tpage or one hw-question)
    """
    print("# Test paper info\n")

    # returns pairs of [page,version] - only display pages
    ST = msgr.getScannedTests()
    UT = msgr.getUnusedTests()
    IT = msgr.getIncompleteTests()

    print("Test papers unused: [{}]".format(format_int_list_with_runs(UT)))

    print("Scanned tests in the system:")
    for t in ST:
        scannedTPages = []
        scannedHWPages = []
        for x in ST[t]:
            if x[0][0] == "t":  # is a test page = "t.p"
                p = int(x[0].split(".")[1])
                scannedTPages.append(p)
            elif x[0][0] == "h":  # is a hw page = "h.q.o"
                q = int(x[0].split(".")[1])
                if q not in scannedHWPages:
                    scannedHWPages.append(q)

        print(
            "\t{}: testPages [{}] hwPages [{}]".format(
                t,
                format_int_list_with_runs(scannedTPages),
                format_int_list_with_runs(scannedHWPages),
            )
        )
    print("Number of scanned tests in the system: {}".format(len(ST)))

    if len(IT) == 0:
        print(f"Incomplete scans: {len(IT)}")
    else:
        print(f"Incomplete scans: {len(IT)} - listed with their missing pages: ")
    for t in IT:
        missingPagesT = []
        missingPagesH = []
        for x in IT[t]:  # each entry is [page, version, scanned?]
            if x[0][0] == "t":  # is a test page
                p = int(x[0].split(".")[1])
                if x[2] is False:
                    missingPagesT.append(p)
            elif x[0][0] == "h":  # is a w page
                q = int(x[0].split(".")[1])
                if x[2] is False:
                    missingPagesH.append(q)
        print(
            "\t{}: t[{}] h[{}]".format(
                t,
                format_int_list_with_runs(missingPagesT),
                format_int_list_with_runs(missingPagesH),
            )
        )


@with_scanner_messenger
def check_and_print_scan_status_unknowns(*, msgr):
    """Prints summary of unknown pages.

    Keyword Args:
        msgr (plom.Messenger/tuple): either a connected Messenger or a
            tuple appropriate for credientials.
    """
    print("# Unknown page info\n")
    unknown_pagedata = msgr.getUnknownPages()
    N = len(unknown_pagedata)
    is_are = "is" if N == 1 else "are"
    page_or_pages = "page" if N == 1 else "pages"
    extra = "." if N == 0 else ": (use the Manager tool to address)"
    print(f"There {is_are} currently {N} unknown {page_or_pages}{extra}")
    for p in unknown_pagedata:
        print(
            f'\t{p["pagename"]} (p. {p["bundle_position"]} in bundle {p["bundle_name"]})'
        )
