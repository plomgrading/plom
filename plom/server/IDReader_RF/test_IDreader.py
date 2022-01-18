# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2021-2022 Colin B. Macdonald

import numpy as np

from plom.misc_utils import working_directory
from .idReader import calc_log_likelihood
from .idReader import is_model_present, download_model, download_or_train_model
from .model_utils import load_model


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
