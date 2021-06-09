# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2020 Vala Vakilian

# https://www.digitalocean.com/community/tutorials/how-to-build-a-neural-network-to-recognize-handwritten-digits-with-tensorflow
# and https://www.tensorflow.org/api_docs/python/tf/keras/datasets/mnist/load_data
# https://www.tensorflow.org/tutorials/estimators/cnn
# and then hacked to work with tensorflow 2.

# tensorflow bits and pieces
import tensorflow as tf
from tensorflow import keras


def train_model():
    """Grab the mnist data to train against."""

    print("Getting mnist handwritten digit data set.")
    mnist = tf.keras.datasets.mnist
    (X_train, y_train), (X_test, y_test) = mnist.load_data()

    # define the model using keras Sequential
    # https://keras.io/guides/sequential_model/
    print("Build and compile digit-recognition model")
    model = keras.Sequential(
        [
            keras.layers.Flatten(input_shape=(28, 28)),
            keras.layers.Reshape((28, 28, 1)),
            keras.layers.Conv2D(
                filters=32, kernel_size=[5, 5], activation=tf.nn.relu, padding="same"
            ),
            keras.layers.MaxPooling2D(pool_size=[2, 2], strides=2),
            keras.layers.Conv2D(
                filters=64, kernel_size=[5, 5], activation=tf.nn.relu, padding="same"
            ),
            keras.layers.MaxPooling2D(pool_size=[2, 2], strides=2),
            keras.layers.Flatten(),
            keras.layers.Dense(units=1024, activation=tf.nn.relu),
            keras.layers.Dropout(rate=0.4),
            keras.layers.Dense(units=10, activation=tf.nn.softmax),
        ]
    )

    # Compile it
    model.compile(
        optimizer="adam",
        loss="sparse_categorical_crossentropy",
        metrics=[tf.keras.metrics.SparseCategoricalAccuracy()],
    )

    print("Start training model")
    # Train it
    model.fit(X_train, y_train, epochs=8)

    test_loss, test_acc = model.evaluate(X_test, y_test)
    print("Accuracy of model on mnist test-set:", test_acc)

    print("Save the model")
    model.save("model_cache")


if __name__ == "__main__":
    train_model()
