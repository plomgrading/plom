# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2021-2022 Colin B. Macdonald

from pathlib import Path

import numpy as np

from plom.misc_utils import working_directory
from .idReader import calc_log_likelihood
from .idReader import is_model_present, download_model, download_or_train_model
from .model_utils import load_model
from .predictStudentID import get_digit_box, get_digit_prob
from plom.produce.demotools import buildDemoSourceFiles
from plom.scan.scansToImages import processFileToBitmaps


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


def test_get_digit_box(tmpdir):
    tmpdir = Path(tmpdir)
    # for persistent debugging:
    # tmpdir = Path("home/cbm/src/plom/plom.git/tmp")
    assert buildDemoSourceFiles(basedir=tmpdir)
    # TODO: we should scribble on them here?
    files = processFileToBitmaps(tmpdir / "sourceVersions/version1.pdf", tmpdir)

    id_img = files[0]
    # these will fail if we don't include the box
    x = get_digit_box(id_img, 5, 10)
    assert x is None
    x = get_digit_box(id_img, 1900, 2000)
    assert x is None

    x = get_digit_box(id_img, 100, 1950)
    # should get a bunch of pixels
    assert len(x) > 100

    # TODO: it downloads even if present!
    with working_directory(tmpdir):
        download_or_train_model()
        model = load_model()

    # TODO: b/c we didn't scribble, this likely to fail
    x = get_digit_prob(model, id_img, 100, 1950, 8)
    assert len(x) == 0 or len(x) == 8
