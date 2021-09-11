# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2021 Colin B. Macdonald

from stdiomask import getpass

from plom import check_version_map
from plom.produce import build_all_papers, confirm_processed, identify_prenamed, build_specific_paper
from plom.produce import paperdir
from plom.messenger import ManagerMessenger
from plom.plom_exceptions import PlomExistingDatabase


def build_papers(server=None, password=None, *, fakepdf=False, no_qr=False, number=None, ycoor=None):
    if server and ":" in server:
        s, p = server.split(":")
        msgr = ManagerMessenger(s, port=p)
    else:
        msgr = ManagerMessenger(server)
    msgr.start()

    if not password:
        password = getpass('Please enter the "manager" password: ')

    msgr.requestAndSaveToken("manager", password)
    try:
        spec = msgr.get_spec()
        pvmap = msgr.getGlobalPageVersionMap()
        paperdir.mkdir(exist_ok=True)

        if number:
            classlist = msgr.IDrequestClasslist()
            print(
                'Building pre-named paper number {} in "{}"...'.format(
                    number,
                    paperdir,
                )
            )
            build_specific_paper(spec, pvmap, classlist, fakepdf=fakepdf, no_qr=no_qr, numberToMake=number, ycoor=ycoor)
        else:

            if spec["numberToName"] > 0:
                classlist = msgr.IDrequestClasslist()
                print(
                    'Building {} pre-named papers and {} blank papers in "{}"...'.format(
                        spec["numberToName"],
                        spec["numberToProduce"] - spec["numberToName"],
                        paperdir,
                    )
                )
            else:
                classlist = None
                print(
                    'Building {} blank papers in "{}"...'.format(
                        spec["numberToProduce"], paperdir
                    )
                )
            build_all_papers(spec, pvmap, classlist, fakepdf=fakepdf, no_qr=no_qr, ycoor=ycoor)

        print("Checking papers produced and updating databases")
        confirm_processed(spec, msgr, classlist)
        print("Identifying any pre-named papers into the database")
        identify_prenamed(spec, msgr, classlist)
    finally:
        msgr.closeUser()
        msgr.stop()


def build_database(server=None, password=None, vermap={}):
    """Build the database from a pre-set version map.

    args:
        vermap (dict): question version map.  If empty dict, server will
            make its own mapping.  For the map format see
            :func:`plom.finish.make_random_version_map`.
        server (str):
        password (str):

    return:
        str: long multiline string of all the version DB entries.
    """
    if server and ":" in server:
        s, p = server.split(":")
        msgr = ManagerMessenger(s, port=p)
    else:
        msgr = ManagerMessenger(server)
    msgr.start()

    if not password:
        password = getpass('Please enter the "manager" password: ')

    check_version_map(vermap)

    msgr.requestAndSaveToken("manager", password)
    try:
        status = msgr.TriggerPopulateDB(vermap)
    except PlomExistingDatabase:
        msgr.closeUser()
        msgr.stop()
        raise

    # grab map and sanity check
    qvmap = msgr.getGlobalQuestionVersionMap()
    if vermap:
        assert qvmap == vermap

    msgr.closeUser()
    msgr.stop()
    return status
