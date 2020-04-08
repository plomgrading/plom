__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
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
# left = int(sys.argv[1])
top = int(sys.argv[1])
# width = int(sys.argv[3])
height = int(sys.argv[2])
bottom = top + height
print("Will examine vertical range of images [{}:{}]".format(top, bottom))

# Dictionary of scans and their digit-log-likes
scans = {}
# List of student numbers in classlist
studentNumbers = []

import tensorflow as tf
from tensorflow import keras
import tensorflow.python.keras.backend as K

# hack suggested here https://github.com/tensorflow/tensorflow/issues/34201
# import tensorflow.keras.backend as K

model = tf.keras.models.load_model("plomBuzzword")


# from https://fairyonice.github.io/Measure-the-uncertainty-in-deep-learning-models-using-dropout.html


class KerasDropoutPrediction(object):
    def __init__(self, model):
        self.f = K.function(
            [model.layers[0].input, K.symbolic_learning_phase()], [model.output],
        )

    def predict(self, x, n_iter=20):
        result = []
        for _ in range(n_iter):
            result.append(self.f([x, True]))
        result = np.array(result).reshape(n_iter, 10).T
        return result


model.compile(
    optimizer="adam",
    loss="sparse_categorical_crossentropy",
    metrics=[tf.keras.metrics.SparseCategoricalAccuracy()],
)
kdp = KerasDropoutPrediction(model)


def getDigits(fn):
    # define this in order to sort by area of bounding rect
    def boundingRectArea(tau):
        x, y, w, h = cv2.boundingRect(tau)
        return w * h

    # read in the whole
    wholeImage = cv2.imread(fn)
    # extract only the required portion of the image.
    image = wholeImage[:][top:bottom]
    # proces the image so as to find the countours
    grey = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(grey, (5, 5), 0)
    edged = cv2.Canny(blurred, 50, 200, 255)

    contours = cv2.findContours(
        edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    contourList = imutils.grab_contours(contours)
    sortedContourList = sorted(contourList, key=cv2.contourArea, reverse=True)
    displayContour = None

    # loop over the contours
    for tau in sortedContourList:
        # approximate the contour
        peri = cv2.arcLength(tau, True)
        approx = cv2.approxPolyDP(tau, 0.02 * peri, True)
        if len(approx) == 4:
            displayContour = approx
            break

    warped = four_point_transform(edged, displayContour.reshape(4, 2))
    output = four_point_transform(image, displayContour.reshape(4, 2))
    # note that this width of 1250 is defined by the IDbox template
    newWidth = int(output.shape[0] * 1250.0 / output.shape[1])
    scaled = cv2.resize(output, (1250, newWidth), cv2.INTER_CUBIC)
    # the digit box numbers again come from the IDBox template and numerology
    digitBoxes = scaled[30:130, 355:1220]
    # the following are useful for debugging if template changed
    # cv2.imshow("The ID digits", digitBoxes)
    # cv2.waitKey(0)  # waits until a key is pressed
    # cv2.destroyAllWindows()  # destroys the window showing image

    lst = []
    for k in range(8):
        # extract the kth digit box. Some magical hackery / numerology here.
        digit1 = digitBoxes[0:100, k * 109 + 5 : (k + 1) * 109 - 5]
        # now some hackery to centre on the digit so closer to mnist dataset
        # find the contours and centre on the largest (by area)
        digit2 = cv2.GaussianBlur(digit1, (3, 3), 0)
        digit3 = cv2.Canny(digit2, 5, 255, 200)
        contours = cv2.findContours(
            digit3.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        contourList = imutils.grab_contours(contours)
        # sort by bounding box area
        sortedContours = sorted(contours, key=boundingRectArea, reverse=True)
        # make sure we can find at least one contour
        if len(sortedContours) == 0:
            # can't make a prediction so return
            return None
        # get bounding rect of biggest contour
        bnd = cv2.boundingRect(sortedContours[0])
        # put some padding around that rectangle
        pad = 10
        xl = max(0, bnd[1] - pad)
        yt = max(0, bnd[0] - pad)
        # grab the image - should be the digit.
        digit4 = digit2[xl : bnd[1] + bnd[3] + pad, yt : bnd[0] + bnd[2] + pad]
        # Do some clean-up
        digit5 = cv2.adaptiveThreshold(
            cv2.cvtColor(digit4, cv2.COLOR_BGR2GRAY),
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            31,
            1,
        )
        # and a little more - blur helps get rid of "dust" artefacts
        digit6 = cv2.blur(digit5, (3, 3))
        # now need to resize it to height or width =28 (depending on aspect ratio)
        # the "28" comes from mnist dataset
        rat = digit5.shape[0] / digit5.shape[1]
        if rat > 1:
            w = 28
            h = int(28 // rat)
        else:
            w = int(28 * rat)
            h = 28
        # region of interest
        roi = cv2.resize(digit6, (h, w), interpolation=cv2.INTER_AREA)
        px = int((28 - w) // 2)
        py = int((28 - h) // 2)
        # and a bit more clean-up - put black around border where needed
        roi2 = cv2.copyMakeBorder(
            roi, px, 28 - w - px, py, 28 - h - py, cv2.BORDER_CONSTANT, value=[0, 0, 0]
        )
        # get it into format needed by tensorflow predictor
        roi3 = np.expand_dims(roi2, 0)
        # do the actual prediction! (ie approx probabilities that image is digit 0,1,2,..,9)
        pred = kdp.predict(roi3).mean(axis=1)

        # and append that prediction to list
        lst.append(pred)
    return lst


def logLike(sid, probs):
    # pass in the student ID-digits and the probs
    # probs = scans[fn]
    # probs[k][n] = approx prob that digit k of ID is n.
    logP = 0
    # logP will be the approx -log(prob) - so more probable means smaller logP.
    # make it negative since we'll minimise "cost" when we do the linear assignment problem stuff below.
    for k in range(0, 8):
        d = int(sid[k])
        logP -= np.log(max(probs[k][d], 1e-30))  # avoids taking log of 0.
    return logP


# todo update file paths
# read in the list of student numbers
with open("../specAndDatabase/classlist.csv", newline="") as csvfile:
    red = csv.reader(csvfile, delimiter=",")
    next(red, None)
    for row in red:
        studentNumbers.append(row[0])

    # read each scan and process it into log-likes
    fnumber = 0
    # for fn in sorted(glob.glob("../scanAndGroup/readyForMarking/idgroup/*idg.png")):
    for fn in sorted(glob.glob("./pages/*.png")):
        lst = getDigits(fn)
        dig = [np.argmax(v) for v in lst]
        print("Processing {} = {}".format(fn, dig))
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
        lst.append(logLike(x, scans[fn]))
    costs.append(lst)

# Computing minimum cost matrix
rids, cids = solve_dense(costs)
with open("./predictionlist.csv", "w") as fh:
    fh.write("test, id\n")
    for r, c in zip(rids, cids):
        # each filename is <blah>/tXXXXidg.png
        basef = os.path.basename(fnames[r])
        # so extract digits 1234
        testNumber = basef[1:5]
        print("{}, {}".format(testNumber, studentNumbers[c]))
        fh.write("{}, {}\n".format(testNumber, studentNumbers[c]))
    fh.close()
