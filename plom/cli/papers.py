# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Aidan Murphy

from pprint import pprint

from plom.cli import with_messenger


@with_messenger
def list_papers(*, msgr, verbose=False):
    """Prints summary of uploads to each paper.

    Keyword Args:
        msgr (plom.Messenger/tuple): either a connected Messenger or a
            tuple appropriate for credentials.
        verbose (bool): print more information
    """
    info_dict = msgr.get_paper_composition_info()
    # these strings are magic
    unused_papers = info_dict["unused"]

    complete_papers = info_dict["complete"]
    incomplete_papers = info_dict["incomplete"]

    print("UNUSED PAPERS")
    print(", ".join(str(num) for num in unused_papers))
    print("\n")

    print("COMPLETE PAPERS")
    if verbose:
        pprint(info_dict["complete"])
    else:
        print(", ".join(str(num) for num in complete_papers))
    print("\n")

    print("INCOMPLETE PAPERS")
    if verbose:
        pprint(info_dict["incomplete"])
    else:
        print(", ".join(str(num) for num in incomplete_papers))
    print("\n")

    # print(tabulate(st, headers="firstrow"))
