# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Andrew Rechnitzer
import getpass
import os
from pathlib import Path
from PIL import Image
import shutil
import tempfile

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


def extractSolutionImages(server, password):
    spec = getSpec(server, password)

    success, msg = check_solution_files_present(spec["numberOfVersions"])
    if success:
        print(msg)
    else:
        print(msg)
        return False

    # create a tempdir for working
    tmpdir = Path(tempfile.mkdtemp(prefix="tmp_images_", dir=os.getcwd()))

    # split sources pdf into page images
    for v in range(1, spec["numberOfVersions"] + 1):
        processFileToBitmaps(source_path / f"solutions{v}.pdf", tmpdir)
    # we now have images of the form solutionsv-p.pdf

    # time to combine things and save in solution_path
    solution_path.mkdir(exist_ok=True)
    for q in range(1, spec["numberOfQuestions"] + 1):
        sq = str(q)
        mxv = spec["numberOfVersions"]
        if spec["question"][sq]["select"] == "fixed":
            mxv = 1  # only do version 1 if 'fixed'
        for v in range(1, mxv + 1):
            image_list = [
                tmpdir / f"solutions{v}-{p}.png" for p in spec["question"][sq]["pages"]
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
