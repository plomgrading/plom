# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2020 Vala Vakilian

"""
Note: Code in this file is very similar to test_IDreader code for the
Tensorflow model.
"""

from .idReader import is_model_absent, calc_log_likelihood, download_or_train_model


def test_is_model_absent():
    assert is_model_absent() == True


def test_log_likelihood():
    import numpy as np

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


def test_download_or_train_model():
    assert is_model_absent() == True
    download_or_train_model()  # Although we cannot directly check the output of download_or_train_model, we can check that the is correct files are present and the function works as intended
    assert is_model_absent() == False
