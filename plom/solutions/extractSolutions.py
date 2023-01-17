# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Andrew Rechnitzer
# Copyright (C) 2022 Colin B. Macdonald

from pathlib import Path
import sys
import tempfile

from PIL import Image

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib
import tomlkit

from plom.scan import processFileToBitmaps
from plom.specVerifier import checkSolutionSpec
from plom.solutions import with_manager_messenger

source_path = Path("sourceVersions")
solution_path = Path("solutionImages")


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
    soln["solution"] = {}
    for q in range(1, testSpec["numberOfQuestions"] + 1):
        soln["solution"][str(q)] = {"pages": testSpec["question"][str(q)]["pages"]}
    return soln


def saveSolutionSpec(solutionSpec):
    with open("solutionSpec.toml", "w") as fh:
        tomlkit.dump(solutionSpec, fh)


def loadSolutionSpec(spec_filename):
    with open(spec_filename, "rb") as fh:
        solutionSpec = tomllib.load(fh)
    return solutionSpec


@with_manager_messenger
def extractSolutionImages(solution_spec_filename=None, *, msgr):
    """Extract solution images from PDF files in special location.

    The PDF files need to be in a special place and have special names.
    TODO: doc better.  Maybe the location could at least be a kwarg with
    a default value.

    Args:
        solution_spec_filename (str/pathlib.Path/None): the spec of the
            solution.  If None, it tries to autoconstruct from the
            server's exam spec.

    Keyword Args:
        msgr (plom.Messenger/tuple): either a connected Messenger or a
            tuple appropriate for credientials.

    Return:
        bytes: the bitmap of the solution.
    """

    testSpec = msgr.get_spec()

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

    with tempfile.TemporaryDirectory() as _td:
        tmp = Path(_td)

        # split sources pdf into page images
        for v in range(1, testSpec["numberOfVersions"] + 1):
            # TODO: Issue #1744: this function returns the filenames...
            processFileToBitmaps(source_path / f"solutions{v}.pdf", tmp)

        # time to combine things and save in solution_path
        solution_path.mkdir(exist_ok=True)
        for q in range(1, testSpec["numberOfQuestions"] + 1):
            sq = str(q)
            mxv = testSpec["numberOfVersions"]
            if testSpec["question"][sq]["select"] == "fix":
                mxv = 1  # only do version 1 if 'fix'
            for v in range(1, mxv + 1):
                print(f"Processing solutions for Q{q} V{v}")
                image_list = [
                    tmp / f"solutions{v}-{p:03}.png"
                    for p in solutionSpec["solution"][sq]["pages"]
                ]
                # maybe processing made jpegs
                for i, f in enumerate(image_list):
                    if not f.is_file():
                        if f.with_suffix(".jpg").is_file():
                            image_list[i] = f.with_suffix(".jpg")
                # check the image list - make sure they exist
                for fn in image_list:
                    if not fn.is_file():
                        print(
                            "Make sure structure of solution pdf matches your test pdf."
                        )
                        raise RuntimeError(
                            f"Error - could not find solution image = {fn.name}"
                        )
                destination = solution_path / f"solution.q{q}.v{v}.png"
                glueImages(image_list, destination)

    return True
