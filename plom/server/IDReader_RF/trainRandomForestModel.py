# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Vala Vakilian

from sklearn.datasets import fetch_openml
from sklearn.model_selection import train_test_split
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import pickle
from sklearn.metrics import accuracy_score


def train_model():
    """Trains the random forest model and saves it."""

    # Fetch the MNIST data.
    mnist = fetch_openml("mnist_784")

    # Retrieve the data and the labels
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

    # Saving the model
    saved_model_fname = "model_cache/RF_ML_model.sav"

    pickle.dump(model, open(saved_model_fname, "wb"))

    # Now we are done, we will do a sanity check
    loaded_model = pickle.load(open(saved_model_fname, "rb"))

    testing_predictions = loaded_model.predict(X_test)
    score = model.score(X_test, y_test)

    score = accuracy_score(testing_predictions, y_test)

    print("Model score is: ", str(score))
    if score < 0.9:
        print(
            "<<<WARNING>>> Model score is too low. This might effect the student ID detections negatively."
        )

    return


if __name__ == "__main__":
    train_model()
