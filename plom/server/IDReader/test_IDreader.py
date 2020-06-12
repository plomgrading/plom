from .idReader import (
    is_model_absent,
    log_likelihood,
    download_or_train_model,
    run_id_reader,
)


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

    student_ids = [i for i in range(2, 10)]
    probabilities = [
        [0, 0, 0.5, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0.5, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0.5, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0.5, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0.5, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0.5, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0.5, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0.5],
    ]
    assert log_likelihood(student_ids, probabilities) == 5.545177444479562


def test_download_or_train_model():
    assert is_model_absent() == True
    download_or_train_model()  # Although we cannot directly check the output of download_or_train_model, we can check that the is correct files are present and the function works as intended
    assert is_model_absent() == False


def test_full_idreader_test():
    # import libraries for this unit test
    import os
    import json
    import requests
    from pathlib import Path
    import shutil
    import csv

    basePath = Path("")

    baseUrl = "https://gitlab.com/drydenwiebe/plomidreadertestdata/-/raw/master/"
    files = [
        "IDReaderTest.lock",
        "predictionlist_test.csv",
    ]

    for fn in files:
        url = baseUrl + fn
        print("Getting {} - ".format(fn))
        response = requests.get(url)
        if response.status_code != 200:
            print("\tError getting file {}.".format(fn))
        else:
            print("\tDone.")
        with open(basePath / fn, "wb+") as fh:
            fh.write(response.content)

    baseUrl = "https://gitlab.com/drydenwiebe/plomidreadertestdata/-/raw/master"

    cover_pages = [
        "t0020p05v2.d8c74e70.png",
        "t0003p02v1.339c437a.png",
        "t0007p02v1.fe1e9e87.png",
        "t0008p05v2.d02997eb.png",
        "t0018p02v1.0afa5d80.png",
        "t0017p01v1.933f093a.png",
        "t0006p06v2.83951c02.png",
        "t0016p04v1.6bf038c1.png",
        "t0015p04v1.452b3bb2.png",
        "t0006p01v1.4d0a2fea.png",
        "t0009p01v1.af691137.png",
        "t0018p05v2.55e0e9c0.png",
        "t0010p05v2.e820e960.png",
        "t0014p04v1.d389a05f.png",
        "t0020p01v1.e6ee8bfd.png",
        "t0003p05v2.1304c3e2.png",
        "t0002p01v1.1a96e3b2.png",
        "t0017p04v1.c6101da6.png",
        "t0018p03v2.70159fa8.png",
        "t0009p04v1.50c007db.png",
        "t0017p02v1.336a7e34.png",
        "t0014p02v1.c3ab59e2.png",
        "t0013p02v1.8ebb93ea.png",
        "t0016p06v2.019781da.png",
        "t0012p06v2.e3844f15.png",
        "t0009p06v1.b1adb177.png",
        "t0013p04v1.4da5af79.png",
        "t0010p04v1.8a1cd581.png",
        "t0015p05v2.8997353c.png",
        "t0011p04v1.ccc6dc36.png",
        "t0005p04v1.1ddf3ae7.png",
        "t0005p03v2.c9c0d83f.png",
        "t0003p01v1.7678295c.png",
        "t0017p05v1.1bdc30e8.png",
        "t0005p01v1.94f780ca.png",
        "t0004p05v1.69ccf54a.png",
        "t0006p05v2.32c9af33.png",
        "t0012p05v2.38c7a9a8.png",
        "t0009p05v1.c8d699bb.png",
        "t0005p05v1.28b2fb62.png",
        "t0015p01v1.7d43ff2b.png",
        "t0014p03v2.270138ad.png",
        "t0001p03v2.7bd18a0e.png",
        "t0011p01v1.e390fe0a.png",
        "t0008p03v2.71e6db13.png",
        "t0007p01v1.bb6481de.png",
        "t0007p05v2.5c2d5863.png",
        "t0016p05v2.dbc78cf0.png",
        "t0017p03v2.8b984b20.png",
        "t0020p02v1.20525f1b.png",
        "t0001p05v1.f41493f3.png",
        "t0016p01v1.318cf4cd.png",
        "t0019p01v1.827a450c.png",
        "t0005p02v1.e9f6539f.png",
        "t0012p02v1.df3296bf.png",
        "t0008p01v1.9a1fcad0.png",
        "t0013p03v1.4aa4d3e8.png",
        "t0019p02v1.c6e52cbb.png",
        "t0009p02v1.271f2a8b.png",
        "t0006p02v1.beafbc04.png",
        "t0004p06v1.29fe7363.png",
        "t0017p06v1.de29f7c3.png",
        "t0010p02v1.0eb92e36.png",
        "t0010p01v1.7895a062.png",
        "t0014p05v1.9243de48.png",
        "t0002p05v1.ccab2797.png",
        "t0007p03v1.d5cde37d.png",
        "t0011p06v2.fb590345.png",
        "t0002p06v1.f06d73e6.png",
        "t0002p02v1.01587bd3.png",
        "t0006p04v1.5f5607c5.png",
        "t0003p04v1.9375da55.png",
        "t0001p04v1.469259e9.png",
        "t0008p02v1.3f771939.png",
        "t0011p05v2.56f64e04.png",
        "t0004p01v1.bfb46a55.png",
        "t0002p03v1.cbed7dba.png",
        "t0007p06v2.ad20f966.png",
        "t0014p01v1.5e25f997.png",
        "t0012p04v1.0fc8d7a3.png",
        "t0005p06v1.9a3b7154.png",
        "t0019p04v1.396d0023.png",
        "t0016p03v1.994e74a0.png",
        "t0018p06v2.43a7515a.png",
        "t0018p01v1.117dc5d4.png",
        "t0014p06v1.9f340ba7.png",
        "t0016p02v1.d4715d9d.png",
        "t0004p03v2.644bff98.png",
        "t0011p03v2.b6cff136.png",
        "t0015p06v2.3f0825a1.png",
        "t0008p04v1.0b453251.png",
        "t0019p03v1.73f64c40.png",
        "t0012p03v1.389c7ffe.png",
        "t0013p01v1.b1534468.png",
        "t0019p05v1.5b0eb646.png",
        "t0015p02v1.11147004.png",
        "t0004p02v1.a1198fe7.png",
        "t0009p03v2.bb9a1104.png",
        "t0006p03v2.5f6de33e.png",
        "t0007p04v1.4fd26ec6.png",
        "t0015p03v1.7c509461.png",
        "t0018p04v1.62937fe7.png",
        "t0013p06v1.c23b2d72.png",
        "t0008p06v2.b1243db9.png",
        "t0019p06v1.125456b5.png",
        "t0003p03v1.62a5d429.png",
        "t0010p03v2.a8c18e6e.png",
        "t0010p06v2.d557c54f.png",
        "t0012p01v1.6e3daace.png",
        "t0004p04v1.ba3408b6.png",
        "t0001p02v1.04ed958e.png",
        "t0020p04v1.0e7eec0e.png",
        "t0003p06v2.4d2acd77.png",
        "t0011p02v1.2ad31260.png",
        "t0001p01v1.8019d160.png",
        "t0013p05v1.7551bf45.png",
        "t0020p06v2.be301ff1.png",
        "t0020p03v1.abd12a48.png",
        "t0002p04v1.faf5626e.png",
    ]

    if not os.path.exists(os.getcwd() + "/pages/originalPages"):
        os.makedirs(os.getcwd() + "/pages/originalPages")

    for fn in cover_pages:
        url = baseUrl + "/pages/originalPages/" + fn
        print("Getting {} - ".format(fn))
        response = requests.get(url)
        if response.status_code != 200:
            print("\tError getting file {}.".format(fn))
        else:
            print("\tDone.")
        with open(basePath / fn, "wb") as fh:
            fh.write(response.content)
            shutil.move(
                str(os.getcwd()) + "/" + fn,
                str(os.getcwd()) + "/pages/originalPages/" + fn,
            )

    files = [
        "classlist.csv",
        "pageNotSubmitted.pdf",
        "verifiedSpec.toml",
        "IDReader.timestamp",
        "plom.db",
        "questionNotSubmitted.pdf",
    ]

    if not os.path.exists(os.getcwd() + "/specAndDatabase"):
        os.makedirs(os.getcwd() + "/specAndDatabase")

    for fn in files:
        url = baseUrl + "/specAndDatabase/" + fn
        print("Getting {} - ".format(fn))
        response = requests.get(url)
        if response.status_code != 200:
            print("\tError getting file {}.".format(fn))
        else:
            print("\tDone.")
        with open(basePath / fn, "wb") as fh:
            fh.write(response.content)
            shutil.move(
                str(os.getcwd()) + "/" + fn, str(os.getcwd()) + "/specAndDatabase/" + fn
            )

    lock_file = "IDReaderTest.lock"

    if not os.path.isfile(lock_file):
        assert False

    with open(lock_file) as f:
        fileDictAndRect = json.load(f)

    run_id_reader(fileDictAndRect[0], fileDictAndRect[1])

    # read in all of the student numbers in the predicted list and assert that they are in the test class list

    predicted_classlist = "specAndDatabase/predictionlist.csv"

    with open(predicted_classlist) as f:
        predicted_classlist_csv = csv.reader(f)
        for row in predicted_classlist_csv:
            assert len(row[1]) == 9 or len(row[1]) == 3

    for path in ["pages", "specAndDatabase", "plomBuzzword"]:
        try:
            shutil.rmtree(path)
        except PermissionError:
            pass

    for fn in ["predictionlist_test.csv", lock_file]:
        try:
            os.unlink(fn)
        except PermissionError:
            pass


if __name__ == "__main__":
    test_full_idreader_test()
