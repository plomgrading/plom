__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin MacDonald"]
__license__ = "AGPLv3"

## https://www.pyimagesearch.com/2017/02/13/recognizing-digits-with-opencv-and-python/
import csv
import cv2
import glob
import imutils
from imutils.perspective import four_point_transform
from imutils import contours
from lapsolver import solve_dense
import numpy as np
import json
import os
import sys

# Get vertical range of image to examine from argv
top = int(sys.argv[1])
bottom = int(sys.argv[2])
print("Will examine vertical range of images [{}:{}]".format(top, bottom))

# Dictionary of scans and their digit-log-likes
scans = {}
# List of student numbers in classlist
studentNumbers = []

import tensorflow as tf
from tensorflow import keras
import tensorflow.keras.backend as K

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

# from https://fairyonice.github.io/Measure-the-uncertainty-in-deep-learning-models-using-dropout.html
class KerasDropoutPrediction(object):
    def __init__(self, model):
        self.f = K.function(
            [model.layers[0].input, K.learning_phase()], [model.layers[-1].output]
        )

    def predict(self, x, n_iter=20):
        result = []
        for _ in range(n_iter):
            result.append(self.f([x, 1]))
        result = np.array(result).reshape(n_iter, 10).T
        return result


def boundingRectArea(cnt):
    x, y, w, h = cv2.boundingRect(cnt)
    return w * h


k = 0


def getDigits(fn):
    preproc = cv2.imread(fn)
    # extract only the required portion of the image.
    image = preproc[:][top:bottom]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 50, 200, 255)

    cnts = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = imutils.grab_contours(cnts)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)
    displayCnt = None

    # loop over the contours
    for c in cnts:
        # approximate the contour
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            displayCnt = approx
            break

    warped = four_point_transform(edged, displayCnt.reshape(4, 2))
    output = four_point_transform(image, displayCnt.reshape(4, 2))
    newWidth = int(output.shape[0] * 1250.0 / output.shape[1])
    scaled = cv2.resize(output, (1250, newWidth), cv2.INTER_CUBIC)
    meh = scaled[30:130, 355:1220]
    lst = []
    for k in range(8):
        digit1 = meh[0:100, k * 109 + 5 : (k + 1) * 109 - 5]
        digit2 = cv2.GaussianBlur(digit1, (3, 3), 0)
        digit3 = cv2.Canny(digit2, 5, 255, 200)
        contours = cv2.findContours(
            digit3.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        contours = imutils.grab_contours(contours)
        contours = sorted(contours, key=boundingRectArea, reverse=True)
        if len(contours) == 0:
            return None

        bnd = cv2.boundingRect(contours[0])
        cv2.rectangle(
            digit3, (bnd[0], bnd[1]), (bnd[0] + bnd[2], bnd[1] + bnd[3]), (255, 0, 0), 2
        )

        pad = 10
        xl = max(0, bnd[1] - pad)
        yt = max(0, bnd[0] - pad)
        digit4 = digit2[xl : bnd[1] + bnd[3] + pad, yt : bnd[0] + bnd[2] + pad]

        digit5 = cv2.adaptiveThreshold(
            cv2.cvtColor(digit4, cv2.COLOR_BGR2GRAY),
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            31,
            1,
        )
        digit6 = cv2.blur(digit5, (3, 3))
        rat = digit5.shape[0] / digit5.shape[1]
        if rat > 1:
            w = 28
            h = int(28 // rat)
        else:
            w = int(28 * rat)
            h = 28
        roi = cv2.resize(digit6, (h, w), interpolation=cv2.INTER_AREA)
        px = int((28 - w) // 2)
        py = int((28 - h) // 2)

        roi2 = cv2.copyMakeBorder(
            roi, px, 28 - w - px, py, 28 - h - py, cv2.BORDER_CONSTANT, value=[0, 0, 0]
        )
        roi3 = np.expand_dims(roi2, 0)
        pred = kdp.predict(roi3).mean(axis=1)
        # lst.append(np.argmax(pred))
        lst.append(pred)
    return lst


def logLike(sid, fn):
    ll = scans[fn]
    p = 0
    for k in range(0, 8):
        d = int(sid[k])
        p -= np.log(max(ll[k][d], 1e-30))
    return p


# read in the list of student numbers
with open("../resources/classlist.csv", newline="") as csvfile:
    red = csv.reader(csvfile, delimiter=",")
    next(red, None)
    for row in red:
        studentNumbers.append(row[0])

with tf.Session() as sess:
    # Restore variables from disk.
    saver.restore(sess, "digitModel")
    model.compile(
        optimizer=tf.train.AdamOptimizer(0.00001),
        loss="sparse_categorical_crossentropy",
        metrics=[tf.keras.metrics.SparseCategoricalAccuracy()],
    )
    kdp = KerasDropoutPrediction(model)
    # read each scan and process it into log-likes
    fnumber = 0
    for fn in sorted(glob.glob("../scanAndGroup/readyForMarking/idgroup/*idg.png")):
        print("Processing {}".format(fn))
        lst = getDigits(fn)
        if lst is None:
            # couldn't recognize digits
            continue
        fnumber += 1
        scans[fn] = lst


# build the munkres cost matrix
costs = []
fnames = list(scans.keys())
tlist = {}

for fn in fnames:
    lst = []
    for x in studentNumbers:
        lst.append(logLike(x, fn))
    costs.append(lst)

# Computing minimum cost matrix
rids, cids = solve_dense(costs)
with open("../resources/predictionlist.csv", "w") as fh:
    fh.write("test, id\n")
    for r, c in zip(rids, cids):
        # each filename is <blah>/tXXXXidg.png
        basef = os.path.basename(fnames[r])
        # so extract digits 1234
        testNumber = basef[1:5]
        print("{}, {}".format(testNumber, studentNumbers[c]))
        fh.write("{}, {}\n".format(testNumber, studentNumbers[c]))
    fh.close()
