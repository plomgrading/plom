import cv2
import numpy as np
from random import sample
from collections import defaultdict

mnist = np.load("/home/andrew/.keras/datasets/mnist.npz")

N = 16  # how many of each digit to collect
digits = defaultdict(list)

for k in range(len(mnist["y_test"])):
    digits[mnist["y_test"][k]].append(k)

print("Collected random digits. Now saving them.")
imgs = []
for d in range(10):
    theDigits = sample(digits[d], N)
    for k in range(N):
        c = digits[d][k]
        img = ~mnist["x_test"][c]  # since digit is bitwise-inverted.
        # img2 = cv2.resize(img, (64, 64), interpolation=cv2.INTER_CUBIC)
        # fname = "mnist_{}_{}.png".format(d, k)
        # cv2.imwrite(fname, img)
        imgs.append(img)

np.savez("digits.npz".format(d), np.array(imgs))
