# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Andrew Rechnitzer
import getpass
import os
from pathlib import Path
from PIL import Image
import shutil
import tempfile
import toml

from plom.messenger import ManagerMessenger
from plom.plom_exceptions import PlomExistingLoginException
from plom.scan.scansToImages import processFileToBitmaps

source_path = Path("sourceVersions")
solution_path = Path("solutionImages")


def getSpec(server, password):
    if server and ":" in server:
        s, p = server.split(":")
        msgr = ManagerMessenger(s, port=p)
    else:
        msgr = ManagerMessenger(server)
    msgr.start()

    # get the password if not specified
    if password is None:
        try:
            pwd = getpass.getpass("Please enter the 'manager' password:")
        except Exception as error:
            print("ERROR", error)
            exit(1)
    else:
        pwd = password

    try:
        msgr.requestAndSaveToken("manager", pwd)
    except PlomExistingLoginException as e:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another script running,\n"
            "    e.g., on another computer?\n\n"
            'In order to force-logout the existing authorisation run "plom-solution clear"'
        )
        raise

    try:
        spec = msgr.get_spec()
    finally:
        msgr.closeUser()
        msgr.stop()

    return spec


def check_solution_files_present(numberOfVersions):
    print(f"Looking for solution files in directory '{source_path}'")
    for v in range(1, numberOfVersions + 1):
        filename = source_path / f"solutions{v}.pdf"
        print(f"Checking file {filename}")
        if not filename.is_file():
            return (False, f"Missing solution for version {v}")
    return (True, "All solution files present")


def glueImages(image_list, destination):
    # https://stackoverflow.com/questions/30227466/combine-several-images-horizontally-with-python
    images = [Image.open(img) for img in image_list]
    widths, heights = zip(*(img.size for img in images))
    total_width = sum(widths)
    max_height = max(heights)
    new_image = Image.new("RGB", (total_width, max_height))
    x_offset = 0
    for img in images:
        new_image.paste(img, (x_offset, 0))
        x_offset += img.size[0]

    new_image.save(destination)


def createSolutionSpec(testSpec):
    soln = {}
    soln["numberOfVersions"] = testSpec["numberOfVersions"]
    soln["numberOfPages"] = testSpec["numberOfPages"]
    soln["numberOfQuestions"] = testSpec["numberOfQuestions"]
    soln["solutionPages"] = {}
    for q in range(1, testSpec["numberOfQuestions"] + 1):
        soln["solutionPages"][str(q)] = testSpec["question"][str(q)]["pages"]
    return soln


def saveSolutionSpec(solutionSpec):
    with open("solutionSpec.toml", "w") as fh:
        toml.dump(solutionSpec, fh)


def loadSolutionSpec(spec_filename):
    with open(spec_filename, "r") as fh:
        solutionSpec = toml.dump(spec_filename, fh)
    return solutionSpec


def isPositiveInt(s):
    try:
        n = int(s)
        if n > 0:
            return True
        else:
            return False
    except ValueError:
        return False


def isContiguousListPosInt(l, lastPage):
    # check it is a list
    if type(l) is not list:
        return False
    # check each entry is 0<n<=lastPage
    for n in l:
        if not isPositiveInt(n):
            return False
        if n > lastPage:
            return False
    # check it is contiguous
    sl = set(l)
    for n in range(min(sl), max(sl) + 1):
        if n not in sl:
            return False
    # all tests passed
    return True


def checkSolutionSpec(testSpec, solutionSpec):
    print("Checking = ", solutionSpec)
    # make sure keys are present
    for x in [
        "numberOfVersions",
        "numberOfPages",
        "numberOfQuestions",
        "solutionPages",
    ]:
        if x not in solutionSpec:
            return (False, f"Missing key = {x}")
    # check Q/V values match test-spec
    for x in ["numberOfVersions", "numberOfQuestions"]:
        if solutionSpec[x] != testSpec[x]:
            return (False, f"Value of {x} does not match test spec")
    # check pages is pos-int
    if isPositiveInt(solutionSpec["numberOfPages"]) is False:
        return (False, f"numberOfPages must be a positive integer.")

    # make sure right number of question-keys - match test-spec
    if len(solutionSpec["solutionPages"]) != solutionSpec["numberOfQuestions"]:
        return (
            False,
            f"Question keys incorrect = {list(solutionSpec['solutionPages'].keys() )}",
        )
    # make sure each pagelist is contiguous an in range
    for q in range(1, solutionSpec["numberOfQuestions"] + 1):
        if str(q) not in solutionSpec["solutionPages"]:
            return (
                False,
                f"Question keys incorrect = {list(solutionSpec['solutionPages'].keys() )}",
            )
        if (
            isContiguousListPosInt(
                solutionSpec["solutionPages"][str(q)], solutionSpec["numberOfPages"]
            )
            is False
        ):
            return (
                False,
                f"Pages for solution {q} are not a contiguous list in of positive integers between 1 and {solutionSpec['numberOfPages']}",
            )
    return (True, "All ok")


def extractSolutionImages(server, password, solution_spec_filename=None):
    testSpec = getSpec(server, password)

    if solution_spec_filename is None:
        solutionSpec = createSolutionSpec(testSpec)
        saveSolutionSpec(solutionSpec)
    elif Path(solution_spec_filename).is_file() is False:
        print(f"Cannot find file {solution_spec_filename}")
        return False
    else:
        solutionSpec = loadSolutionSpec(solution_spec_filename)

    valid, msg = checkSolutionSpec(testSpec, solutionSpec)
    if valid:
        print("Valid solution specification - continuing.")
    else:
        print(f"Error in solution specification = {msg}")
        return False

    success, msg = check_solution_files_present(solutionSpec["numberOfVersions"])
    if success:
        print(msg)
    else:
        print(msg)
        return False

    # create a tempdir for working
    tmpdir = Path(tempfile.mkdtemp(prefix="tmp_images_", dir=os.getcwd()))

    # split sources pdf into page images
    for v in range(1, testSpec["numberOfVersions"] + 1):
        processFileToBitmaps(source_path / f"solutions{v}.pdf", tmpdir)
    # we now have images of the form solutionsv-p.pdf

    # time to combine things and save in solution_path
    solution_path.mkdir(exist_ok=True)
    for q in range(1, testSpec["numberOfQuestions"] + 1):
        sq = str(q)
        mxv = testSpec["numberOfVersions"]
        if testSpec["question"][sq]["select"] == "fixed":
            mxv = 1  # only do version 1 if 'fixed'
        for v in range(1, mxv + 1):
            image_list = [
                tmpdir / f"solutions{v}-{p}.png"
                for p in solutionSpec["solutionPages"][sq]
            ]
            # check the image list - make sure they exist
            for fn in image_list:
                if fn.is_file() is False:
                    print(f"Error - could not find solution image = {fn.name}")
                    print(
                        "Make sure the structure of your solution pdf matches your test pdf."
                    )
                    shutil.rmtree(tmpdir)
                    return False
            #
            destination = solution_path / f"solution.q{q}.v{v}.png"
            glueImages(image_list, destination)

    shutil.rmtree(tmpdir)

    return True
