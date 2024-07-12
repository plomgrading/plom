# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2021-2022, 2024 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2023 Sophia Vetrici

import fitz
import numpy as np
import PIL.Image
from pytest import raises

from plom.misc_utils import working_directory
from .predictStudentID import compute_probabilities
from .assign_prob import calc_log_likelihood
from .assign_prob import assemble_cost_matrix, lap_solver
from .model_utils import download_or_train_model
from .model_utils import load_model, is_model_present, download_model
from .predictStudentID import get_digit_box, get_digit_prob

from plom.create.demotools import buildDemoSourceFiles
from plom.scan import processFileToBitmaps
from plom.create.scribble_utils import scribble_name_and_id


def test_log_likelihood() -> None:
    student_id = "01234567"
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
    assert calc_log_likelihood("99999999", probabilities) > 100
    with raises(ValueError):
        calc_log_likelihood("123", probabilities)


def test_download_or_train_model(tmp_path) -> None:
    with working_directory(tmp_path):
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
def test_get_digit_box(tmp_path) -> None:
    # for persistent debugging:
    # tmp_path = "/home/cbm/src/plom/plom.git/tmp"

    assert buildDemoSourceFiles(basedir=tmp_path)

    with fitz.open(tmp_path / "sourceVersions/version1.pdf") as d:
        scribble_name_and_id(d, "01234567", "Testy McTester")
        f = tmp_path / "foo.pdf"
        d.save(f)
    files = processFileToBitmaps(f, tmp_path)
    id_img = files[0]

    # these will fail if we don't include the box
    x = get_digit_box(id_img, 0.001, 0.01)
    assert x is None
    x = get_digit_box(id_img, 0.95, 1.0)
    assert x is None

    x = get_digit_box(id_img, 0.01, 0.98)
    # should get a bunch of pixels
    assert len(x) > 100

    # test: list_of_list_of_probabilities
    with working_directory(tmp_path):
        download_or_train_model()
        model = load_model()
    x = get_digit_prob(model, id_img, 0.05, 0.975, 8, debug=False)
    assert len(x) == 8
    for probs in x:
        assert len(probs) == 10
        for p in probs:
            assert 0 <= p <= 1, "Not a probability"

    # test: debug_extracts_images
    with working_directory(tmp_path):
        x = get_digit_prob(model, id_img, 0.0, 1.0, 8, debug=True)
    d = tmp_path / "debug_id_reader"
    assert len(list(d.glob("digit_foo*"))) == 8
    for f in d.glob("digit_*"):
        p = PIL.Image.open(f)
        assert p.width == p.height == 28
    assert len(list(d.glob("idbox_foo*"))) == 1

    # nice to split out but waste to download
    # def test_lap_solver(tmp_path):
    # assert buildDemoSourceFiles(basedir=tmp_path)

    miniclass = [
        {"id": "01234567", "studentName": "Testy McTester"},
        {"id": "07654321", "studentName": "Testing van Test"},
        {"id": "01010101", "studentName": "Tessa Ting"},
        {"id": "01277777", "studentName": "MC Test-a-lot"},
        {"id": "01277788", "studentName": "DJ Testerella"},
    ]
    _id_imgs = []
    for s in miniclass:
        with fitz.open(tmp_path / "sourceVersions/version1.pdf") as d:
            scribble_name_and_id(d, s["id"], s["studentName"], seed=42)
            f = tmp_path / f"mytest_{s['id']}.pdf"
            d.save(f)
        files = processFileToBitmaps(f, tmp_path)
        _id_imgs.append(files[0])

    id_imgs = {(k + 1): x for k, x in enumerate(_id_imgs)}
    test_nums = list(range(1, len(id_imgs)))
    ids = [x["id"] for x in miniclass]
    with working_directory(tmp_path):
        probs = compute_probabilities(id_imgs, 0.15, 0.9, 8)
        _ = assemble_cost_matrix(test_nums, ids, probs)
        pred = lap_solver(test_nums, ids, probs)

    for P, S in zip(pred, miniclass):
        assert P[1] == S["id"]
