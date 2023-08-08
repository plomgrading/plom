# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

import csv
import cv2 as cv
import numpy as np
from tqdm import tqdm

from django.core.management.base import BaseCommand, CommandError

from Papers.models import QuestionPage, Specification


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
            "--q_n", nargs=1, type=int, required=True, help="The question number (int)"
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
        question_number = options["q_n"]
        question_version = options["q_v"]
        reverse = options["reverse"]
        spec = Specification.load().spec_dict

        if question_number is None:
            raise CommandError("Please provide one question number.")

        if question_version is None:
            raise CommandError("Please provide one question version.")

        question_number = question_number[0]
        question_version = question_version[0]

        q_range = range(1, spec["numberOfQuestions"] + 1)
        v_range = range(0, spec["numberOfVersions"] + 1)

        if question_number not in q_range:
            raise CommandError(
                f"Question {question_number} out of valid range. Valid range: {list(q_range)}."
            )

        if question_version not in v_range:
            raise CommandError(
                f"Version {question_version} out of valid range. Valid range: {list(v_range)}."
            )

        pages = QuestionPage.objects.filter(
            question_number=question_number
        ).select_related("image", "paper")
        pages = pages.filter(image__isnull=False)

        if question_version != 0:
            pages = pages.filter(version=question_version)

        count = pages.count()
        print(f"Found {count} tasks. Getting images...")

        def _crop_img(img, scale=1.0):
            center_x, center_y = img.shape[1] / 2, img.shape[0] / 2
            width_scaled, height_scaled = img.shape[1] * scale, img.shape[0] * scale
            left_x, right_x = center_x - width_scaled / 2, center_x + width_scaled / 2
            top_y, bottom_y = center_y - height_scaled / 2, center_y + height_scaled / 2
            img_cropped = img[int(top_y) : int(bottom_y), int(left_x) : int(right_x)]
            return img_cropped

        def _set_aspect_ratio(img, scale=1.0):
            width, height = img.shape[1], img.shape[0]
            if width > height:
                dim = (int(1600 * scale), int(1200 * scale))
            else:
                dim = (int(1200 * scale), int(1600 * scale))
            img = cv.resize(img, dsize=dim)
            return img

        imgs_by_th_list = {}

        for page in tqdm(pages, desc="Analyzing pages"):
            image = cv.imread(page.image.image_file.path)
            crop = _set_aspect_ratio(_crop_img(image, scale=0.8), scale=0.2)
            grey = cv.cvtColor(crop, cv.COLOR_BGR2GRAY)
            th = cv.adaptiveThreshold(
                grey, 255, cv.ADAPTIVE_THRESH_GAUSSIAN_C, cv.THRESH_BINARY, 11, 2
            )
            if (
                imgs_by_th_list.get((page.paper.paper_number, page.question_number))
                is None
            ):
                imgs_by_th_list[(page.paper.paper_number, page.question_number)] = []
            imgs_by_th_list[(page.paper.paper_number, page.question_number)].append(
                np.sum(th)
            )
            # paper_list = [19,14]  # <-- put pages you want to look at here
            # paper_num = page.paper.paper_number
            # if paper_num in paper_list:
            #     cv.imwrite(f"TEST_ORIG_{paper_num}.jpg", image)
            #     cv.imwrite(f"TEST_THRESH_{paper_num}.jpg", th)

        imgs_by_th_sum = {}

        min = -1
        max = 0

        for (paper_number, question_num), list_of_th in imgs_by_th_list.items():
            avg = np.average(list_of_th)
            imgs_by_th_sum[(paper_number, question_num)] = avg

            if avg > max:
                max = avg
            if avg < min or min == -1:
                min = avg
            if min == -1:
                min = avg

        min_out, max_out = 1000, 0
        if reverse:
            min_out, max_out = max_out, min_out

        mapped = {}
        for (paper_number, question_num), th_sum in imgs_by_th_sum.items():
            mapped[(paper_number, question_num)] = np.interp(
                th_sum, (min, max), (min_out, max_out)
            )

        sorted_imgs = dict(sorted(mapped.items(), key=lambda item: item[1]))

        filename = f"q{question_number}_"
        if question_version != 0:
            filename += f"v{question_version}_"
        if reverse:
            filename += "reverse_"
        filename += "sorted.csv"

        with open(filename, "w") as f:
            writer = csv.writer(f)
            writer.writerow(["Paper Number", "Question Number", "Priority Value"])
            for (paper_number, question_number), th_sum in sorted_imgs.items():
                writer.writerow([paper_number, question_number, th_sum])

        print(f"Saved to {filename}")
