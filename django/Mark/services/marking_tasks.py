# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

import json
import pathlib
import imghdr

from rest_framework.exceptions import ValidationError

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from Preparation.services import PQVMappingService
from Papers.services import SpecificationService
from Papers.models import Paper
from Rubrics.models import Rubric

from Mark.models import (
    MarkingTask,
    ClaimMarkingTask,
    SurrenderMarkingTask,
    MarkAction,
    Annotation,
    AnnotationImage,
)


class MarkingTaskService:
    """
    Functions for creating and modifying marking tasks.
    """

    def create_task(self, paper, question_number, user=None):
        """
        Create a marking task.

        Args:
            paper: a Paper instance, the test paper of the task
            question_number: int, the question of the task
            user: optional, User instance: user assigned to the task
        """

        pqvs = PQVMappingService()
        if not pqvs.is_there_a_pqv_map():
            raise RuntimeError("Server does not have a question-version map.")

        pqv_map = pqvs.get_pqv_map_dict()
        question_version = pqv_map[paper.paper_number][question_number]

        task_code = f"q{paper.paper_number:04}g{question_number}"

        the_task = MarkingTask(
            assigned_user=user,
            code=task_code,
            paper=paper,
            question_number=question_number,
            question_version=question_version,
        )
        the_task.save()
        return the_task

    def init_all_tasks(self):
        """
        Initialize all of the marking tasks for an entire exam, with null users.
        """

        spec_service = SpecificationService()
        if not spec_service.is_there_a_spec():
            raise RuntimeError("The server does not have a spec.")

        spec = spec_service.get_the_spec()
        n_questions = spec["numberOfQuestions"]

        all_papers = Paper.objects.all()
        all_papers = all_papers.order_by("paper_number")[
            :10
        ]  # TODO: just the first ten!
        for p in all_papers:
            for i in range(1, n_questions + 1):
                self.create_task(p, i)

    def get_marking_progress(self, version, question):
        """Send back current marking progress counts to the client.

        Args:
            question (int)
            version (int)

        Returns:
            tuple: two integers, first the number of marked papers for
            this question/version and the total number of papers for
            this question/version.
        """
        try:
            completed = MarkingTask.objects.filter(
                status="complete", question_number=question, question_version=version
            )
            total = MarkingTask.objects.get(
                question_number=question, question_version=version
            )
        except MarkingTask.DoesNotExist:
            return (0, 0)

        return (len(completed), len(total))

    def get_task(self, paper_number, question_number):
        """
        Get a marking task from its paper number and question number.

        Args:
            paper_number: int
            question_number: int
        """
        paper = Paper.objects.get(paper_number=paper_number)
        return MarkingTask.objects.get(paper=paper, question_number=question_number)

    def unpack_code(self, code):
        """
        Return a tuple of (paper_number, question_number)
        from a task code string.

        Args:
            code (str): a task code, e.g. q0001g1
        """

        assert len(code) == len("q0000g0")
        paper_number = int(code[1:5])
        question_number = int(code[-1])

        return paper_number, question_number

    def get_task_from_code(self, code):
        """
        Get a marking task from its code.

        Arg:
            code: str, a unique string that includes the paper number and question number.
        """

        paper_number, question_number = self.unpack_code(code)
        return self.get_task(paper_number, question_number)

    def get_first_available_task(self, question=None, version=None):
        """
        Return the first marking task with a 'todo' status.

        Args:
            question (optional): int, requested question number
            version (optional): int, requested version number
        """

        available = MarkingTask.objects.filter(status="todo")
        available = available.order_by("paper__paper_number")

        if question:
            available = available.filter(question_number=question)

        if version:
            available = available.filter(question_version=version)

        return available.first()

    def are_there_tasks(self):
        """
        Return True if there is at least one marking task in the database.
        """

        return MarkingTask.objects.exists()

    def assign_task_to_user(self, user, task):
        """
        Write a user to a marking task and update its status. Also creates
        and saves a ClaimMarkingTask action instance.

        Args:
            user: reference to a User instance
            task: reference to a MarkingTask instance
        """

        if task.status == "out":
            raise RuntimeError("Task is currently assigned.")

        action = ClaimMarkingTask(
            user=user,
            task=task,
        )
        action.save()

        task.assigned_user = user
        task.status = "out"
        task.save()

    def surrender_task(self, user, task):
        """
        Remove a user from a marking task, set its status to 'todo', and
        save the action to the database.

        Args:
            user: reference to a User instance
            task: reference to a MarkingTask instance
        """

        task.assigned_user = None
        task.status = "todo"
        task.save()

        action = SurrenderMarkingTask(
            user=user,
            task=task,
        )
        action.save()

    def surrender_all_tasks(self, user):
        """
        Surrender all of the tasks currently assigned to the user.

        Args:
            user: reference to a User instance
        """

        user_tasks = MarkingTask.objects.filter(assigned_user=user, status="out")
        for task in user_tasks:
            self.surrender_task(user, task)

    def user_can_update_task(self, user, code):
        """
        Return true if a user is allowed to update a certain task, false otherwise.

        TODO: should be possible to remove the "assigned user" and "status" fields
        and infer both from querying ClaimTask and MarkAction instances.

        Args:
            user: reference to a User instance
            code: (str) task code
        """

        the_task = self.get_task_from_code(code)
        if the_task.assigned_user and the_task.assigned_user != user:
            return False

        if the_task.status != "out" and the_task.status != "complete":
            return False

        return True

    def get_latest_claim(self, user, code):
        """
        Get the latest ClaimMarkingTask instance for a user and task.
        """

        task = self.get_task_from_code(code)
        claims = ClaimMarkingTask.objects.filter(user=user, task=task)
        latest_claim = claims.order_by("time").first()
        return latest_claim

    def mark_task(self, user, code, score, image, data):
        """
        Save a user's marking attempt to the database.
        """

        claim = self.get_latest_claim(user, code)
        editions_so_far = len(MarkAction.objects.filter(claim_action=claim))
        annotation = Annotation(
            edition=editions_so_far + 1,
            score=score,
            image=image,
            annotation_data=data,
        )
        annotation.save()

        action = MarkAction(
            claim_action=claim,
            annotation=annotation,
            user=user,
            task=claim.task,
        )
        action.save()

    def get_n_marked_tasks(self):
        """
        Return the number of marking tasks that are completed.
        """

        return len(MarkingTask.objects.filter(status="complete"))

    def get_n_total_tasks(self):
        """
        Return the total number of tasks in the database.
        """

        return len(MarkingTask.objects.all())

    def save_annotation_image(self, md5sum, annot_img):
        """
        Save an annotation image to disk and the database.

        Args:
            md5sum: (str) the annotation image's hash.
            annot_img: (InMemoryUploadedFlie) the annotation image file.
        """

        imgtype = imghdr.what(None, h=annot_img.read())
        if imgtype not in ["png", "jpg", "jpeg"]:
            raise ValidationError(
                f"Unsupported image type: expected png or jpg, got {imgtype}"
            )
        annot_img.seek(0)

        imgs_folder = settings.BASE_DIR / "media" / "annotation_images"
        imgs_folder.mkdir(exist_ok=True)
        img = AnnotationImage(hash=md5sum)
        img.save()

        img_path = imgs_folder / f"annotation_{img.pk}.png"
        img.path = img_path
        if img_path.exists():
            raise FileExistsError(
                f"Annotation image with public key {img.pk} already exists."
            )

        with open(img_path, "wb") as saved_annot_image:
            for chunk in annot_img.chunks():
                saved_annot_image.write(chunk)
        img.save()

        return img

    def validate_and_clean_marking_data(self, user, code, data, plomfile):
        """
        Validate the incoming marking data.

        Args:
            user: reference to a User instance.
            code (str): key of the associated task.
            data (dict): information about the mark, rubrics, and annotation images.
            plomfile (str): a JSON field representing annotation data.

        Returns:
            cleaned_data (dict): cleaned request data
            annot_data (dict): annotation-image data parsed from a JSON string.
        """

        annot_data = json.loads(plomfile)
        cleaned_data = {}

        if not self.user_can_update_task(user, code):
            raise RuntimeError("User cannot update task.")

        try:
            for val in ["pg", "ver", "score", "mtime"]:
                elem = data[val][0]
                cleaned_data[val] = int(elem)
        except IndexError:
            raise ValidationError(f"Multiple values for '{val}', expected 1.")
        except ValueError:
            raise ValidationError(f"Could not cast {val} as int: {elem}")

        if type(data["rubrics"]) == str:
            rubrics = [data["rubrics"]]
        else:
            rubrics = data["rubrics"]

        cleaned_data["rubrics"] = []
        for rubric_key in rubrics:
            try:
                rubric = Rubric.objects.get(key=rubric_key)
            except ObjectDoesNotExist:
                raise ValidationError(f"Invalid rubric key: {rubric_key}")
            cleaned_data["rubrics"] = [rubric]

        src_img_data = annot_data["base_images"]
        for image_data in src_img_data:
            img_path = pathlib.Path(image_data["server_path"])
            if not img_path.exists():
                raise ValidationError("Invalid original-image in request.")

        return cleaned_data, annot_data
