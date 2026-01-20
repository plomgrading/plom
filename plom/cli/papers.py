# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Aidan Murphy

from pprint import pprint

from plom.cli import with_messenger
from plom.misc_utils import format_int_list_with_runs


@with_messenger
def list_papers(*, msgr, verbose=False):
    """Prints summary of uploads to each paper.

    Keyword Args:
        msgr (plom.Messenger/tuple): either a connected Messenger or a
            tuple appropriate for credentials.
        verbose (bool): print more information.
    """
    info_dict = msgr.get_paper_composition_info()
    # these strings are magic
    unused_papers = info_dict["unused"]
    complete_papers = info_dict["complete"]
    incomplete_papers = info_dict["incomplete"]

    print("UNUSED PAPERS")
    if not unused_papers:
        print("*None*")
    elif verbose:
        print(unused_papers)
    else:
        print(format_int_list_with_runs(unused_papers))
    print("\n")

    print("COMPLETE PAPERS")
    if not complete_papers.keys():
        print("*None*")
    elif verbose:
        pprint(complete_papers)
    else:
        print(format_int_list_with_runs(complete_papers.keys()))
    print("\n")

    print("INCOMPLETE PAPERS")
    if not incomplete_papers.keys():
        print("*None*")
    elif verbose:
        pprint(incomplete_papers)
    else:
        print(format_int_list_with_runs(incomplete_papers.keys()))
    print("\n")
