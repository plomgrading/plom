__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin MacDonald"]
__license__ = "AGPLv3"

# https://www.digitalocean.com/community/tutorials/how-to-build-a-neural-network-to-recognize-handwritten-digits-with-tensorflow
# and https://www.tensorflow.org/api_docs/python/tf/keras/datasets/mnist/load_data
# https://www.tensorflow.org/tutorials/estimators/cnn

# tensorflow bits and pieces
import tensorflow as tf
from tensorflow import keras

# to check number of cpus
import multiprocessing

ncpu = multiprocessing.cpu_count()

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

saver = tf.train.Saver()

with tf.Session(
    config=tf.ConfigProto(
        device_count={"CPU": ncpu},
        inter_op_parallelism_threads=ncpu,
        intra_op_parallelism_threads=ncpu,
    )
) as sess:
    mnist = tf.keras.datasets.mnist
    (X_train, y_train), (X_test, y_test) = mnist.load_data()

    model.compile(
        optimizer=tf.train.AdamOptimizer(0.00001),
        loss="sparse_categorical_crossentropy",
        metrics=[tf.keras.metrics.SparseCategoricalAccuracy()],
    )

    model.fit(X_train, y_train, epochs=8)

    test_loss, test_acc = model.evaluate(X_test, y_test)

    print("Test accuracy:", test_acc)
    saver.save(sess, "digitModel")
