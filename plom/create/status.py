# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Colin B. Macdonald
# Copyright (C) 2022 Natalia Accomazzo Scotti

from textwrap import wrap

from plom import SpecVerifier
from plom.create import with_manager_messenger
from plom.plom_exceptions import PlomServerNotReady, PlomNoClasslist
from plom.misc_utils import format_int_list_with_runs


# support for colour checkmarks
ansi_green = "\033[92m"
ansi_yellow = "\033[93m"
ansi_red = "\033[91m"
ansi_off = "\033[0m"
warn_mark = "[" + ansi_yellow + "!" + ansi_off + "]"
cross = "[" + ansi_red + "\N{MULTIPLICATION SIGN}" + ansi_off + "]"
question_mark = "[" + ansi_red + "?" + ansi_off + "]"
check_mark = "[" + ansi_green + "\N{CHECK MARK}" + ansi_off + "]"


@with_manager_messenger
def status(*, msgr) -> None:
    """Status information about a server.

    Keyword Args:
        msgr (plom.Messenger/tuple): either a connected Messenger or a
            tuple appropriate for credientials.
    """
    # TODO: this can't really fail without the decorator stuff failing!
    # TODO: need contextmanager for messenger so we can start it later
    # then we can try except PlomAPIException (e.g., see chooser.py)
    # see https://gitlab.com/plom/plom/-/merge_requests/1275
    print("Server status")
    print("-------------\n")
    srv_ver = msgr.get_server_version()
    if "Plom" in srv_ver:
        print(check_mark + f" online: {msgr.server}")
        print(check_mark + f" {srv_ver}")
    else:
        print(question_mark + f" cannot find a Plom server at {msgr.server}")

    if msgr.scheme != "https":
        print(warn_mark + " insecure connection (http instead of https)")
    elif msgr.is_ssl_verified():
        print(check_mark + " secure connection verified with SSL")
    else:
        print(warn_mark + " insecure connection (self-signed or invalid SSL cert)")

    print("\nSpecification")
    print("-------------\n")
    try:
        spec = msgr.get_spec()
        exam_info = msgr.get_exam_info()
    except PlomServerNotReady:
        print(cross + " Server does not yet have a spec")
        print("    You will need to add specification for your test.")
        spec = None
        exam_info = None
    else:
        print(check_mark + " Server has a spec ")
        sv = SpecVerifier(spec)
        print(sv)
        # maybe above printer should do this?
        print(f"  Server public code: {spec['publicCode']}")

    print("\nUser information")
    print("----------------\n")
    users = msgr.getUserDetails()
    if users.pop("manager", None):
        print(check_mark + " manager account")
    else:
        print(cross + " no manager account: how can you even see this!?")
    if users.pop("scanner", None):
        print(check_mark + " scanner account")
    else:
        print(warn_mark + " no scanner account: you will not be able to upload")
    if users.pop("reviewer", None):
        print(check_mark + " reviewer account")
    else:
        print(warn_mark + " no reviewer: likely harmless as this is a beta feature")
    if len(users) > 0:
        print(check_mark + f" {len(users)} user accounts: ")
        print("    " + ", ".join(users.keys()))
    else:
        print(warn_mark + " No user accounts yet")

    print("\nClasslist")
    print("---------\n")

    try:
        classlist = msgr.IDrequestClasslist()
        print(check_mark + f" Server has a classlist with {len(classlist)} entries")
    except PlomNoClasslist as e:
        print(cross + f" No classlist: {e}")
        classlist = None
    if classlist and classlist[0].get("paper_number", None):
        # classlist has papernum column
        papernums = [
            int(r["paper_number"]) for r in classlist if int(r["paper_number"]) > 0
        ]
        if len(set(papernums)) != len(papernums):
            print(cross + ' "paper_number" fields are not unique!')
        else:
            print(
                check_mark
                + f' {len(papernums)} have "paper_number" field for prenaming:'
            )
            print(
                "    " + "\n    ".join(wrap(format_int_list_with_runs(papernums), 72))
            )
    else:
        papernums = []
    if spec and exam_info:
        # TODO: Issue #1745: this assumes contiguous test numbers
        not_named = set(range(1, exam_info["current_largest_paper_num"]))
        not_named.difference_update(papernums)
        print(
            check_mark
            + f" {len(not_named)} unassigned paper numbers (these will not be prenamed):"
        )
        print(
            "    " + "\n    ".join(wrap(format_int_list_with_runs(list(not_named)), 72))
        )

    print("\nDatabase")
    print("--------\n")
    vmap = msgr.getGlobalQuestionVersionMap()
    if len(vmap) > 0:
        print(check_mark + f" There are {len(vmap)} rows in the papers table")
    elif spec is None:
        print(cross + " No rows have been inserted in the papers table")
        print("    (you will not be able to add any until you add a spec)")
    else:
        print(warn_mark + " No rows have been inserted in the papers table")

    print("\nRubrics")
    print("-------\n")
    rubs = msgr.MgetRubrics()
    if len(rubs) == 0:
        print("Server does not yet have any rubrics")
    else:
        print(f"Server has {len(rubs)} rubrics")
        userrubs = [r for r in rubs if r["username"] != "manager"]
        print(f"  {len(userrubs)} created by users")
