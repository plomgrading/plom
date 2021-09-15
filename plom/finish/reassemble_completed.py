# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2018-2021 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe

from multiprocessing import Pool
import os
from pathlib import Path
import shutil
import tempfile

from tqdm import tqdm

from plom import get_question_label
from plom.messenger import FinishMessenger
from plom.plom_exceptions import PlomExistingLoginException
from plom.finish.coverPageBuilder import makeCover
from plom.finish.examReassembler import reassemble


def _parfcn(z):
    """Parallel function used below, must be defined in root of module.

    Args:
        z (tuple): Arguments to reassemble and makeCover.
    """
    x, y = z
    if x and y:
        makeCover(*x)
        reassemble(*y)


def build_cover_page_data(msgr, tmpdir, t, maxMarks):
    """Builds the information used to create cover pages.

    Args:
        msgr (FinishMessenger): Messenger object that talks to the server.
        t (int): Test number.
        maxMarks (dict): Maxmarks per question str -> int.

    Returns:
        tuple: (testnumber, sname, sid, tab) where `tab` is a table with
            rows `[q_label, ver, mark, max_mark]`.
    """
    # should be [ [sid, sname], [q,v,m], [q,v,m] etc]
    cpi = msgr.RgetCoverPageInfo(t)
    spec = msgr.get_spec()
    sid = cpi[0][0]
    sname = cpi[0][1]
    # for each Q [q, v, mark, maxPossibleMark]
    arg = []
    for qvm in cpi[1:]:
        question_label = get_question_label(spec, qvm[0])
        arg.append([question_label, qvm[1], qvm[2], maxMarks[str(qvm[0])]])
    testnumstr = str(t).zfill(4)
    covername = tmpdir / "cover_{}.pdf".format(testnumstr)
    return (int(t), sname, sid, arg, covername)


def download_page_images(msgr, tmpdir, outdir, short_name, num_questions, t, sid):
    """Builds the information for reassembling the entire test.

    Args:
        msgr (FinishMessenger): Messenger object that talks to the server.
        tmpdir (pathlib.Path): directory to save the temp images.
        outdir (pathlib.Path): directory for the reassembled papers.
        short_name (str): name of the test without the student id.
        num_questions (int): number of questions.
        t (str/int): Test number.
        sid (str): student number.

    Returns:
       tuple : (outname, short_name, sid, covername, page_filenames)
    """
    id_image_blobs = msgr.request_ID_images(t)
    id_pages = []
    for i, obj in enumerate(id_image_blobs):
        filename = tmpdir / f"img_{int(t):04}_id{i:02}.png"
        id_pages.append(filename)
        with open(filename, "wb") as f:
            f.write(obj)
    marked_pages = []
    for q in range(1, num_questions + 1):
        obj = msgr.get_annotations_image(t, q)
        # Hardcoded to PNG here (and elsewhere!)
        filename = tmpdir / f"img_{int(t):04}_q{q:02}.png"
        marked_pages.append(filename)
        with open(filename, "wb") as f:
            f.write(obj)
    dnm_image_blobs = msgr.request_donotmark_images(t)
    dnm_pages = []
    for i, obj in enumerate(dnm_image_blobs):
        filename = tmpdir / f"img_{int(t):04}_dnm{i:02}.png"
        dnm_pages.append(filename)
        with open(filename, "wb") as f:
            f.write(obj)
    testnumstr = str(t).zfill(4)
    covername = tmpdir / "cover_{}.pdf".format(testnumstr)
    outname = outdir / f"{short_name}_{sid}.pdf"
    return (outname, short_name, sid, covername, id_pages, marked_pages, dnm_pages)


def main(server=None, pwd=None):
    if server and ":" in server:
        s, p = server.split(":")
        msgr = FinishMessenger(s, port=p)
    else:
        msgr = FinishMessenger(server)
    msgr.start()

    try:
        msgr.requestAndSaveToken("manager", pwd)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another finishing-script or manager-client running,\n"
            "    e.g., on another computer?\n\n"
            "In order to force-logout the existing authorisation run `plom-finish clear`."
        )
        raise

    try:
        shortName = msgr.getInfoShortName()
        spec = msgr.get_spec()
        num_questions = spec["numberOfQuestions"]

        outdir = Path("reassembled")
        outdir.mkdir(exist_ok=True)
        tmpdir = Path(tempfile.mkdtemp(prefix="tmp_images_", dir=os.getcwd()))
        print(f"Downloading to temp directory {tmpdir}")

        completedTests = msgr.RgetCompletionStatus()
        # dict key = testnumber, then list id'd, tot'd, #q's marked
        identifiedTests = msgr.RgetIdentified()
        # dict key = testNumber, then pairs [sid, sname]
        maxMarks = msgr.MgetAllMax()

        # get data for cover pages and reassembly
        pagelists = []
        coverpagelist = []

        for t in completedTests:
            if completedTests[t][0] == True and completedTests[t][1] == num_questions:
                if identifiedTests[t][0] is not None:
                    dat1 = build_cover_page_data(msgr, tmpdir, t, maxMarks)
                    dat2 = download_page_images(
                        msgr,
                        tmpdir,
                        outdir,
                        shortName,
                        num_questions,
                        t,
                        identifiedTests[t][0],
                    )
                    coverpagelist.append(dat1)
                    pagelists.append(dat2)
                else:
                    print(">>WARNING<< Test {} has no ID".format(t))
    finally:
        msgr.closeUser()
        msgr.stop()

    N = len(coverpagelist)
    print("Reassembling {} papers...".format(N))
    with Pool() as p:
        r = list(
            tqdm(
                p.imap_unordered(_parfcn, list(zip(coverpagelist, pagelists))), total=N
            )
        )
    # Serial
    # for z in zip(coverpagelist, pagelists):
    #    _parfcn(z)
    shutil.rmtree(tmpdir)


if __name__ == "__main__":
    main()
