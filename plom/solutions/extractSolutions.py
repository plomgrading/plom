# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Andrew Rechnitzer
# Copyright (C) 2022-2023 Colin B. Macdonald

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

    Returns:
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

        # time to combine things and save in solution_path
        solution_path.mkdir(exist_ok=True)

        # split sources pdf into page images
        for v in range(1, testSpec["numberOfVersions"] + 1):
            bitmaps = processFileToBitmaps(source_path / f"solutions{v}.pdf", tmp)
            for q in range(1, testSpec["numberOfQuestions"] + 1):
                sq = str(q)
                if testSpec["question"][sq]["select"] == "fix":
                    if v != 1:
                        continue
                pages = solutionSpec["solution"][sq]["pages"]
                print(f"Processing solutions for Q{q} V{v}: getting pages {pages}")
                try:
                    # note `pages` assumes indexed from 1
                    image_list = [bitmaps[p - 1] for p in pages]
                except IndexError as e:
                    raise RuntimeError(
                        f"Could not find solution image for a page: {e}\n"
                        "Make sure structure of solution pdf matches your test pdf"
                        " or that you provide a custom solution specification."
                    ) from e
                destination = solution_path / f"solution.q{q}.v{v}.png"
                glueImages(image_list, destination)

    return True
