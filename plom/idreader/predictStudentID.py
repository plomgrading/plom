# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2020-2022 Colin B. Macdonald
# Copyright (c) 2022 Edith Coates

"""
Use image processing to extract and "read" student numbers.

See:
https://www.pyimagesearch.com/2017/02/13/recognizing-digits-with-opencv-and-python/
"""

import math
from pathlib import Path

import numpy as np
import cv2
import imutils
from imutils.perspective import four_point_transform

from .model_utils import load_model


# define this in order to sort by area of bounding rect
def bounding_rect_area(bounding_rectangle):
    """Return the area of the rectangle.

    Args:
        bounding_rectangle (list): Target rectangle object.

    Returns:
        int: Area of the rectangle.
    """
    _, _, w, h = cv2.boundingRect(bounding_rectangle)
    return w * h


def get_digit_box(filename, top, bottom):
    """Find the box that includes the student ID for extracting the digits.

    Args:
        filename (str/pathlib.Path): the image of the ID page.
        top (float): Top of the cropping in `[0, 1]`, a percentage of
            the height of the image.
        bottom (bottom): Bottom of the cropping in `[0, 1`].  Its
            often helpful to crop in case there are other large boxes on
            the page, which might confuse the box-finder.

    Returns:
        None: in case of some sort of error, or
        numpy.ndarray: The processed image that includes the student
            ID digits.
    """
    front_image = cv2.imread(str(filename))

    top = math.floor(top * front_image.shape[0])
    bottom = math.ceil(bottom * front_image.shape[0])
    # Extract only the required portion of the image.
    cropped_image = front_image[:][top:bottom]

    # Process the image so as to find the contours.
    # Grey, Blur and Edging are standard processes for text detection.
    # TODO: I must make these better formatted.
    grey_image = cv2.cvtColor(cropped_image, cv2.COLOR_BGR2GRAY)
    blurred_image = cv2.GaussianBlur(grey_image, (5, 5), 0)
    edged_image = cv2.Canny(blurred_image, 50, 200, 255)

    # Find the contours to find the black bordered box.
    contours = cv2.findContours(
        edged_image.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    contour_lists = imutils.grab_contours(contours)
    sorted_contour_list = sorted(contour_lists, key=cv2.contourArea, reverse=True)
    id_box_contour = None

    for contour in sorted_contour_list:
        # Approximate the contour.
        perimeter = cv2.arcLength(contour, True)
        third_order_moment = cv2.approxPolyDP(contour, 0.02 * perimeter, True)

        if len(third_order_moment) == 4:
            id_box_contour = third_order_moment
            break

    # if whatever the above is doing failed, then abort
    if id_box_contour is None:
        return None

    # TODO: Why is this this not using edged_image
    # warped = four_point_transform(edged_image, id_box_contour.reshape(4, 2))
    output = four_point_transform(cropped_image, id_box_contour.reshape(4, 2))

    # TODO = add in some dimensions check = this box should not be tiny.
    if output.shape[0] < 32 or output.shape[1] < 32:
        return None

    # TODO: Remove magic number creation.
    # note that this width of 1250 is defined by the IDbox template
    new_width = int(output.shape[0] * 1250.0 / output.shape[1])
    scaled = cv2.resize(output, (1250, new_width), cv2.INTER_CUBIC)

    # the digit box numbers again come from the IDBox template and numerology
    ID_box = scaled[30:350, 355:1220]

    return ID_box


def get_digit_images(ID_box, num_digits):
    """Find the digit images and return them in a list.

    Args:
        ID_box (numpy.ndarray): Image containing the student ID.
        num_digits (int): Number of digits in the student ID.

    Returns:
        list: A list of numpy.ndarray which are the images for each digit.
            In case of errors, returns an empty list
    """

    processed_digits_images_list = []

    for digit_index in range(num_digits):

        # TODO: Maybe remove magical hackery.
        # extract the kth digit box. Some magical hackery / numerology here.
        digit1 = ID_box[0:100, digit_index * 109 + 5 : (digit_index + 1) * 109 - 5]

        # TODO: I think I could remove all of this.
        # Now some hackery to centre on the digit so closer to mnist dataset.
        # Find the contours and centre on the largest (by area).
        digit2 = cv2.GaussianBlur(digit1, (3, 3), 0)
        digit3 = cv2.Canny(digit2, 5, 255, 200)
        contours = cv2.findContours(
            digit3.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        contour_lists = imutils.grab_contours(contours)
        # sort by bounding box area
        sorted_contours = sorted(contour_lists, key=bounding_rect_area, reverse=True)
        # make sure we can find at least one contour
        if len(sorted_contours) == 0:
            # can't make a prediction so return empty list
            return []
        # get bounding rect of biggest contour
        bnd = cv2.boundingRect(sorted_contours[0])
        # put some padding around that rectangle
        pad = 10
        xl = max(0, bnd[1] - pad)
        yt = max(0, bnd[0] - pad)
        # grab the image - should be the digit.
        digit4 = digit2[xl : bnd[1] + bnd[3] + pad, yt : bnd[0] + bnd[2] + pad]
        # Do some clean-up by thresholding pixels
        digit5 = cv2.adaptiveThreshold(
            cv2.cvtColor(digit4, cv2.COLOR_BGR2GRAY),
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            31,
            1,
        )
        # and a little more - blur helps get rid of "dust" artifacts
        digit6 = cv2.blur(digit5, (3, 3))
        # now need to resize it to height or width =28 (depending on aspect ratio)
        # the "28" comes from mnist dataset, mnist digits are 28 x 28
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
        processed_digits_images_list.append(roi2)

    return processed_digits_images_list


def get_digit_prob(
    prediction_model, id_page_file, top, bottom, num_digits, *, debug=True
):
    """Return a list of probability predictions for the student ID digits on the cropped image.

    Args:
        prediction_model (sklearn.ensemble._forest.RandomForestClassifier): Prediction model.
        id_page_file (str/pathlib.Path): File path for the image which includes the ID box.
        top (float): Top boundary of image in `[0, 1]`.
        bottom (float): Bottom boundary of image in `[0, 1]`.
        num_digits (int): Number of digits in the student ID.

    Keyword Args:
        debug (bool): output the trimmed images into "debug_id_reader/"

    Returns:
        list: A list of lists of probabilities.  The outer list is over
            the 8 positions.  Inner lists have length 10: the probability
            that the digit is a 0, 1, 2, ..., 9.
            In case of errors it returns an empty list
    """
    id_page_file = Path(id_page_file)
    # Retrieve the box including the digits in a row.
    ID_box = get_digit_box(id_page_file, top, bottom)
    if ID_box is None:  # some sort of error finding the ID box
        print("Trouble finding the ID box")
        return []

    if debug:
        dbdir = Path("debug_id_reader")
        dbdir.mkdir(exist_ok=True)
        p = dbdir / f"idbox_{id_page_file.stem}.png"
        cv2.imwrite(str(p), ID_box)

    processed_digits_images = get_digit_images(ID_box, num_digits)
    if len(processed_digits_images) == 0:
        print("Trouble finding digits inside the ID box")
        return []

    if debug:
        for n, digit_image in enumerate(processed_digits_images):
            p = dbdir / f"digit_{id_page_file.stem}-pos{n}.png"
            cv2.imwrite(str(p), digit_image)
            # cv2.imshow("argh", digit_image)
            # cv2.waitKey(0)

    prob_lists = []
    for digit_image in processed_digits_images:
        # get it into format needed by model predictor
        # TODO: is this the same as just flattening:
        # digit_vector = digit_image.flatten()
        digit_vector = np.expand_dims(digit_image, 0)
        digit_vector = digit_vector.reshape((1, np.prod(digit_image.shape)))
        number_pred_prob = prediction_model.predict_proba(digit_vector)
        prob_lists.append(number_pred_prob[0])

    return prob_lists


def compute_probabilities(image_file_paths, top, bottom, num_digits):
    """Return a list of probabilities for digits for each test.

    Args:
        image_file_paths (dict): A dictionary including the paths of the images.
        top (float): Top boundary of image in `[0, 1]` where 0 is the
            top of the page and 1 is the bottom.
        bottom (float): Bottom boundary of image in `[0, 1]`.
        num_digits (int): Number of digits in the student ID.

    Returns:
        dict: A dictionary which involves the probabilities for each image file.
    """
    prediction_model = load_model()

    # Dictionary of test numbers their digit-probabilities
    probabilities = {}

    for testNumber, image_file in image_file_paths.items():
        prob_lists = get_digit_prob(
            prediction_model, image_file, top, bottom, num_digits
        )
        if len(prob_lists) == 0:
            print(
                f"Test{testNumber}: could not read digits, excluding from calculations"
            )
            continue
        elif len(prob_lists) != 8:
            print(f"Test{testNumber}: unexpectedly len={len(prob_lists)}: {prob_lists}")
            probabilities[testNumber] = prob_lists
        else:
            probabilities[testNumber] = prob_lists

    return probabilities
