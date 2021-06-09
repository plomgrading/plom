# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2020 Andrew Rechnitzer
# Copyright (C) 2019-2020 Colin B. Macdonald

from collections import defaultdict
from glob import glob
import getpass
import hashlib
import json
import os
import shutil
from pathlib import Path

from plom.messenger import ScanMessenger
from plom.plom_exceptions import PlomExistingLoginException
from plom import PlomImageExts


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


def fileSuccessfulUpload(bundle, shortName, fname, qr=True):
    """After successful upload move file within bundle.

    The image file is moved to 'uploads/sentpages' within the bundle.
    If the qr-flag is set then also move the corresponding .qr file
    Note - tpages will have a qr file, while hwpages and lpages
    do not.
    """
    shutil.move(fname, bundle / Path("uploads/sentPages") / shortName)
    # tpages have a .qr while hwpages and lpages do not.
    if qr:
        shutil.move(
            Path(str(fname) + ".qr"),
            bundle / Path("uploads/sentPages") / (str(shortName) + ".qr"),
        )


def fileFailedUpload(reason, message, bundle, shortName, fname):
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
        shutil.move(fname, bundle / Path("uploads/discardedPages") / shortName)
        shutil.move(
            Path(str(fname) + ".qr"),
            bundle / Path("uploads/discardedPages") / (str(shortName) + ".qr"),
        )
    elif reason == "collision":
        nname = bundle / Path("uploads/collidingPages") / shortName
        shutil.move(fname, nname)
        shutil.move(str(fname) + ".qr", str(nname) + ".qr")
        # and write the name of the colliding file
        with open(str(nname) + ".collide", "w+") as fh:
            json.dump(message, fh)  # this is [collidingFile, test, page, version]
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
        shortName = os.path.split(fname)[1]
        # TODO: very fragile order extraction, check how Andrew does it...
        bundle_order = int(Path(shortName).stem.split("-")[-1])
        if bundle_order in skip_list:
            print(
                "Image {} with bundle_order {} already uploaded. Skipping.".format(
                    fname, bundle_order
                )
            )
            continue

        ts, ps, vs = extractTPV(shortName)
        print("Upload {},{},{} = {} to server".format(ts, ps, vs, shortName))
        md5 = hashlib.md5(open(fname, "rb").read()).hexdigest()
        code = "t{}p{}v{}".format(ts.zfill(4), ps.zfill(2), vs)
        rmsg = msgr.uploadTestPage(
            code,
            int(ts),
            int(ps),
            int(vs),
            shortName,
            fname,
            md5,
            bundle_name,
            bundle_order,
        )
        # rmsg = [True] or [False, reason, message]
        if rmsg[0]:  # was successful upload
            fileSuccessfulUpload(Path("bundles") / bundle_name, shortName, fname)
            TUP[ts].append(ps)
        else:  # was failed upload - reason, message in rmsg[1], rmsg[2]
            fileFailedUpload(
                rmsg[1], rmsg[2], Path("bundles") / bundle_name, shortName, fname
            )
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


def sendHWFiles(msgr, file_list, skip_list, student_id, question, bundle_name):
    """Send the hw-page images of one bundle to the server.

    Args:
        msgr (Messenger): an open authenticated communication mechanism.
        files (list of pathlib.Path): the page images to upload.
        bundle_name (str): the name of the bundle we are sending.
        student_id (int): the id of the student whose hw is being uploaded
        question (list[int]): the question numbers (list of ints) that
            these files are being uploaded to.
        skip_list (list of int): the bundle-orders of pages already in
            the system and so can be skipped.

    Returns:
        defaultdict: TODO document this.

    After each image is uploaded we move it to various places in the
    bundle's "uploads" subdirectory.
    """
    # keep track of which SID uploaded which Q.
    SIDQ = defaultdict(list)
    for fname in file_list:
        print("Upload hw page image {}".format(fname))
        shortName = os.path.split(fname)[1]
        sid, q, n = extractIDQO(shortName)
        bundle_order = n
        if bundle_order in skip_list:
            print(
                "Image {} with bundle_order {} already uploaded. Skipping.".format(
                    fname, bundle_order
                )
            )
            continue

        if sid != student_id:
            raise ValueError(
                "Image {} mismatch in student ID: {} vs {}".format(
                    fname, sid, student_id
                )
            )
        if not (q == "_" or [int(q)] == question):
            raise ValueError(
                "Image {} question supplied {} does not match that in filename {}".format(
                    fname, q, question
                )
            )
        q = question

        print("Upload HW {},{},{} = {} to server".format(sid, q, n, shortName))
        md5 = hashlib.md5(open(fname, "rb").read()).hexdigest()
        rmsg = msgr.uploadHWPage(
            sid, q, n, shortName, fname, md5, bundle_name, bundle_order
        )
        if not rmsg[0]:
            raise RuntimeError(
                "Unsuccessful HW upload, with server returning:\n{}".format(rmsg[1:])
            )
        fileSuccessfulUpload(Path("./"), shortName, fname, qr=False)
        # be careful of workingdir.
        SIDQ[sid].append(q)
    return SIDQ


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
        print("Upload hw page image {}".format(fname))
        shortName = os.path.split(fname)[1]
        sid, n = extractJIDO(shortName)
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
        rmsg = msgr.uploadLPage(
            sid, n, shortName, fname, md5, bundle_name, bundle_order
        )
        if not rmsg[0]:
            raise RuntimeError(
                "Unsuccessful HW upload, with server returning:\n{}".format(rmsg[1:])
            )
        fileSuccessfulUpload(Path("./"), shortName, fname, qr=False)
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

    # get the password if not specified
    if password is None:
        try:
            pwd = getpass.getpass("Please enter the 'scanner' password:")
        except Exception as error:
            print("ERROR", error)
    else:
        pwd = password

    # get started
    try:
        msgr.requestAndSaveToken("scanner", pwd)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another scanner-script running,\n"
            "    e.g., on another computer?\n\n"
            'In order to force-logout the existing authorisation run "plom-scan clear" or "plom-hwscan clear"'
        )
        exit(10)

    if not bundleDir.is_dir():
        raise ValueError("should've been a directory!")

    files = []
    # Look for pages in decodedPages
    for ext in PlomImageExts:
        files.extend(sorted((bundleDir / "decodedPages").glob("t*.{}".format(ext))))
    TUP = sendTestFiles(msgr, bundleDir.name, files, skip_list)
    # we do not automatically replace any missing test-pages, since that is a serious issue for tests, and should be done only by manager.

    updates = msgr.triggerUpdateAfterTUpload()

    # close down messenger
    msgr.closeUser()
    msgr.stop()

    return [TUP, updates]


def uploadHWPages(
    bundle_name, skip_list, student_id, question, server=None, password=None
):
    """Upload the hw pages to the server.

    hwpages uploaded to given student_id and question.
    Skips pages-image with orders in the skip-list (ie the page number within the bundle.pdf)

    Bundle must already be created.  We will upload the
    files and then send a 'please trigger an update' message to the server.
    """

    if server and ":" in server:
        s, p = server.split(":")
        msgr = ScanMessenger(s, port=p)
    else:
        msgr = ScanMessenger(server)
    msgr.start()

    # get the password if not specified
    if password is None:
        try:
            pwd = getpass.getpass("Please enter the 'scanner' password:")
        except Exception as error:
            print("ERROR", error)
    else:
        pwd = password

    # get started
    try:
        msgr.requestAndSaveToken("scanner", pwd)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another scanner-script running,\n"
            "    e.g., on another computer?\n\n"
            'In order to force-logout the existing authorisation run "plom-hwscan clear"'
        )
        exit(10)

    file_list = []
    # files are sitting in "bundles/submittedHWByQ/<bundle_name>"
    os.chdir(os.path.join("bundles", "submittedHWByQ", bundle_name))
    # Look for pages in pageImages
    for ext in PlomImageExts:
        file_list.extend(sorted(glob(os.path.join("pageImages", "*.{}".format(ext)))))

    HWUP = sendHWFiles(msgr, file_list, skip_list, student_id, question, bundle_name)

    updates = msgr.triggerUpdateAfterHWUpload()

    # go back to original dir
    os.chdir("..")
    os.chdir("..")
    os.chdir("..")

    # close down messenger
    msgr.closeUser()
    msgr.stop()

    return [HWUP, updates]


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

    # get the password if not specified
    if password is None:
        try:
            pwd = getpass.getpass("Please enter the 'scanner' password:")
        except Exception as error:
            print("ERROR", error)
    else:
        pwd = password

    # get started
    try:
        msgr.requestAndSaveToken("scanner", pwd)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another scanner-script running,\n"
            "    e.g., on another computer?\n\n"
            'In order to force-logout the existing authorisation run "plom-hwscan clear"'
        )
        exit(10)

    file_list = []
    # files are sitting in "bundles/submittedLoose/<bundle_name>"
    os.chdir(os.path.join("bundles", "submittedLoose", bundle_name))
    # Look for pages in pageImages
    for ext in PlomImageExts:
        file_list.extend(sorted(glob(os.path.join("pageImages", "*.{}".format(ext)))))

    LUP = sendLFiles(msgr, file_list, skip_list, student_id, bundle_name)

    updates = msgr.triggerUpdateAfterLUpload()

    # go back to original dir
    os.chdir("..")
    os.chdir("..")
    os.chdir("..")

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

    # get the password if not specified
    if password is None:
        try:
            pwd = getpass.getpass("Please enter the 'scanner' password:")
        except Exception as error:
            print("ERROR", error)
    else:
        pwd = password

    # get started
    try:
        msgr.requestAndSaveToken("scanner", pwd)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another scanner-script running,\n"
            "    e.g., on another computer?\n\n"
            'In order to force-logout the existing authorisation run "plom-scan clear"'
        )
        exit(10)

    # get test_number from SID.
    # response is [true, test_number] or [false, reason]
    test_success = msgr.sidToTest(student_id)

    msgr.closeUser()
    msgr.stop()

    if test_success[0]:  # found it
        return test_success[1]  # return the number
    else:  # couldn't find it
        return None


def bundle_name_from_filename(filename):
    """Return the bundle name for a file.

    Args:
        filename (str, Path): name of file, typically a PDF file.

    Returns
        str: Currently bundle name is the stem of the file name with
            some input sanitizing such as spaces replaced with underscores.
    """
    filename = Path(filename)
    return filename.stem.replace(" ", "_")


def bundle_name_and_md5(filename):
    """Return the bundle name and md5sum checksum for a file.

    Args:
        filename (str, Path): name of file.

    Returns
        tuple: (str, str) for bundle_name and md5sum.

    Exceptions:
        FileNotFoundError: file does not exist.
    """
    filename = Path(filename)
    if not filename.is_file():
        raise FileNotFoundError("not found or not a file/symlink")
    bundle_name = bundle_name_from_filename(filename)
    md5 = hashlib.md5(open(filename, "rb").read()).hexdigest()
    return (bundle_name, md5)


def doesBundleExist(bundle_file, server=None, password=None):
    """Check if bundle exists and is so does its md5sum match a given file.

    Args:
        bundle_file (str, Path): needs to be the actual file not the
            bundle name because we need to compute the md5sum.

    Returns:
        list: the pair `[True, bundle_name]` where `bundle_name` is a
            `str` or `[False, reason]` where `reason` is a `str`.
    """
    if server and ":" in server:
        s, p = server.split(":")
        msgr = ScanMessenger(s, port=p)
    else:
        msgr = ScanMessenger(server)
    msgr.start()

    # get the password if not specified
    if password is None:
        pwd = getpass.getpass("Please enter the 'scanner' password:")
    else:
        pwd = password

    # get started
    try:
        msgr.requestAndSaveToken("scanner", pwd)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another scanner-script running,\n"
            "    e.g., on another computer?\n\n"
            'In order to force-logout the existing authorisation run "plom-scan clear"'
        )
        exit(10)

    bundle_name, md5 = bundle_name_and_md5(bundle_file)
    bundle_success = msgr.doesBundleExist(bundle_name, md5)

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

    if password is None:
        pwd = getpass.getpass("Please enter the 'scanner' password: ")
    else:
        pwd = password

    try:
        msgr.requestAndSaveToken("scanner", pwd)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another scanner-script running,\n"
            "    e.g., on another computer?\n\n"
            'In order to force-logout the existing authorisation run "plom-scan clear"'
        )
        exit(10)

    try:
        bundle_success = msgr.createNewBundle(bundle_name, md5)
    finally:
        msgr.closeUser()
        msgr.stop()

    return bundle_success
