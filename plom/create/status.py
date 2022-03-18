# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Colin B. Macdonald

from plom import SpecVerifier
from plom.create import with_manager_messenger
from plom.plom_exceptions import PlomServerNotReady, PlomBenignException


# support for colour checkmarks
ansi_green = "\033[92m"
ansi_yellow = "\033[93m"
ansi_red = "\033[91m"
ansi_off = "\033[0m"
warn_mark = "[" + ansi_yellow + "!" + ansi_off + "]"
cross = "[" + ansi_red + "\N{Multiplication Sign}" + ansi_off + "]"
check_mark = "[" + ansi_green + "\N{Check Mark}" + ansi_off + "]"


@with_manager_messenger
def status(*, msgr):
    """Status information about a server.

    Keyword Args:
        msgr (plom.Messenger/tuple): either a connected Messenger or a
            tuple appropriate for credientials.
    """
    print("Specification")
    print("-------------\n")
    try:
        spec = msgr.get_spec()
    except PlomServerNotReady:
        print(cross + " Server does not yet have a spec")
        print("    You will need to add specification for your test.")
    else:
        print(check_mark + " Server has a spec ")
        sv = SpecVerifier(spec)
        print(sv)
        # maybe above printer should do this?
        print(f"  Server public code: {spec['publicCode']}")

    print("\nUser information")
    print("----------------\n")
    users = msgr.getUserDetails()
    users.pop("HAL")
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
    except PlomBenignException as e:
        # TODO: make PlomServerHasNoClasslist: subclass of PlomServerNotReady?
        print(cross + f" No classlist: {e}")

    print("\nDatabase")
    print("---------\n")
    # TODO
