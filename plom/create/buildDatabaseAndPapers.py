# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2021-2022 Colin B. Macdonald
# Copyright (C) 2021 Peter Lee

from pathlib import Path

from plom import check_version_map
from plom.misc_utils import working_directory
from plom.create.buildNamedPDF import build_papers_backend
from plom.create.buildNamedPDF import check_pdf_and_id_if_needed
from plom.create import paperdir as paperdir_name
from plom.create import with_manager_messenger


@with_manager_messenger
def build_papers(
    *,
    basedir=Path("."),
    fakepdf=False,
    no_qr=False,
    indexToMake=None,
    xcoord=None,
    ycoord=None,
    msgr=None,
):
    """Build the blank papers using version information from server and source PDFs.

    Keyword Args:
        msgr (plom.Messenger/tuple): either a connected Messenger or a
            tuple appropriate for credientials.
        basedir (pathlib.Path/str): Look for the source version PDF files
            in `basedir/sourceVersions`.  Produce the printable PDF files
            in `basedir/papersToPrint`.
        fakepdf (bool): when true, the build empty pdfs (actually empty files)
            for use when students upload homework or similar (and only 1 version).
        no_qr (bool): when True, don't stamp with QR codes.  Default: False
            (which means *do* stamp with QR codes).
        indexToMake (int/None): prepare a particular paper, or None to make
            all papers.
        xcoord (float/None): tweak the x-coordinate of the stamped name/id
            box for prenamed papers.  None for a default value.
        ycoord (float/None): tweak the y-coordinate of the stamped name/id
            box for prenamed papers.  None for a default value.

    Raises:
        PlomConflict: server does not yet have a version map database, say
            b/c build_database has not yet been called.
    """
    basedir = Path(basedir)
    paperdir = basedir / paperdir_name
    paperdir.mkdir(exist_ok=True)

    # TODO: temporarily avoid changing indent
    if True:
        spec = msgr.get_spec()
        pvmap = msgr.getGlobalPageVersionMap()
        qvmap = msgr.getGlobalQuestionVersionMap()
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
                qvmap,
                classlist,
                fakepdf=fakepdf,
                no_qr=no_qr,
                indexToMake=indexToMake,
                xcoord=xcoord,
                ycoord=ycoord,
            )

        print(
            "Checking papers produced and ID-ing any pre-named papers into the database"
        )
        check_pdf_and_id_if_needed(
            spec, msgr, classlist, paperdir=paperdir, indexToCheck=indexToMake
        )


@with_manager_messenger
def build_database(*, msgr, vermap={}):
    """Build the database from a pre-set version map.

    Keyword Args:
        msgr (plom.Messenger/tuple): either a connected Messenger or a
            tuple appropriate for credientials.
        vermap (dict): question version map.  If empty dict, server will
            make its own mapping.  For the map format see
            :func:`plom.finish.make_random_version_map`.

    return:
        str: long multiline string of all the version DB entries.

    raises:
        PlomExistingDatabase
        PlomServerNotReady
    """
    check_version_map(vermap)

    status = msgr.TriggerPopulateDB(vermap)
    # sanity check the version map
    qvmap = msgr.getGlobalQuestionVersionMap()
    if vermap:
        assert qvmap == vermap, RuntimeError("Report a bug in version_map code!")
    return status
