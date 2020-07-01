from .idReader import is_model_absent, log_likelihood, download_or_train_model


def test_is_model_absent():
    assert is_model_absent() == True


def test_log_likelihood():
    import numpy as np
    student_ids = [i for i in range(0, 8)]
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
        np.isclose(log_likelihood(student_ids, probabilities), 5.545177444479562, 1e-7)
    )


def test_download_or_train_model():
    assert is_model_absent() == True
    download_or_train_model()  # Although we cannot directly check the output of download_or_train_model, we can check that the is correct files are present and the function works as intended
    assert is_model_absent() == False
