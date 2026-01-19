# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023-2026 Colin B. Macdonald
# Copyright (C) 2025 Andrew Rechnitzer

import csv

import cv2 as cv
import numpy as np
from tqdm import tqdm

from django.core.management.base import BaseCommand, CommandError

# TODO: why model here?  Maybe there is some service to talk to instead?
from plom_server.Papers.models import FixedPage
from plom_server.Papers.services import SpecificationService

from ...services import TaskOrderService


class Command(BaseCommand):
    help = """
        Sorts the tasks by the amount written on the page image.

        The sorted tasks are saved as a csv file in the current
        directory. By default, the tasks are assigned priority
        values with the pages that have the most written on them
        getting the highest priority value.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--q_n",
            nargs=1,
            type=int,
            required=True,
            help="The question index number (int)",
        )
        parser.add_argument(
            "--q_v",
            nargs=1,
            type=int,
            default=[0],
            help="The question version (optional int)",
        )
        parser.add_argument(
            "--reverse",
            action="store_true",
            help="Reverse the ordering of the tasks (optional bool)",
        )

    def handle(self, *args, **options):
        question_index = options["q_n"]
        question_version = options["q_v"]
        reverse = options["reverse"]

        if question_index is None:
            raise CommandError("Please provide one question index number.")

        if question_version is None:
            raise CommandError("Please provide one question version.")

        question_index = question_index[0]
        question_version = question_version[0]

        q_idx_range = SpecificationService.get_question_indices()
        if question_index not in q_idx_range:
            raise CommandError(
                f"Question index {question_index} out of valid range."
                f" Valid range: {q_idx_range}."
            )

        # zero has special meaning here
        v_range = range(0, SpecificationService.get_n_versions() + 1)
        if question_version not in v_range:
            raise CommandError(
                f"Version {question_version} out of valid range. Valid range: {list(v_range)}."
            )

        pages = FixedPage.objects.filter(
            page_type=FixedPage.QUESTIONPAGE, question_index=question_index
        ).select_related("image", "paper")
        pages = pages.filter(image__isnull=False)

        if question_version != 0:
            pages = pages.filter(version=question_version)

        count = pages.count()
        print(f"Found {count} tasks. Getting images...")

        def _crop_img(img, scale=1.0):
            """Crops the image from the center by the given scale.

            Args:
                img (np.array): The image to crop.
                scale (float, optional): The scale to crop by. Defaults
                    to 1.0 which means no cropping.

            Returns:
                np.array: The cropped image.
            """
            assert scale <= 1.0 and scale > 0.0, "Scale must be between 0 and 1"
            center_x, center_y = img.shape[1] / 2, img.shape[0] / 2
            width_scaled, height_scaled = img.shape[1] * scale, img.shape[0] * scale
            left_x, right_x = center_x - width_scaled / 2, center_x + width_scaled / 2
            top_y, bottom_y = center_y - height_scaled / 2, center_y + height_scaled / 2
            img_cropped = img[int(top_y) : int(bottom_y), int(left_x) : int(right_x)]
            return img_cropped

        def _set_aspect_ratio(img, scale=1.0):
            """Sets the aspect ratio of the image to 4:3 and resizes it.

            Args:
                img (np.array): The image to set the aspect ratio of.
                scale (float, optional): The scale to resize by. Defaults
                    to 1.0 which means no resizing.

            Returns:
                np.array: The image with the aspect ratio set.
            """
            width, height = img.shape[1], img.shape[0]
            if width > height:
                dim = (int(1600 * scale), int(1200 * scale))
            else:
                dim = (int(1200 * scale), int(1600 * scale))
            img = cv.resize(img, dsize=dim)
            return img

        imgs_threshold_list = {}

        for page in tqdm(pages, desc="Analyzing pages"):
            # get the image
            image = cv.imread(page.image.baseimage.image_file.path)
            cropped_im = _set_aspect_ratio(
                _crop_img(image, scale=0.8),  # crop to keep center 80% of image
                scale=0.2,  # resize to 20% of original size
            )
            # greyscale image
            greyscale_im = cv.cvtColor(cropped_im, cv.COLOR_BGR2GRAY)
            # threshold image dynamically so that the background is white
            # regardless of lighting conditions
            threshold_im = cv.adaptiveThreshold(
                greyscale_im,
                maxValue=255,
                adaptiveMethod=cv.ADAPTIVE_THRESH_GAUSSIAN_C,
                thresholdType=cv.THRESH_BINARY,
                blockSize=11,
                C=2,
            )

            paper_num = page.paper.paper_number
            question_idx = page.question_index

            # add the sum of the pixels in the thresholded image to a list corresponding
            # to the paper and question index (to handle multiple pages for the same question)
            if imgs_threshold_list.get((paper_num, question_idx)) is None:
                imgs_threshold_list[(paper_num, question_idx)] = []
            imgs_threshold_list[(paper_num, question_idx)].append(np.sum(threshold_im))

            # Uncomment to save images for debugging
            # paper_list = []  # <-- put pages you want to look at here
            # if paper_num in paper_list:
            #     cv.imwrite(f"TEST_ORIG_{paper_num}.jpg", image)
            #     cv.imwrite(f"TEST_THRESH_{paper_num}.jpg", threshold_im)

        # get the average of the pixel sums for each paper and question index
        pixel_avgs = {}
        for (paper_number, question_idx), list_of_th in imgs_threshold_list.items():
            # avereage of the pixel sums for all pages of the same question
            avg = np.average(list_of_th)
            pixel_avgs[(paper_number, question_idx)] = avg

        sorted_imgs = dict(
            sorted(pixel_avgs.items(), key=lambda item: item[1], reverse=reverse),
        )

        filename = f"qi{question_index}_"
        if question_version != 0:
            filename += f"v{question_version}_"
        if reverse:
            filename += "reverse_"
        filename += "sorted.csv"

        keys = TaskOrderService.get_csv_header()
        assert "Paper Number" in keys
        assert "Question Index" in keys
        assert "Priority" in keys
        with open(filename, "w") as f:
            w = csv.DictWriter(f, keys)
            w.writeheader()
            for i, (k, th_sum) in enumerate(sorted_imgs.items()):
                paper_number, question_idx = k  # unpack key
                # TODO: could save grey value th_sum in new column...
                w.writerow(
                    {
                        "Paper Number": paper_number,
                        "Question Index": question_idx,
                        "Priority": i,
                    }
                )

        print(f"Saved to {filename}")
