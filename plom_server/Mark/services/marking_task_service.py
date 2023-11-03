# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Natalie Balashov

import json
import pathlib
import random
from typing import Tuple, Union

from rest_framework.exceptions import ValidationError

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db.models import QuerySet
from django.db import transaction

from plom import is_valid_tag_text

from Preparation.services import PQVMappingService
from Papers.services import ImageBundleService
from Papers.models import Paper
from Rubrics.models import Rubric

from . import marking_priority, mark_task
from ..models import (
    MarkingTask,
    MarkingTaskTag,
    MarkingTaskPriority,
    Annotation,
)


class MarkingTaskService:
    """Functions for creating and modifying marking tasks."""

    @transaction.atomic
    def create_task(self, paper, question_number, user=None):
        """Create a marking task.

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

        # mark other tasks with this code as 'out of date'
        # and set the assigned user to None
        previous_tasks = MarkingTask.objects.filter(code=task_code)
        for old_task in previous_tasks.exclude(status=MarkingTask.OUT_OF_DATE):
            old_task.status = MarkingTask.OUT_OF_DATE
            old_task.assigned_user = None
            old_task.save()

        # get priority of latest old task to assign to new task, but
        # if no previous priority exists, set a new value based on the current strategy
        latest_old_task = previous_tasks.order_by("-time").first()
        if latest_old_task:
            priority = latest_old_task.marking_priority
        else:
            strategy = marking_priority.get_mark_priority_strategy()
            if strategy == MarkingTaskPriority.PAPER_NUMBER:
                priority = Paper.objects.count() - paper.paper_number
            else:
                priority = random.randint(0, 1000)

        the_task = MarkingTask(
            assigned_user=user,
            code=task_code,
            paper=paper,
            question_number=question_number,
            question_version=question_version,
            marking_priority=priority,
        )
        the_task.save()
        return the_task

    def get_marking_progress(self, question: int, version: int) -> Tuple[int, int]:
        """Send back current marking progress counts to the client.

        Args:
            question (int)
            version (int)

        Returns:
            two integers, first the number of marked papers for
            this question/version and the total number of papers for
            this question/version.
        """
        try:
            completed = MarkingTask.objects.filter(
                status=MarkingTask.COMPLETE,
                question_number=question,
                question_version=version,
            )
            total = MarkingTask.objects.filter(
                question_number=question, question_version=version
            ).exclude(status=MarkingTask.OUT_OF_DATE)
        except MarkingTask.DoesNotExist:
            return (0, 0)

        return (completed.count(), total.count())

    def get_task_from_code(self, code: str) -> MarkingTask:
        """Get a marking task from its code.

        Args:
            code: a unique string that includes the paper number and question number.

        Returns:
            The marking task object the matches the code.

        Raises:
            ValueError: invalid code.
            RuntimeError: code valid but task does not exist.
        """
        try:
            paper_number, question_number = mark_task.unpack_code(code)
        except AssertionError as e:
            raise ValueError(f"{code} is not a valid task code.") from e
        try:
            return mark_task.get_latest_task(paper_number, question_number)
        except ObjectDoesNotExist as e:
            raise RuntimeError(e) from e

    def get_user_tasks(
        self, user, question=None, version=None
    ) -> QuerySet[MarkingTask]:
        """Get all the marking tasks that are assigned to this user.

        Args:
            user: User instance
            question (optional): int, the question number
            version (optional): int, the version number

        Returns:
            Marking tasks assigned to user
        """
        tasks = MarkingTask.objects.filter(assigned_user=user)
        if question:
            tasks = tasks.filter(question_number=question)
        if version:
            tasks = tasks.filter(question_version=version)

        return tasks

    def get_tasks_from_question_with_annotation(
        self, question: int, version: int
    ) -> QuerySet[MarkingTask]:
        """Get all the marking tasks for this question/version.

        Args:
            question: int, the question number
            version: int, the version number. If version == 0, then all versions are returned.

        Returns:
            A PolymorphicQuerySet of tasks

        Raises:
            None expected
        """
        marking_tasks = MarkingTask.objects.filter(
            question_number=question, status=MarkingTask.COMPLETE
        )
        if version != 0:
            marking_tasks = marking_tasks.filter(question_version=version)
        return marking_tasks

    def get_latest_annotations_from_complete_marking_tasks(
        self,
    ) -> QuerySet[Annotation]:
        """Returns the latest annotations from all tasks that are complete."""
        return Annotation.objects.filter(
            markingtask__status=MarkingTask.COMPLETE
        ).filter(markingtask__latest_annotation__isnull=False)

    def get_first_available_task(
        self, question=None, version=None
    ) -> Union[QuerySet[MarkingTask], None]:
        """Return the first marking task with a 'todo' status, sorted by `marking_priority`.

        If the priority is the same, defer to paper number and then question number.

        Args:
            question (optional): int, requested question number
            version (optional): int, requested version number

        Returns:
            The queryset of available tasks, or
            `None` if no such task exists.
        """
        available = MarkingTask.objects.filter(status=MarkingTask.TO_DO)

        if question:
            available = available.filter(question_number=question)

        if version:
            available = available.filter(question_version=version)

        if not available.exists():
            return None

        return available.order_by(
            "-marking_priority", "paper__paper_number", "question_number"
        ).first()

    def are_there_tasks(self):
        """Return True if there is at least one marking task in the database."""
        return MarkingTask.objects.exists()

    def assign_task_to_user(self, user: User, task: MarkingTask) -> None:
        """Associate a user to a marking task and update the task status.

        Args:
            user: reference to a User instance
            task: reference to a MarkingTask instance

        Exceptions:
            RuntimeError: task is already assigned.
        """
        if task.status == MarkingTask.OUT:
            raise RuntimeError("Task is currently assigned.")

        task.assigned_user = user
        task.status = MarkingTask.OUT
        task.save()

    def surrender_task(self, user, task):
        """Remove a user from a marking task, set its status to 'todo', and save the action to the database.

        Args:
            user: reference to a User instance
            task: reference to a MarkingTask instance
        """
        task.assigned_user = None
        task.status = MarkingTask.TO_DO
        task.save()

    def surrender_all_tasks(self, user):
        """Surrender all of the tasks currently assigned to the user.

        Args:
            user: reference to a User instance
        """
        user_tasks = MarkingTask.objects.filter(
            assigned_user=user, status=MarkingTask.OUT
        )
        with transaction.atomic():
            for task in user_tasks:
                self.surrender_task(user, task)

    def user_can_update_task(self, user, code):
        """Return true if a user is allowed to update a certain task, false otherwise.

        TODO: should be possible to remove the "assigned user" and "status" fields
        and infer both from querying ClaimTask and MarkAction instances.

        Args:
            user: reference to a User instance
            code: (str) task code
        """
        the_task = self.get_task_from_code(code)
        if the_task.assigned_user and the_task.assigned_user != user:
            return False

        if (
            the_task.status != MarkingTask.OUT
            and the_task.status != MarkingTask.COMPLETE
        ):
            return False

        return True

    @transaction.atomic
    def mark_task(self, user, code, score, time, image, data):
        """Save a user's marking attempt to the database."""
        task = self.get_task_from_code(code)
        if task.latest_annotation:
            last_annotation_edition = task.latest_annotation.edition
        else:  # there was no previous annotation
            last_annotation_edition = 0

        this_annotation = Annotation(
            edition=last_annotation_edition + 1,
            score=score,
            image=image,
            annotation_data=data,
            marking_time=time,
            task=task,
            user=user,
        )
        this_annotation.save()
        # update the latest_annotation field in the parent task
        task.latest_annotation = this_annotation
        task.save()

        # link to rubric object
        for item in data["sceneItems"]:
            if item[0] == "GroupDeltaText":
                rubric = Rubric.objects.get(key=item[3])
                rubric.annotations.add(this_annotation)
                rubric.save()

    def get_n_marked_tasks(self):
        """Return the number of marking tasks that are completed."""
        return MarkingTask.objects.filter(status=MarkingTask.COMPLETE).count()

    def get_n_total_tasks(self):
        """Return the total number of tasks in the database."""
        return MarkingTask.objects.all().count()

    def mark_task_as_complete(self, code):
        """Set a task as complete - assuming a client has made a successful request."""
        task = self.get_task_from_code(code)
        task.status = MarkingTask.COMPLETE
        task.save()

    def validate_and_clean_marking_data(self, user, code, data, plomfile):
        """Validate the incoming marking data.

        Args:
            user: reference to a User instance.
            code (str): key of the associated task.
            data (dict): information about the mark, rubrics, and annotation images.
            plomfile (str): a JSON field representing annotation data.

        Returns:
            tuple: three things in a tuple;
            `cleaned_data (dict)`: cleaned request data.
            `annot_data (dict)`: annotation-image data parsed from a JSON string.
            `rubrics_used (list)`: a list of Rubric objects, extracted based on
            keys found inside the `annot_data`.
        """
        annot_data = json.loads(plomfile)
        cleaned_data = {}

        if not self.user_can_update_task(user, code):
            raise RuntimeError("User cannot update task.")

        try:
            for val in ("pg", "ver", "score"):
                elem = data[val]
                cleaned_data[val] = int(elem)
        except IndexError:
            raise ValidationError(f"Multiple values for '{val}', expected 1.")
        except (ValueError, TypeError):
            raise ValidationError(f"Could not cast {val} as int: {elem}")

        # TODO: decide int or float
        try:
            cleaned_data["marking_time"] = float(data["marking_time"])
        except (ValueError, TypeError) as e:
            raise ValidationError(f"Could not cast 'marking_time' as float: {e}")

        # unpack the rubrics, potentially record which ones were used
        annotations = annot_data["sceneItems"]
        rubrics_used = []
        for ann in annotations:
            if ann[0] == "GroupDeltaText":
                rubric_key = ann[3]
                try:
                    rubric = Rubric.objects.get(key=rubric_key)
                except ObjectDoesNotExist:
                    raise ValidationError(f"Invalid rubric key: {rubric_key}")
                rubrics_used.append(rubric)

        src_img_data = annot_data["base_images"]
        for image_data in src_img_data:
            img_path = pathlib.Path(image_data["server_path"])
            if not img_path.exists():
                raise ValidationError("Invalid original-image in request.")

        return cleaned_data, annot_data, rubrics_used

    def get_user_mark_results(self, user, question=None, version=None):
        """For each completed task, get the latest annotation instances for a particular user.

        Args:
            user: User instance
            question (optional): int, the question number
            version (optional): int, the version number

        Returns:
            list [Annotation]: the relevant annotations
        """
        complete_tasks = MarkingTask.objects.filter(
            assigned_user=user, status=MarkingTask.COMPLETE
        )
        if question:
            complete_tasks = complete_tasks.filter(question_number=question)
        if version:
            complete_tasks = complete_tasks.filter(question_version=version)

        complete_tasks.prefetch_related("latest_annotation")
        annotations = map(
            lambda task: task.latest_annotation,
            complete_tasks,
        )

        return list(annotations)

    def get_latest_annotation(self, paper, question):
        """Get the latest annotation for a particular paper/question.

        Args:
            paper: int, the paper number
            question: int, the question number

        Returns:
            Annotation: the latest annotation instance

        Raises:
            ObjectDoesNotExist: no such marking task, either b/c the paper
            does not exist or the question does not exist for that paper.
        """
        task = mark_task.get_latest_task(paper, question)
        return task.latest_annotation

    def get_all_tags(self):
        """Get all of the saved tags.

        Returns:
            list[(int, str)]: The primary key and text of all the tags that exist.
        """
        return [(tag.pk, tag.text) for tag in MarkingTaskTag.objects.all()]

    def get_tags_for_task(self, code: str) -> list[str]:
        """Get a list of tags assigned to this marking task.

        Args:
            code: the question/paper code for a task.

        Returns:
            A list of the text of all tags for this task.

        Raises:
            RuntimeError: no such code.
        """
        # TODO: what if the client has an OLD task with the same code?
        task = self.get_task_from_code(code)
        return [tag.text for tag in task.markingtasktag_set.all()]

    def sanitize_tag_text(self, tag_text):
        """Return a sanitized text from client input. Currently only entails a call to tag_text.strip().

        Args:
            tag_text: str, text that has come from a client request.

        Returns:
            str: sanitized version of the text.
        """
        return tag_text.strip()

    def create_tag(self, user, tag_text):
        """Create a new tag that can be associated with marking task. Assumes the input text has already been sanitized.

        Args:
            user: reference to a User instance
            tag_text: str, the text content of a tag.

        Returns:
            MarkingTaskTag: reference to the newly created tag

        Raises:
            ValidationError: tag contains invalid characters.
        """
        if not is_valid_tag_text(tag_text):
            raise ValidationError(
                f'Invalid tag text: "{tag_text}"; contains disallowed characters'
            )
        new_tag = MarkingTaskTag(user=user, text=tag_text)
        new_tag.save()
        return new_tag

    def add_tag(self, tag, task):
        """Add a tag to a marking task. Assumes the input text has already been sanitized.

        Args:
            tag: reference to a MarkingTaskTag instance
            task: reference to a MarkingTask instance
        """
        tag.task.add(task)
        tag.save()

    def get_tag_from_text(self, text: str) -> Union[MarkingTaskTag, None]:
        """Get a tag object from its text contents. Assumes the input text has already been sanitized.

        Args:
            text: the text contents of a tag.

        Returns:
            The tag if it exists, otherwise `None` if it does not exist.
        """
        text_tags = MarkingTaskTag.objects.filter(text=text)
        if not text_tags.exists():
            return None
        # Assuming the queryset will always have a length of one
        return text_tags.first()

    def add_tag_text_from_task_code(self, tag_text: str, code: str, user: str) -> None:
        """Add a tag to a task, creating the tag if it does not exist.

        Args:
            tag_text: which tag to add, creating it if necessary.
            code: from which task, for example ``"q0123g5"`` for paper
                123 question 5.
            user: who is doing the tagging.
                TODO: record who tagged: Issue #2840.

        Returns:
            None

        Raises:
            ValueError: invalid task code
            RuntimeError: task not found
            ValidationError: invalid tag text
        """
        mts = MarkingTaskService()
        the_task = mts.get_task_from_code(code)
        the_tag = mts.get_tag_from_text(tag_text)
        if not the_tag:
            the_tag = mts.create_tag(user, tag_text)
        mts.add_tag(the_tag, the_task)

    def remove_tag_text_from_task_code(self, tag_text: str, code: str) -> None:
        """Remove a tag from a marking task.

        Args:
            tag_text: which tag to remove.
            code: from which task, for example ``"q0123g5"`` for paper
                123 question 5.

        Raises:
            ValueError: invalid task code, no such tag, or this task does not
                have this tag.
            RuntimeError: task not found.
        """
        the_tag = self.get_tag_from_text(tag_text)
        if not the_tag:
            raise ValueError(f'No such tag "{tag_text}"')
        the_task = self.get_task_from_code(code)
        self.remove_tag_from_task(the_tag, the_task)

    def remove_tag_from_task(self, tag, task):
        """Backend to remove a tag from a marking task.

        Args:
            tag: reference to a MarkingTaskTag instance
            task: reference to a MarkingTask instance
        """
        try:
            tag.task.remove(task)
            tag.save()
        except MarkingTask.DoesNotExist:
            raise ValueError(f'Task {task.code} does not have tag "{tag.text}"')

    @transaction.atomic
    def set_paper_marking_task_outdated(self, paper_number: int, question_number: int):
        """Set the marking task for the given paper/question as OUT_OF_DATE.

        When a page-image is removed or added to a paper/question, any
        existing annotations are now out of date (since the underlying
        pages have changed). This function is called when such changes occur.

        Args:
            paper_number (int): the paper
            question_number (int): the question
        Raises:
            ValueError: when there is no such paper.
            MultipleObjectsReturned: when there are multiple valid marking tasks
                for that paper/question. This should not happen unless something
                has gone seriously wrong.
        """
        try:
            paper_obj = Paper.objects.get(paper_number=paper_number)
        except Paper.DoesNotExist:
            raise ValueError(f"Cannot find paper {paper_number}")

        ibs = ImageBundleService()

        # now we know there is at least one task (either valid or out of date)
        valid_tasks = MarkingTask.objects.exclude(
            status=MarkingTask.OUT_OF_DATE
        ).filter(paper=paper_obj, question_number=question_number)
        valid_task_count = valid_tasks.exclude(status=MarkingTask.OUT_OF_DATE).count()
        # do a integrity check - there can only at most one valid task
        if valid_task_count > 1:
            # Note that we should not find ourselves here unless there is a serious error in the code
            # Any given question should have **at most** one valid task.
            # If we ever arrive here it indicates that there is a corruption of the database
            raise MultipleObjectsReturned(
                f"Very serious error - have found multiple valid Marking-tasks for paper {paper_number} question {question_number}"
            )
        # we know there is at most one valid task.
        if valid_task_count == 1:
            # there is an "in date" task - get it and set it as out of date
            task_obj = valid_tasks.get()
            # set the last id-action as invalid (if it exists)
            if task_obj.latest_annotation:
                latest_annotation = task_obj.latest_annotation
                latest_annotation.is_valid = False
                latest_annotation.save()
            # now set status and make assigned user None
            task_obj.assigned_user = None
            task_obj.status = MarkingTask.OUT_OF_DATE
            task_obj.save()
        else:
            # there is no "in date" task, so we don't have to mark anything as out of date.
            pass

        # now all existing tasks are out of date, so if the question is ready create a new marking task for it.
        if ibs.is_given_paper_question_ready(paper_obj, question_number):
            self.create_task(paper_obj, question_number)
