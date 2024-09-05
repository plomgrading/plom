# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Divy Patel
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2024 Andrew Rechnitzer

from __future__ import annotations

import json
from pathlib import Path

import cv2 as cv
import numpy as np
from sklearn.cluster import KMeans

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.conf import settings

from Identify.services import IDBoxProcessorService
from Mark.services import MarkingTaskService
from Papers.services import SpecificationService
from Rectangles.services import RectangleExtractor


class Command(BaseCommand):
    """Command tool for clustering and tagging questions.

    Currently only does clustering on student id digits and tags the first question.

    python3 manage.py cluster_tag_id_digits [digit_index] [username]
    """

    help = """Cluster and tag questions based id digits."""

    def add_arguments(self, parser):
        parser.add_argument(
            "digit_index", type=int, help="Digit index to cluster on, range: [0-7]"
        )
        parser.add_argument("username", type=str, help="Username")
        parser.add_argument(
            "--get-digits",
            action="store_true",
            help="Extract the digits from database idbox images and store them at media/id_digits",
        )
        parser.add_argument(
            "--compute",
            action="store_true",
            help="Cluster the digits and store the clusters at media/paper_clusters.json",
        )
        parser.add_argument(
            "--tag",
            action="store_true",
            help="Tag the first question of each paper with the cluster number according to the media/paper_clusters.json file",
        )

    def get_digits(self, digit_index) -> None:
        """Extract the digits from database idbox images and store them at media/id_digits.

        Args:
            digit_index (int): Digit index to extract, range: [0-7]
        """
        # instantiate the rectangle extractor for version 1 and the id-page.
        id_page_number = SpecificationService.get_id_page_number()
        rex = RectangleExtractor(1, id_page_number)
        # now get the largest rectangle from big region on the ref-image of page
        idbox_location_rectangle = rex.get_largest_rectangle_contour(
            {
                "left_f": 0.1,
                "right_f": 0.9,
                "top_f": 0.1,
                "bottom_f": 0.9,
            }
        )
        if idbox_location_rectangle is None:
            self.stdout.write("Trouble finding the ID box on reference image")
            return
        # now that we have the IDbox rectangle, we can use existing services to
        # extract them
        id_box_image_dict = IDBoxProcessorService().save_all_id_boxes(
            [
                idbox_location_rectangle[X]
                for X in ["left_f", "top_f", "right_f", "bottom_f"]
            ]
        )
        # now extract the digits from those boxes.

        student_number_length = 8
        count = 0

        dir = Path(settings.MEDIA_ROOT / "digit_images")
        dir.mkdir(exist_ok=True)

        for paper_num, id_box_file in id_box_image_dict.items():
            id_page_file = Path(id_box_file)
            ID_box: (
                cv.typing.MatLike | None
            ) = IDBoxProcessorService().resize_ID_box_and_extract_digit_strip(
                id_page_file
            )
            if ID_box is None:
                self.stdout.write(f"Trouble finding the ID box on paper {paper_num}")
                continue
            digit_images = IDBoxProcessorService().get_digit_images(
                ID_box, student_number_length
            )
            if len(digit_images) != student_number_length:
                self.stdout.write(
                    f"Trouble finding digits inside the ID box on paper {paper_num}"
                )
                continue
            image = np.array(digit_images[digit_index])
            if image.flatten().shape[0] != 28 * 28:
                raise ValueError("Image is not 28x28")

            p = dir / f"paper_{paper_num}_digit_{digit_index}.png"
            cv.imwrite(str(p), image)
            count += 1

        self.stdout.write(f"Done extracting. Extracted {count} digits")

    def compute_clusters(self, digit_index) -> None:
        """Cluster the digits and store the clusters at media/paper_clusters.json.

        Requires:
            The digits have already been extracted and stored at media/digit_images.
            The file names to be of the format paper_{paper_num}_digit_{digit_index}.png
        """
        images = []
        paper_nums = []

        # load images from media/digit_images
        dir = Path(settings.MEDIA_ROOT / "digit_images")
        dir.mkdir(exist_ok=True)
        for p in dir.iterdir():
            if p.stem.split("_")[3] == f"{digit_index}":
                image = cv.imread(str(p), cv.IMREAD_GRAYSCALE)
                image = image.flatten()
                images.append(image)
                paper_num = p.stem.split("_")[1]
                paper_nums.append(paper_num)

        kmeans = KMeans(n_clusters=10, random_state=0, n_init="auto")
        kmeans.fit(np.array(images))

        clustered_papers = []
        for label in range(10):
            curr_papers = []
            for i in range(len(images)):
                if kmeans.labels_[i] == label:
                    paper_num = paper_nums[i]
                    curr_papers.append(paper_num)
            curr_papers.sort()
            clustered_papers.append(curr_papers)

        with open(settings.MEDIA_ROOT / "paper_clusters.json", "w") as f:
            json.dump(clustered_papers, f)

        self.stdout.write("Done clustering")

    def tag_question(self, clusters, username) -> None:
        """Tag the first question."""
        ms = MarkingTaskService()
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(f"User {username} does not exist")
            return
        for i in range(len(clusters)):
            if len(clusters[i]) > 0:
                for paper_num in clusters[i]:
                    code = f"q{paper_num}g1"
                    text = f"cluster_{i}"
                    try:
                        ms.add_tag_text_from_task_code(text, code, user)
                    except RuntimeError:
                        print(f"{code} does not exist")

        self.stdout.write("Done tagging")

    def handle(self, *args, **options):
        if options["get_digits"]:
            self.get_digits(options["digit_index"])
        elif options["compute"]:
            self.compute_clusters(options["digit_index"])
        elif options["tag"]:
            with open(settings.MEDIA_ROOT / "paper_clusters.json", "r") as f:
                paper_clusters = json.load(f)
            self.tag_question(paper_clusters, options["username"])
        else:
            raise CommandError("You must specify one or more flags")
