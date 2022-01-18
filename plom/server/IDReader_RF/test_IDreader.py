# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2021-2022 Colin B. Macdonald

from pathlib import Path
import shutil

import numpy as np
import PIL.Image

from plom.misc_utils import working_directory
from .idReader import calc_log_likelihood
from .model_utils import (
    load_model,
    is_model_present,
    download_model,
    download_or_train_model,
)
from .predictStudentID import get_digit_box, get_digit_prob
from plom.produce.demotools import buildDemoSourceFiles
from plom.scan.scansToImages import processFileToBitmaps
from plom.produce.scribble_utils import fill_in_fake_data_on_exams


def test_log_likelihood():
    num_digits = 8
    student_ids = [i for i in range(0, num_digits)]
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
    assert bool(
        np.isclose(
            calc_log_likelihood(student_ids, probabilities, num_digits),
            5.545177444479562,
            1e-7,
        )
    )


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

    shutil.copy(tmpdir / "sourceVersions/version1.pdf", tmpdir / "exam_0001.pdf")
    miniclass = [{"id": "01234567", "studentName": "Testy McTester"}]
    fill_in_fake_data_on_exams(tmpdir, miniclass, tmpdir / "foo.pdf")

    files = processFileToBitmaps(tmpdir / "foo.pdf", tmpdir)
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
    download_or_train_model(tmpdir)
    model = load_model(tmpdir)
    x = get_digit_prob(model, id_img, 100, 1950, 8)
    assert len(x) == 8
    for probs in x:
        assert len(probs) == 10
        for p in probs:
            assert 0 <= p <= 1, "Not a probablility"

    # test: debug_extracts_images
    with working_directory(tmpdir):
        x = get_digit_prob(model, id_img, 1, 2000, 8, debug=True)
    d = tmpdir / "debug_id_reader"
    assert len(list(d.glob("digit_*"))) == 8
    for f in d.glob("digit_*"):
        p = PIL.Image.open(f)
        assert p.width == p.height == 28
    assert len(list(d.glob("idbox_*"))) == 1
