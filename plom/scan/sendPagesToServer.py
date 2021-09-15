# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2020 Andrew Rechnitzer
# Copyright (C) 2019-2021 Colin B. Macdonald

from collections import defaultdict
from glob import glob
import hashlib
import json
import os
import shutil
from pathlib import Path

from plom.messenger import ScanMessenger
from plom.misc_utils import working_directory
from plom.plom_exceptions import PlomExistingLoginException
from plom import PlomImageExts


def extract_order(filename):
    """From filename of form 'blah-n.png' extract 'n' and return as an int"""
    return int(Path(filename).stem.split("-")[-1])


def extractTPV(name):
    """Get test, page, version from name.

    A name in 'standard form' for a test-page should be
    of the form 'tXXXXpYYvZ.blah'. Asserts will fail
    if name is not of this form.

    Return a triple of str (XXXX, YY, Z) .
    """

    # TODO - replace this with something less cludgy.
    # should be tXXXXpYYvZ.blah
    assert name[0] == "t"
    k = 1
    ts = ""
    while name[k].isnumeric():
        ts += name[k]
        k += 1

    assert name[k] == "p"
    k += 1
    ps = ""
    while name[k].isnumeric():
        ps += name[k]
        k += 1

    assert name[k] == "v"
    k += 1
    vs = ""
    while name[k].isnumeric():
        vs += name[k]
        k += 1
    return (ts, ps, vs)


def move_files_post_upload(bundle, f, qr=True):
    """After successful upload move file within bundle.

    The image file is moved to 'uploads/sentpages' within the bundle.
    If the qr-flag is set then also move the corresponding .qr file

    args:
        bundle (pathlib.Path): the "base" bundle directory.
        f (pathlib.Path): a filename, possibly with a path.
        qr (bool): There should also be a file same as `f` but
            with a ".qr" appended.  Move it too.  Note that TPages
            will have a qr file, while HWPages and LPages do not.
    """
    shutil.move(f, bundle / "uploads/sentPages" / f.name)
    if qr:
        shutil.move(Path(str(f) + ".qr"), bundle / "uploads/sentPages" / f"{f.name}.qr")


def fileFailedUpload(reason, message, bundle, f):
    """Move image after failed upload.

    Upload can fail for 'good' and 'bad' reasons. The image is moved
    accordingly.
    Good reasons - you are trying to upload to a page that already exists in the system.
     * 'duplicate' - the image is duplicate of image in system (by md5sum)
     so move into 'uploads/discardedPages'
     * 'collision' - the image collides with another test-page already uploaded (eg - there is already a scan of test 7 page 2 in the database). Move the image to 'uploads/collidingPages'

    Bad reasons - these should not happen - means you are trying to upload to tests/pages which the system does not know about.
     * testError - the database has no record of the test which you were trying to upload to.
     * pageError - the database has no record of the tpage (of that test) which you were trying to upload to.
    """
    print("Failed upload = {}, {}".format(reason, message))
    if reason == "duplicate":
        to = bundle / "uploads/discardedPages"
        shutil.move(f, to / f.name)
        shutil.move(Path(str(f) + ".qr"), to / f"{f.name}.qr")
    elif reason == "collision":
        to = bundle / "uploads/collidingPages"
        shutil.move(f, to / f.name)
        shutil.move(Path(str(f) + ".qr"), to / f"{f.name}.qr")
        # write stuff into a file: [collidingFile, test, page, version]
        with open(to / f"{f.name}.collide", "w") as fh:
            json.dump(message, fh)
    else:  # now bad errors
        print("Image upload failed for *bad* reason - this should not happen.")
        print("Reason = {}".format(reason))
        print("Message = {}".format(message))


def sendTestFiles(msgr, bundle_name, files, skip_list):
    """Send the test-page images of one bundle to the server.

    Args:
        msgr (Messenger): an open authenticated communication mechanism.
        bundle_name (str): the name of the bundle we are sending.
        files (list of pathlib.Path): the page images to upload.
        skip_list (list of int): the bundle-orders of pages already in
            the system and so can be skipped.

    Returns:
        defaultdict: TODO document this.

    After each image is uploaded we move it to various places in the
    bundle's "uploads" subdirectory.
    """
    TUP = defaultdict(list)
    for fname in files:
        fname = Path(fname)
        bundle_order = extract_order(fname)
        if bundle_order in skip_list:
            print(
                "Image {} with bundle_order {} already uploaded. Skipping.".format(
                    fname, bundle_order
                )
            )
            continue

        ts, ps, vs = extractTPV(fname.name)
        print("Upload {},{},{} = {} to server".format(ts, ps, vs, fname.name))
        md5 = hashlib.md5(open(fname, "rb").read()).hexdigest()
        code = "t{}p{}v{}".format(ts.zfill(4), ps.zfill(2), vs)
        rmsg = msgr.uploadTestPage(
            code,
            int(ts),
            int(ps),
            int(vs),
            fname,
            md5,
            bundle_name,
            bundle_order,
        )
        # rmsg = [True] or [False, reason, message]
        if rmsg[0]:  # was successful upload
            move_files_post_upload(Path("bundles") / bundle_name, fname)
            TUP[ts].append(ps)
        else:  # was failed upload - reason, message in rmsg[1], rmsg[2]
            fileFailedUpload(rmsg[1], rmsg[2], Path("bundles") / bundle_name, fname)
    return TUP


def extractIDQO(fileName):  # get ID, Question and Order
    """Expecting filename of the form blah.SID.Q-N.ext - return SID Q and N.

    `ext` is something like `png`.
    """
    splut = fileName.split(".")  # easy to get SID, and Q
    sid = splut[-3]
    # split again, now on "-" to separate Q and N
    resplut = splut[-2].split("-")
    q = resplut[0]
    n = int(resplut[1])

    return (sid, q, n)


def extractJIDO(fileName):  # get just ID, Order
    """Expecting filename of the form blah.SID-N.ext - return SID and N.

    `ext` is something like `png`.
    """
    splut = fileName.split(".")  # easy to get SID-N
    # split again, now on "-" to separate SID and N
    resplut = splut[-2].split("-")
    sid = int(resplut[0])
    n = int(resplut[1])

    return (sid, n)


def sendLFiles(msgr, fileList, skip_list, student_id, bundle_name):
    """Send the hw-page images of one bundle to the server.

    Args:
        msgr (Messenger): an open authenticated communication mechanism.
        files (list of pathlib.Path): the page images to upload.
        bundle_name (str): the name of the bundle we are sending.
        student_id (int): the id of the student whose hw is being uploaded
        question (int): the question being uploaded
        skip_list (list of int): the bundle-orders of pages already in
            the system and so can be skipped.

    Returns:
        defaultdict: TODO document this.

    After each image is uploaded we move it to various places in the
    bundle's "uploads" subdirectory.
    """
    # keep track of which SID uploaded.
    JSID = {}
    for fname in fileList:
        fname = Path(fname)
        print(f'Upload "Loose" page image {fname}')
        sid, n = extractJIDO(fname.name)
        bundle_order = n
        if bundle_order in skip_list:
            print(
                "Image {} with bundle_order {} already uploaded. Skipping.".format(
                    fname, bundle_order
                )
            )
            continue
        if str(sid) != str(student_id):  # careful with type casting
            print("Problem with file {} - skipping".format(fname))
            continue

        md5 = hashlib.md5(open(fname, "rb").read()).hexdigest()
        rmsg = msgr.uploadLPage(sid, n, fname, md5, bundle_name, bundle_order)
        if not rmsg[0]:
            raise RuntimeError(
                "Unsuccessful Loose upload, with server returning:\n{}".format(rmsg[1:])
            )
        move_files_post_upload(Path("./"), fname, qr=False)
        # be careful of workingdir.
        JSID[sid] = True
    return JSID


def uploadTPages(bundleDir, skip_list, server=None, password=None):
    """Upload the test pages to the server.

    Skips pages-image with orders in the skip-list (i.e., the page
    number within the bundle.pdf)

    Bundle must already be created.  We will upload the
    files and then send a 'please trigger an update' message to the server.
    """
    if server and ":" in server:
        s, p = server.split(":")
        msgr = ScanMessenger(s, port=p)
    else:
        msgr = ScanMessenger(server)
    msgr.start()

    try:
        msgr.requestAndSaveToken("scanner", password)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another scanner-script running,\n"
            "    e.g., on another computer?\n\n"
            'In order to force-logout the existing authorisation run "plom-scan clear" or "plom-hwscan clear"'
        )
        raise

    if not bundleDir.is_dir():
        raise ValueError("should've been a directory!")

    try:
        files = []
        # Look for pages in decodedPages
        for ext in PlomImageExts:
            files.extend(sorted((bundleDir / "decodedPages").glob("t*.{}".format(ext))))
        TUP = sendTestFiles(msgr, bundleDir.name, files, skip_list)
        # we do not automatically replace any missing test-pages, since that is a serious issue for tests, and should be done only by manager.

        updates = msgr.triggerUpdateAfterTUpload()
    finally:
        msgr.closeUser()
        msgr.stop()
    return [TUP, updates]


def upload_HW_pages(file_list, bundle_name, bundledir, sid, server=None, password=None):
    """Upload "homework" pages to a particular student ID on the server.

    args:
        file_list (list): each row is `[n, f, q]` where `n` is the page
            number in the bundle, `f` is the filename, and `q` is a list
            of questions to which this upload should be attached.
        bundle_name (str)
        sid (str): student ID number.
        server (str/None)
        password (str/None)

    Bundle must already be created.  We will upload the files and then
    send a 'please trigger an update' message to the server.
    """
    if server and ":" in server:
        s, p = server.split(":")
        msgr = ScanMessenger(s, port=p)
    else:
        msgr = ScanMessenger(server)
    msgr.start()

    try:
        msgr.requestAndSaveToken("scanner", password)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another scanner-script running,\n"
            "    e.g., on another computer?\n\n"
            'In order to force-logout the existing authorisation run "plom-hwscan clear"'
        )
        raise

    try:
        SIDQ = defaultdict(list)
        for n, f, q in file_list:
            md5 = hashlib.md5(open(f, "rb").read()).hexdigest()
            rmsg = msgr.uploadHWPage(sid, q, n, f, md5, bundle_name, n)
            if not rmsg[0]:
                raise RuntimeError(
                    f"Unsuccessful HW upload, server returned:\n{rmsg[1:]}"
                )
            SIDQ[sid].append(q)
            # TODO: this feels out a bit out of place?
            move_files_post_upload(bundledir, f, qr=False)

        updates = msgr.triggerUpdateAfterHWUpload()
    finally:
        msgr.closeUser()
        msgr.stop()
    return (SIDQ, updates)


def uploadLPages(bundle_name, skip_list, student_id, server=None, password=None):
    """Upload the hw pages to the server.

    lpages uploaded to given student_id.
    Skips pages-image with orders in the skip-list (i.e., the page
    number within the bundle.pdf)

    Bundle must already be created.  We will upload the
    files and then send a 'please trigger an update' message to the server.
    """
    if server and ":" in server:
        s, p = server.split(":")
        msgr = ScanMessenger(s, port=p)
    else:
        msgr = ScanMessenger(server)
    msgr.start()

    try:
        msgr.requestAndSaveToken("scanner", password)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another scanner-script running,\n"
            "    e.g., on another computer?\n\n"
            'In order to force-logout the existing authorisation run "plom-hwscan clear"'
        )
        raise

    file_list = []
    # files are sitting in "bundles/submittedLoose/<bundle_name>"
    with working_directory(os.path.join("bundles", "submittedLoose", bundle_name)):
        # Look for pages in pageImages
        for ext in PlomImageExts:
            file_list.extend(
                sorted(glob(os.path.join("pageImages", "*.{}".format(ext))))
            )

        LUP = sendLFiles(msgr, file_list, skip_list, student_id, bundle_name)

        updates = msgr.triggerUpdateAfterLUpload()

        # go back to original dir
    # close down messenger
    msgr.closeUser()
    msgr.stop()

    return [LUP, updates]


def checkTestHasThatSID(student_id, server=None, password=None):
    """Get test-number corresponding to given student id

    For HW tests should be pre-IDd, so this function is used
    to map a student-id to the underlying test. This means that
    and uploaded HW page can be matched to the test in the database.

    Returns the test-number if the SID is matched to a test in the database
    else returns None.
    """
    if server and ":" in server:
        s, p = server.split(":")
        msgr = ScanMessenger(s, port=p)
    else:
        msgr = ScanMessenger(server)
    msgr.start()

    try:
        msgr.requestAndSaveToken("scanner", password)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another scanner-script running,\n"
            "    e.g., on another computer?\n\n"
            'In order to force-logout the existing authorisation run "plom-scan clear"'
        )
        raise

    # get test_number from SID.
    # response is [true, test_number] or [false, reason]
    test_success = msgr.sidToTest(student_id)

    msgr.closeUser()
    msgr.stop()

    if test_success[0]:  # found it
        return test_success[1]  # return the number
    else:  # couldn't find it
        return None


def does_bundle_exist_on_server(bundle_name, md5sum, server=None, password=None):
    """Check if bundle exists by name and/or md5sum.

    Args:
        bundle_name (str): not the file, just the bundle name (often but
            not always the filename).
        md5sum (str): the md5sum of the bundle

    Returns:
        list: `[False, None]` if it does not exist in any way.  Otherwise
            the pair `[True, reason]` where `reason` is "name", "md5sum",
            or "both".
    """
    if server and ":" in server:
        s, p = server.split(":")
        msgr = ScanMessenger(s, port=p)
    else:
        msgr = ScanMessenger(server)
    msgr.start()

    try:
        msgr.requestAndSaveToken("scanner", password)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another scanner-script running,\n"
            "    e.g., on another computer?\n\n"
            'In order to force-logout the existing authorisation run "plom-scan clear"'
        )
        raise

    try:
        bundle_success = msgr.doesBundleExist(bundle_name, md5sum)
    finally:
        msgr.closeUser()
        msgr.stop()
    return bundle_success


def createNewBundle(bundle_name, md5, server=None, password=None):
    """Create a new bundle with a given name.

    Args:
        bundle_name (str): a bundle name, typically extracted from the
            name of a PDF file.
        md5 (str): the md5sum of the file from which this bundle is
            extracted.  In future, could be extended to a list/dict for
            more than one file.
        server: information to contact a server.
        password: information to contact a server.

    Returns:
        list: either the pair `[True, bundle_name]` or `[False]`.
    """
    if server and ":" in server:
        s, p = server.split(":")
        msgr = ScanMessenger(s, port=p)
    else:
        msgr = ScanMessenger(server)
    msgr.start()

    try:
        msgr.requestAndSaveToken("scanner", password)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another scanner-script running,\n"
            "    e.g., on another computer?\n\n"
            'In order to force-logout the existing authorisation run "plom-scan clear"'
        )
        raise

    try:
        bundle_success = msgr.createNewBundle(bundle_name, md5)
    finally:
        msgr.closeUser()
        msgr.stop()

    return bundle_success
