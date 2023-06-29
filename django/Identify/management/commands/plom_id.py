# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2020-2023 Colin B. Macdonald
# Copyright (c) 2022 Edith Coates
# Copyright (C) 2023 Natalie Balashov

import cv2
import imutils
from imutils.perspective import four_point_transform
import json
import numpy as np
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from plom.idreader.model_utils import download_or_train_model, load_model
from Identify.services import IDReaderService


class Command(BaseCommand):
    """Management command with subcommands for extracting the ID box and doing ID digit reading.

    python3 manage.py plom_id idbox (top) (bottom) (left) (right)
    python3 manage.py plom_id idreader
    python3 manage.py plom_id testing
    """

    help = "Extract the ID box from all papers."

    def testing(self):
        test_image = Path("test_image.png")
        largest_box = self.get_largest_box(test_image)
        cv2.imwrite("largest_box_image.png", largest_box)
        ID_box = self.extract_and_resize_ID_box(test_image)
        cv2.imwrite("output_image.png", ID_box)
        digits = self.extract_and_resize_ID_box(test_image)
        cv2.imwrite("output_image.png", ID_box)

    def get_id_box(self, top, bottom, left, right):
        idservice = IDReaderService()
        box = (top, bottom, left, right)
        if any(x is None for x in box):
            if all(x is None for x in box):
                box = None
            else:
                raise CommandError("If you provide one dimension you must provide all")
        try:
            idservice.get_id_box_cmd(box)
            self.stdout.write("Extracted the ID box from all known ID pages.")
        except ValueError as err:
            raise CommandError(err)

    def run_id_reader(self):
        try:
            self.stdout.write("Firing up the auto id reader.")
            self.stdout.write(
                "Ensuring we have the model: download if not, or train if cannot download..."
            )
            download_or_train_model()

            self.stdout.write("Extracting ID boxes...")
            idservice = IDReaderService()
            # id_box_files = idservice.get_id_box_cmd(None)
            id_box_files = idservice.get_id_box_cmd((0.1, 0.8, 0.02, 0.98))

            self.stdout.write("Computing probabilities for student ID digits.")
            student_number_length = 8
            probs = self.compute_probabilities(id_box_files, student_number_length)

            probs = {k: [x.tolist() for x in v] for k, v in probs.items()}
            with open(settings.MEDIA_ROOT / "id_prob_heatmaps.json", "w") as fh:
                json.dump(probs, fh, indent="  ")
            self.stdout.write(
                "Ran the ID reader and saved probabilities to a JSON file."
            )
        except ValueError as err:
            raise CommandError(err)

    def bounding_rect_area(self, bounding_rectangle):
        """Return the area of the rectangle, useful for sorting by area of bounding rect.

        Args:
            bounding_rectangle (list): Target rectangle object.

        Returns:
            int: Area of the rectangle.
        """
        _, _, w, h = cv2.boundingRect(bounding_rectangle)
        return w * h

    def get_largest_box(self, filename):
        """Helper function for extracting the largest box from an image.

        Args:
            filename (str/pathlib.Path): the image where the largest box is extracted from.

        Returns:
            numpy.ndarray | None: the image, cropped to only include the contour region
            or None if an error occurred.
        """
        src_image = cv2.imread(str(filename))
        # Process the image so as to find the contours.
        # Grey, Blur and Edging are standard processes for text detection.
        grey_image = cv2.cvtColor(src_image, cv2.COLOR_BGR2GRAY)
        blurred_image = cv2.GaussianBlur(grey_image, (5, 5), 0)
        edged_image = cv2.Canny(blurred_image, 50, 200, 255)

        contours = cv2.findContours(
            edged_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        contour_lists = imutils.grab_contours(contours)
        sorted_contour_list = sorted(contour_lists, key=cv2.contourArea, reverse=True)

        for contour in sorted_contour_list:
            perimeter = cv2.arcLength(contour, True)
            # Approximate the contour
            third_order_moment = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
            # check that the contour is a quadrilateral
            if len(third_order_moment) == 4:
                box_contour = third_order_moment
                break
        if box_contour is not None:
            return four_point_transform(src_image, box_contour.reshape(4, 2))

    def extract_and_resize_ID_box(self, filename):
        template_id_box_width = 1250
        id_box = self.get_largest_box(filename)
        height, width, _ = id_box.shape
        if height < 32 or width < 32:  # id_box is too small
            return None
        # scale height to retain aspect ratio of image
        new_height = int(template_id_box_width * height / width)
        scaled_id_box = cv2.resize(
            id_box, (template_id_box_width, new_height), cv2.INTER_CUBIC
        )
        # extract the top strip of the IDBox template
        # which only contains the digits
        return scaled_id_box[25:130, 355:1230]

    def get_digit_images(self, ID_box, num_digits):
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
            height, width, _ = ID_box.shape
            digit_width = width / num_digits
            print(digit_width)
            left = digit_index * 109 + 5
            right = (digit_index + 1) * 109 - 5
            print(f"{left} to {right}")
            digit1 = ID_box[0:height, left:right]
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
            sorted_contours = sorted(
                contour_lists, key=self.bounding_rect_area, reverse=True
            )
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
                roi,
                px,
                28 - w - px,
                py,
                28 - h - py,
                cv2.BORDER_CONSTANT,
                value=[0, 0, 0],
            )
            processed_digits_images_list.append(roi2)
        return processed_digits_images_list

    def get_digit_prob(self, prediction_model, id_page_file, num_digits, *, debug=True):
        """Return a list of probability predictions for the student ID digits on the cropped image.

        Args:
            prediction_model (sklearn.ensemble._forest.RandomForestClassifier): Prediction model.
            id_page_file (str/pathlib.Path): File path for the image which includes the ID box.
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
        ID_box = self.get_digit_box(id_page_file)
        if ID_box is None:
            self.stdout.write("Trouble finding the ID box")
            return []
        if debug:
            dbdir = Path(settings.MEDIA_ROOT / "debug_id_reader")
            dbdir.mkdir(exist_ok=True)
            p = dbdir / f"idbox_{id_page_file.stem}.png"
            cv2.imwrite(str(p), ID_box)
        processed_digits_images = self.get_digit_images(ID_box, num_digits)
        if len(processed_digits_images) == 0:
            self.stdout.write("Trouble finding digits inside the ID box")
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

    def compute_probabilities(self, image_file_paths, num_digits):
        """Return probabilities for digits for each test.

        Args:
            image_file_paths (dict): A dictionary including the paths of the images.

        Returns:
            dict: A dictionary which involves the probabilities for each image file.
        """
        prediction_model = load_model()
        probabilities = {}
        for testNumber, image_file in image_file_paths.items():
            prob_lists = self.get_digit_prob(prediction_model, image_file, num_digits)
            if len(prob_lists) == 0:
                self.stdout.write(
                    f"Test{testNumber}: could not read digits, excluding from calculations"
                )
                continue
            elif len(prob_lists) != 8:
                self.stdout.write(
                    f"Test{testNumber}: unexpectedly len={len(prob_lists)}: {prob_lists}"
                )
                probabilities[testNumber] = prob_lists
            else:
                probabilities[testNumber] = prob_lists
        return probabilities

    def add_arguments(self, parser):
        sp = parser.add_subparsers(
            dest="command",
            description="ID reading",
        )
        sp_box = sp.add_parser(
            "idbox", help="Extract a rectangular region from all pushed ID pages."
        )
        sp_box.add_argument(
            "top",
            type=float,
            help="top bound of rectangle to extract",
            default=None,
            nargs="?",
        )
        sp_box.add_argument(
            "bottom",
            type=float,
            help="bottom bound of rectangle to extract",
            default=None,
            nargs="?",
        )
        sp_box.add_argument(
            "left",
            type=float,
            help="left bound of rectangle to extract",
            default=None,
            nargs="?",
        )
        sp_box.add_argument(
            "right",
            type=float,
            help="right bound of rectangle to extract",
            default=None,
            nargs="?",
        )
        sp.add_parser(
            "idreader",
            help="Run existing ID reading tools.",
            description="""
                This command tries to find the student ID boxes on each ID page.
                When those are successfully read, each digit is passed to a
                machine learning model to produce a "heat map" of which digit it
                might be.
                To make predictions based on those results, see
                `python manage.py auto_ider`.
            """,
        )
        sp.add_parser("testing")

    def handle(self, *args, **options):
        if options["command"] == "idbox":
            self.get_id_box(
                options["top"], options["bottom"], options["left"], options["right"]
            )
        elif options["command"] == "idreader":
            self.run_id_reader()
        elif options["command"] == "testing":
            self.testing()
        else:
            self.print_help("manage.py", "plom_id")
