# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2020-2023 Colin B. Macdonald

"""Utilities to load the digit-prediction model."""

import gzip
from pathlib import Path
import pickle

import requests
import sklearn

from .trainRandomForestModel import train_model


def load_model(where=Path("model_cache")):
    """Load the digit-predictor model from disc.

    Args:
        where (None/pathlib.Path): where to find the the model, defaults
            to "model_cache/" under the current working directory.

    Returns:
        sklearn.RandomForestClassifier: a model trained to predict
        digits in bitmaps.
    """
    filename = f"RF_ML_model_sklearn{sklearn.__version__}.gz"
    with gzip.open(where / filename, "rb") as f:
        return pickle.load(f)


def is_model_present(where=Path("model_cache")):
    """Checks if the ML model is available.

    Args:
        where (pathlib.Path): where to find the the model, defaults
            to "model_cache/" under the current working directory.

    Returns:
        boolean: True/False, indicating if the model is present.
    """
    filename = f"RF_ML_model_sklearn{sklearn.__version__}.gz"
    return (where / filename).exists()


def download_model(where=Path("model_cache")):
    """Try to download the model, respond with False if unsuccessful.

    Args:
        where (None/pathlib.Path): where to look for / put the model,
            defaults to "model_cache/" under the current directory.

    Returns:
        boolean: True/False about if the model was successful.
    """
    where.mkdir(exist_ok=True)

    base_url = "https://gitlab.com/plom/plomidreaderdata/-/raw/main/plomBuzzword/"
    files = [f"RF_ML_model_sklearn{sklearn.__version__}.gz"]
    for file_name in files:
        url = base_url + file_name
        print("Getting {} - ".format(file_name))
        response = requests.get(url)
        if response.status_code != 200:
            print("\tError getting file {}.".format(file_name))
            return False
        with open(where / file_name, "wb") as file_header:
            file_header.write(response.content)
        print("\tDone Saving")
    return True


def download_or_train_model(where=Path("model_cache")):
    """Download the ID detection model if possible, if not, train it.

    Args:
        where (None/pathlib.Path): where to look for / put the model,
            defaults to "model_cache/" under the current directory.

    Returns:
        None

    Prints messages to stdout as it works.
    """
    if is_model_present(where):
        print("Model is already present; no action required")
        return

    print(
        "Will try to download model and if that fails, then train it locally (which is time-consuming)"
    )
    if download_model(where):
        print("Successfully downloaded sklearn (Random-Forest) model. Good to go.")
    else:
        print("Could not download the model, need to train model instead.")
        print(
            "This will take some time -- on the order of 2-3 minutes depending on your computer."
        )
        train_model()
