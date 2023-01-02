# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020, 2022-2023 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe

"""
Digit hunter extracts random digit images from the MNIST database
and stores then in a json file (used to create digits.json).  The
results are used by various demo tools to create fake ID-pages.
This python program not run on a normal Plom (or demo) run, however it
is being kept in the repo for posterity.

Dataset used: https://en.wikipedia.org/wiki/MNIST_database
"""

import base64
import json
from random import sample
from collections import defaultdict
import subprocess

import numpy as np
import tensorflow as tf
import cv2

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

        # quantize
        # img = np.round(np.round(img / 255.0 * 3) / 3.0 * 255)

        # colorize
        bgr = np.zeros((28, 28, 3))
        bgr[:, :, 0] = img // 4 + 192  # blue to [192, 255]
        bgr[:, :, 1] = img
        bgr[:, :, 2] = img

        worked, buf = cv2.imencode(".png", bgr)

        # pngquant to compress to 4-colour
        # TODO: faster to use a pipe instead of so much disk access
        fname = "tmpdigit.png"
        with open(fname, "wb") as f:
            f.write(buf)
        subprocess.check_call(["pngquant", "4", "--force", fname])
        with open(fname.replace(".png", "-fs8.png"), "rb") as f:
            buf = f.read()

        # cv2.imshow("argh", img)
        if worked is False:
            print("EEK - problem")
            quit()
        imgs.append(base64.b64encode(buf).decode())

with open("digits.json", "w") as fh:
    json.dump(imgs, fh)
