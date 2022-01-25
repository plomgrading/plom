# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2021-2022 Colin B. Macdonald

from pathlib import Path

import fitz
import numpy as np
import PIL.Image
from pytest import raises

from plom.misc_utils import working_directory
from .idReader import calc_log_likelihood, run_id_reader
from .model_utils import (
    load_model,
    is_model_present,
    download_model,
    download_or_train_model,
)
from .predictStudentID import get_digit_box, get_digit_prob
from plom.create.demotools import buildDemoSourceFiles
from plom.scan import processFileToBitmaps
from plom.create.scribble_utils import scribble_name_and_id


def test_log_likelihood():
    student_id = [i for i in range(0, 8)]
    probabilities = [
        [0.5, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0.5, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0.5, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0.5, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0.5, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0.5, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0.5, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0.5, 0, 0],
    ]
    assert np.isclose(
        calc_log_likelihood(student_id, probabilities),
        5.545177444479562,
        1e-7,
    )
    assert calc_log_likelihood([9] * 8, probabilities) > 100
    with raises(ValueError):
        calc_log_likelihood([1, 2, 3], probabilities)


def test_download_or_train_model(tmpdir):
    with working_directory(tmpdir):
        assert not is_model_present()
        assert download_model()
        # check correct files are present
        assert is_model_present()
        download_or_train_model()
        assert is_model_present()
        m = load_model()
        # check something about the model
        assert isinstance(m.get_params(), dict)


# Bit messy with so many subtests: refactor to a setup / teardown class?
def test_get_digit_box(tmpdir):
    tmpdir = Path(tmpdir)
    # for persistent debugging:
    # tmpdir = Path("/home/cbm/src/plom/plom.git/tmp")

    assert buildDemoSourceFiles(basedir=tmpdir)

    d = fitz.open(tmpdir / "sourceVersions/version1.pdf")
    scribble_name_and_id(d, "01234567", "Testy McTester")
    f = tmpdir / "foo.pdf"
    d.save(f)
    d.close()
    files = processFileToBitmaps(f, tmpdir)
    id_img = files[0]

    # these will fail if we don't include the box
    x = get_digit_box(id_img, 5, 10)
    assert x is None
    x = get_digit_box(id_img, 1900, 2000)
    assert x is None

    x = get_digit_box(id_img, 100, 1950)
    # should get a bunch of pixels
    assert len(x) > 100

    # test: list_of_list_of_probabilities
    with working_directory(tmpdir):
        download_or_train_model()
        model = load_model()
    x = get_digit_prob(model, id_img, 100, 1950, 8, debug=False)
    assert len(x) == 8
    for probs in x:
        assert len(probs) == 10
        for p in probs:
            assert 0 <= p <= 1, "Not a probablility"

    # test: debug_extracts_images
    with working_directory(tmpdir):
        x = get_digit_prob(model, id_img, 1, 2000, 8, debug=True)
    d = tmpdir / "debug_id_reader"
    assert len(list(d.glob("digit_foo*"))) == 8
    for f in d.glob("digit_*"):
        p = PIL.Image.open(f)
        assert p.width == p.height == 28
    assert len(list(d.glob("idbox_foo*"))) == 1

    # nice to split out but waste to download
    # def test_lap_solver(tmpdir):
    # tmpdir = Path(tmpdir)
    # assert buildDemoSourceFiles(basedir=tmpdir)

    miniclass = [
        {"id": "01234567", "studentName": "Testy McTester"},
        {"id": "07654321", "studentName": "Testing van Test"},
        {"id": "01010101", "studentName": "Tessa Ting"},
        {"id": "01277777", "studentName": "MC Test-a-lot"},
        {"id": "01277788", "studentName": "DJ Testerella"},
    ]
    id_imgs = []
    for s in miniclass:
        d = fitz.open(tmpdir / "sourceVersions/version1.pdf")
        scribble_name_and_id(d, s["id"], s["studentName"], seed=42)
        f = tmpdir / f"mytest_{s['id']}.pdf"
        d.save(f)
        d.close()
        files = processFileToBitmaps(f, tmpdir)
        id_imgs.append(files[0])

    id_imgs = {(k + 1): x for k, x in enumerate(id_imgs)}
    with working_directory(tmpdir):
        pred = run_id_reader(id_imgs, [0, 300, 0, 1800], [x["id"] for x in miniclass])
    for P, S in zip(pred, miniclass):
        assert P[1] == S["id"]
