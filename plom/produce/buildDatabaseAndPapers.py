# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2021 Colin B. Macdonald
# Copyright (C) 2021 Peter Lee

from pathlib import Path

from plom import check_version_map
from plom.misc_utils import working_directory
from plom.produce.buildNamedPDF import build_papers_backend
from plom.produce.buildNamedPDF import check_pdf_and_id_if_needed
from plom.produce import paperdir as paperdir_name
from plom.messenger import ManagerMessenger
from plom.plom_exceptions import PlomExistingDatabase


def build_papers(
    server=None,
    password=None,
    *,
    basedir=Path("."),
    fakepdf=False,
    no_qr=False,
    indexToMake=None,
    ycoord=None,
):
    """Build the blank papers using version information from server and source PDFs.

    Args:
        server (str): server name and optionally port.
        password (str): the manager password.

    Keyword Args:
        basedir (pathlib.Path/str): Look for the source version PDF files
            in `basedir/sourceVersions`.  Produce the printable PDF files
            in `basedir/papersToPrint`.
        fakepdf (bool): when true, the build empty pdfs (actually empty files)
            for use when students upload homework or similar (and only 1 version).
        no_qr (bool): when True, don't stamp with QR codes.  Default: False
            (which means *do* stamp with QR codes).
        indexToMake (int/None): prepare a particular paper, or None to make
            all papers.
        ycoord (float/None): tweak the y-coordinate of the stamped name/id
            box for prenamed papers.  None for a default value.
    """
    if server and ":" in server:
        s, p = server.split(":")
        msgr = ManagerMessenger(s, port=p)
    else:
        msgr = ManagerMessenger(server)
    msgr.start()

    msgr.requestAndSaveToken("manager", password)

    basedir = Path(basedir)
    paperdir = basedir / paperdir_name
    paperdir.mkdir(exist_ok=True)

    try:
        spec = msgr.get_spec()
        pvmap = msgr.getGlobalPageVersionMap()
        if spec["numberToName"] > 0:
            _classlist = msgr.IDrequestClasslist()
            # TODO: Issue #1646 mostly student number (w fallback)
            # TODO: but careful about identify_prenamed below which may need id
            classlist = [(x["id"], x["studentName"]) for x in _classlist]
            # Do sanity check on length of classlist
            if len(classlist) < spec["numberToName"]:
                raise ValueError(
                    "Classlist is too short for {} pre-named papers".format(
                        spec["numberToName"]
                    )
                )
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
        if indexToMake:
            if (indexToMake < 1) or (indexToMake > spec["numberToProduce"]):
                raise ValueError(
                    f"Index out of range. Must be in range [1,{ spec['numberToProduce']}]"
                )
            if indexToMake <= spec["numberToName"]:
                print(f"Building only specific paper {indexToMake} (prenamed)")
            else:
                print(f"Building only specific paper {indexToMake} (blank)")
        with working_directory(basedir):
            build_papers_backend(
                spec,
                pvmap,
                classlist,
                fakepdf=fakepdf,
                no_qr=no_qr,
                indexToMake=indexToMake,
                ycoord=ycoord,
            )

        print(
            "Checking papers produced and ID-ing any pre-named papers into the database"
        )
        check_pdf_and_id_if_needed(
            spec, msgr, classlist, paperdir=paperdir, indexToCheck=indexToMake
        )
    finally:
        msgr.closeUser()
        msgr.stop()


def build_database(server=None, password=None, vermap={}):
    """Build the database from a pre-set version map.

    args:
        server (str): server name and optionally port.
        password (str): the manager password.
        vermap (dict): question version map.  If empty dict, server will
            make its own mapping.  For the map format see
            :func:`plom.finish.make_random_version_map`.

    return:
        str: long multiline string of all the version DB entries.
    """
    if server and ":" in server:
        s, p = server.split(":")
        msgr = ManagerMessenger(s, port=p)
    else:
        msgr = ManagerMessenger(server)
    msgr.start()

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
