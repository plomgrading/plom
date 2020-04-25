# -*- coding: utf-8 -*-

"""Digit hunter extracts random digit images from the MNIST database and stores then in a json file. The results are used by faketools.py to create ID-pages for the plom-demo."""

__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer and Colin B. Macdonald"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import base64
import cv2
import json
import numpy as np
from random import sample
import tensorflow as tf
from collections import defaultdict
import subprocess

# pair (x_train, y_train), (x_test, y_test) from mnist dataset
mnist = tf.keras.datasets.mnist.load_data()
names = mnist[1][1]
images = mnist[1][0]

N = 32  # how many of each digit to collect
digits = defaultdict(list)

for k in range(len(names)):
    digits[names[k]].append(k)

print("Collected random digits. Now saving them.")
imgs = []
for d in range(10):
    theDigits = sample(digits[d], N)
    for k in range(N):
        c = digits[d][k]
        img = ~images[c]  # since digit is bitwise-inverted.
        assert img.shape == (28, 28)

        # colorize
        bgr = np.zeros((28, 28, 3))
        bgr[:,:,0] = 255
        bgr[:,:,1] = img
        bgr[:,:,2] = img

        worked, buf = cv2.imencode(".png", bgr)

        #cv2.imshow("argh", img)
        if worked is False:
            print("EEK - problem")
            quit()
        imgs.append(base64.b64encode(buf).decode())

with open("digits.json", "w") as fh:
    json.dump(imgs, fh)
