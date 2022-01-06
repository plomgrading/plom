# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2021 Colin B. Macdonald

import gzip
from pathlib import Path
import pickle
from warnings import warn

import pandas as pd
import sklearn
from sklearn.datasets import fetch_openml
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score


def train_model():
    """Trains the random forest model and saves it."""

    # Fetch the MNIST data.
    mnist = fetch_openml("mnist_784")

    # pylint: disable=no-member
    images = pd.DataFrame(mnist.data)
    labels = pd.DataFrame(mnist.target)

    # Split the data into training and testing data
    X_train, X_test, y_train, y_test = train_test_split(
        mnist.data, mnist.target, test_size=1 / 8.0
    )

    # TODO: This is used only for debugging.
    # X_train = X_train[0:100]
    # y_train = y_train[0:100]

    # Define and Train the model
    model = RandomForestClassifier()
    model.fit(X_train, y_train)

    model_cache = Path("model_cache")
    model_cache.mkdir(exist_ok=True)

    filename = f"RF_ML_model_sklearn{sklearn.__version__}.gz"
    with gzip.open(model_cache / filename, "wb") as f:
        pickle.dump(model, f)

    # Now we are done, we will do a sanity check
    with gzip.open(model_cache / filename, "rb") as f:
        loaded_model = pickle.load(f)
    testing_predictions = loaded_model.predict(X_test)
    # score = model.score(X_test, y_test)
    score = accuracy_score(testing_predictions, y_test)
    print("Model score is: ", str(score))
    if score < 0.95:
        warn(f"Model score {score} is below 95. Consider rerunning to retrain.")


if __name__ == "__main__":
    train_model()
