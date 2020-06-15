from .idReader import is_model_absent, log_likelihood, download_or_train_model


def test_is_model_absent():
    assert is_model_absent() == True


def test_log_likelihood():
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
    assert log_likelihood(student_ids, probabilities) == 5.545177444479562


def test_download_or_train_model():
    assert download_or_train_model() == True
    assert is_model_absent() == False
