# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Divy Patel

import cv2
import numpy as np
import json
from pathlib import Path
from sklearn.cluster import KMeans

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.conf import settings

from Identify.services import IDReaderService
from Identify.management.commands.plom_id import Command as PlomIDCommand
from Mark.services import MarkingTaskService


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
        idservice = IDReaderService()
        plom_id_command = PlomIDCommand()
        student_number_length = 8
        id_box_files = idservice.get_id_box_cmd((0.1, 0.9, 0.0, 1.0))
        count = 0

        for paper_num, id_box_file in id_box_files.items():
            id_page_file = Path(id_box_file)
            ID_box = plom_id_command.extract_and_resize_ID_box(id_page_file)
            if ID_box is None:
                self.stdout.write(
                    f"Trouble finding the ID box for paper_num: {paper_num}"
                )
                continue
            digit_images = plom_id_command.get_digit_images(
                ID_box, student_number_length
            )
            if len(digit_images) != student_number_length:
                self.stdout.write("Trouble finding digits inside the ID box")
                continue
            image = np.array(digit_images[digit_index])
            if image.flatten().shape[0] != 28 * 28:
                raise ValueError("Image is not 28x28")

            dir = Path(settings.MEDIA_ROOT / "digit_images")
            dir.mkdir(exist_ok=True)
            p = dir / f"paper_{paper_num}_digit_{digit_index}.png"
            cv2.imwrite(str(p), image)
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
        for p in dir.iterdir():
            if p.stem.split("_")[3] == f"{digit_index}":
                image = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
                image = image.flatten()
                images.append(image)
                paper_num = p.stem.split("_")[1]
                paper_nums.append(paper_num)

        kmeans = KMeans(n_clusters=10, random_state=0, n_init="auto")
        images_np = np.array(images)
        kmeans.fit(images_np)

        clustered_papers = []
        for label in range(10):
            curr_papers = []
            for i in range(len(images)):
                if kmeans.labels_[i] == label:
                    paper_num = paper_nums[i]
                    curr_papers.append(paper_num)
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
        if options["compute"]:
            self.compute_clusters(options["digit_index"])
        if options["tag"]:
            with open(settings.MEDIA_ROOT / "paper_clusters.json", "r") as f:
                paper_clusters = json.load(f)
            self.tag_question(paper_clusters, options["username"])
