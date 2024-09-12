# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2024 Aden Chan
# Copyright (C) 2024 Aidan Murphy
# Copyright (C) 2024 Bryan Tanady


from __future__ import annotations

import json
import pathlib
import random
from typing import Any

from rest_framework.exceptions import ValidationError

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db.models import QuerySet
from django.db import transaction

from plom import is_valid_tag_text
from Papers.services import ImageBundleService, PaperInfoService
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
    def create_task(
        self,
        paper: Paper,
        question_index: int,
        *,
        user: User | None = None,
        copy_old_tags: bool = True,
    ) -> MarkingTask:
        """Create a marking task.

        Args:
            paper: a Paper instance, the test paper of the task.
            question_index: the question of the task, by 1-based index.

        Keyword Args:
            user: optional, User instance of user assigned to the task.
            copy_old_tags: copy any tags from the latest old task to the new task.

        Returns:
            The newly created marking task object.
        """
        # get the version of the given paper/question
        try:
            question_version = PaperInfoService().get_version_from_paper_question(
                paper.paper_number, question_index
            )
        except ValueError as err:
            raise RuntimeError(f"Server does not have a question-version map - {err}")

        task_code = f"q{paper.paper_number:04}g{question_index}"

        # other tasks with this code are now 'out of date'
        MarkingTask.objects.filter(code=task_code).exclude(
            status=MarkingTask.OUT_OF_DATE
        ).update(status=MarkingTask.OUT_OF_DATE, assigned_user=None)

        # get priority of latest old task to assign to new task, but
        # if no previous priority exists, set a new value based on the current strategy
        latest_old_task = (
            MarkingTask.objects.filter(code=task_code).order_by("-time").first()
        )
        if latest_old_task:
            priority = latest_old_task.marking_priority
        else:
            strategy = marking_priority.get_mark_priority_strategy()
            if strategy == MarkingTaskPriority.PAPER_NUMBER:
                priority = Paper.objects.count() - paper.paper_number
            else:
                priority = random.randint(0, 1000)

        the_task = MarkingTask.objects.create(
            assigned_user=user,
            code=task_code,
            paper=paper,
            question_index=question_index,
            question_version=question_version,
            marking_priority=priority,
        )
        # if there is an older task and we are instructed to copy any old tags, then do so.
        if copy_old_tags and latest_old_task:
            for tag_obj in latest_old_task.markingtasktag_set.all():
                the_task.markingtasktag_set.add(tag_obj)
            the_task.save()
        return the_task

    def get_marking_progress(self, question: int, version: int) -> tuple[int, int]:
        """Send back current marking progress counts to the client.

        Args:
            question: which question index.
            version: which version.

        Returns:
            two integers, first the number of marked papers for
            this question/version and the total number of papers for
            this question/version.  Note: if question or version are
            invalid we return a pair of zeros.
        """
        try:
            completed = MarkingTask.objects.filter(
                status=MarkingTask.COMPLETE,
                question_index=question,
                question_version=version,
            )
            total = MarkingTask.objects.filter(
                question_index=question, question_version=version
            ).exclude(status=MarkingTask.OUT_OF_DATE)
        except MarkingTask.DoesNotExist:
            return (0, 0)

        return (completed.count(), total.count())

    def get_task_from_code(self, code: str) -> MarkingTask:
        """Get a marking task from its code.

        Args:
            code: a unique string that includes the paper number and question index.

        Returns:
            The latest marking task object that matches the code.

        Raises:
            ValueError: invalid code.
            RuntimeError: code valid but task does not exist.
        """
        try:
            paper_number, question_idx = mark_task.unpack_code(code)
        except AssertionError as e:
            raise ValueError(f"{code} is not a valid task code: {e}") from e
        try:
            return mark_task.get_latest_task(paper_number, question_idx)
        except ObjectDoesNotExist as e:
            raise RuntimeError(e) from e

    def get_user_tasks(
        self, user: User, question_idx: int | None = None, version: int | None = None
    ) -> QuerySet[MarkingTask]:
        """Get all the marking tasks that are assigned to this user.

        Args:
            user: User instance
            question_idx (optional): the question index.
            version (optional): the version number

        Returns:
            Marking tasks assigned to user
        """
        tasks = MarkingTask.objects.filter(assigned_user=user)
        if question_idx:
            tasks = tasks.filter(question_index=question_idx)
        if version:
            tasks = tasks.filter(question_version=version)

        return tasks

    def get_tasks_from_question_with_annotation(
        self, question_idx: int, version: int
    ) -> QuerySet[MarkingTask]:
        """Get all the marking tasks for this question/version.

        Args:
            question_idx: the question index.
            version: int, the version number. If version == 0, then all versions are returned.

        Returns:
            A QuerySet of tasks.

        Raises:
            None expected.
        """
        marking_tasks = MarkingTask.objects.filter(
            question_index=question_idx, status=MarkingTask.COMPLETE
        )
        if version != 0:
            marking_tasks = marking_tasks.filter(question_version=version)
        return marking_tasks

    def get_complete_marking_tasks(self) -> QuerySet[MarkingTask]:
        """Returns all complete marking tasks."""
        return MarkingTask.objects.filter(status=MarkingTask.COMPLETE).all()

    def get_latest_annotations_from_complete_marking_tasks(
        self,
    ) -> QuerySet[Annotation]:
        """Returns the latest annotations from all tasks that are complete."""
        # TODO - can we remove this function?
        return Annotation.objects.filter(
            markingtask__status=MarkingTask.COMPLETE
        ).filter(markingtask__latest_annotation__isnull=False)

    def are_there_tasks(self) -> bool:
        """Return True if there is at least one marking task in the database."""
        return MarkingTask.objects.exists()

    @staticmethod
    def assign_task_to_user(task_pk: int, user: User) -> None:
        """Associate a user to a marking task and update the task status.

        The task must be TO_DO, and it will become OUT.

        Note: this looks superficially like :method:`reassign_task_to_user`;
        this current method is really about claiming "OUT" tasks for a user.

        Args:
            task_pk: the primary key of a task.
            user: reference to a User instance.

        Exceptions:
            RuntimeError: task is already assigned.
            MarkingTask.DoesNotExist: if there is no such task.
        """
        task = MarkingTask.objects.select_for_update().get(pk=task_pk)
        if task.status != MarkingTask.TO_DO:
            raise RuntimeError(
                f'Task is not available: currently assigned to "{task.assigned_user}"'
            )

        # the assigned_user is None, then okay, or if set to the current user okay,
        # but otherwise throw an error.
        if not (task.assigned_user is None or task.assigned_user == user):
            raise RuntimeError(
                f'Unable to assign task to user "{user}" - task has'
                f'- a different assigned user "{task.assigned_user}".'
            )

        task.assigned_user = user
        task.status = MarkingTask.OUT
        task.save()

    def surrender_all_tasks(self, user: User) -> None:
        """Surrender all of the tasks currently assigned to the user.

        Args:
            user: reference to a User instance
        """
        MarkingTask.objects.filter(assigned_user=user, status=MarkingTask.OUT).update(
            assigned_user=None, status=MarkingTask.TO_DO
        )

    def get_n_marked_tasks(self) -> int:
        """Return the number of marking tasks that are completed."""
        return MarkingTask.objects.filter(status=MarkingTask.COMPLETE).count()

    def get_n_total_tasks(self) -> int:
        """Return the total number of tasks in the database."""
        return MarkingTask.objects.all().count()

    def get_n_valid_tasks(self) -> int:
        """Return the total number of tasks in the database, excluding out of date tasks."""
        return MarkingTask.objects.exclude(status=MarkingTask.OUT_OF_DATE).count()

    def validate_and_clean_marking_data(
        self, code: str, data: dict[str, Any], plomfile: str
    ) -> tuple[dict[str, Any], dict, list[Rubric]]:
        """Validate the incoming marking data.

        Args:
            code (str): key of the associated task.
            data (dict): information about the mark, rubrics, and annotation images.
            plomfile (str): a JSON field representing annotation data.

        Returns:
            tuple: three things in a tuple;
            `cleaned_data (dict)`: cleaned request data.
            `annot_data (dict)`: annotation-image data parsed from a JSON string.
            `rubrics_used (list)`: a list of Rubric objects, extracted based on
            keys found inside the `annot_data`.

        Raises:
            ValidationError
        """
        annot_data = json.loads(plomfile)
        cleaned_data: dict[str, Any] = {}

        try:
            cleaned_data["pg"] = int(data["pg"])
        except IndexError:
            raise ValidationError('Multiple values for "pg", expected 1.')
        except (ValueError, TypeError):
            raise ValidationError(f'Could not cast "pg" as int: {data["pg"]}')

        try:
            cleaned_data["ver"] = int(data["ver"])
        except IndexError:
            raise ValidationError('Multiple values for "ver", expected 1.')
        except (ValueError, TypeError):
            raise ValidationError(f'Could not cast "ver" as int: {data["ver"]}')

        try:
            cleaned_data["score"] = float(data["score"])
        except IndexError:
            raise ValidationError('Multiple values for "score", expected 1.')
        except (ValueError, TypeError):
            raise ValidationError(f'Could not cast "score" as float: {data["score"]}')

        try:
            cleaned_data["marking_time"] = float(data["marking_time"])
        except (ValueError, TypeError) as e:
            raise ValidationError(f"Could not cast 'marking_time' as float: {e}")

        try:
            cleaned_data["integrity_check"] = int(data["integrity_check"])
        except (ValueError, TypeError) as e:
            raise ValidationError(f"Could not get 'integrity_check' as a int: {e}")

        # unpack the rubrics, potentially record which ones were used
        # TODO: similar code to this in annotations.py:_add_annotation_to_rubrics
        annotations = annot_data["sceneItems"]
        rubrics_used = []
        for ann in annotations:
            if ann[0] == "Rubric":
                rid = ann[3]["rid"]
                try:
                    rubric = Rubric.objects.get(rid=rid, latest=True)
                except ObjectDoesNotExist:
                    raise ValidationError(f"Invalid rubric rid: {rid}")
                rubrics_used.append(rubric)

        src_img_data = annot_data["base_images"]
        for image_data in src_img_data:
            img_path = pathlib.Path(image_data["server_path"])
            if not img_path.exists():
                raise ValidationError("Invalid original-image in request.")

        return cleaned_data, annot_data, rubrics_used

    def get_latest_annotation(self, paper: int, question_idx: int) -> Annotation:
        """Get the latest annotation for a particular paper/question.

        Args:
            paper: the paper number.
            question_idx: the question index, from one.

        Returns:
            The latest annotation instance.

        Raises:
            ObjectDoesNotExist: no such marking task, either b/c the paper
                does not exist or the question does not exist for that
                paper.
            ValueError: This paper question exists but does not have
                annotations.
        """
        task = mark_task.get_latest_task(paper, question_idx)
        if task.latest_annotation is None:
            raise ValueError(
                f"Paper {paper} question index {question_idx} has no annotations"
            )
        return task.latest_annotation

    def get_annotation_by_edition(
        self, paper: int, question_idx: int, edition: int
    ) -> Annotation:
        """Get a particular edition of the Annotations for a paper/question.

        Args:
            paper: the paper number.
            question_idx: the question index, from one.
            edition: papers can be annotated many times, this controls
                which revision is wanted.  To get the latest,
                see :method:`get_latest_annotation`

        Returns:
            The matching Annotation instance.

        Raises:
            ObjectDoesNotExist: paper does not exist, question index does
                not exist or the requested edition does not exist within
                a valid (not out-of-date) task.

        TODO: we might consider raising ValueError if there is such an
        edition for an OUT_OF_DATE task: for now that case is folded into
        the task not existing.

        TODO: work would also be required, here and elsewhere, for multiple
        concurrent tasks.  Most likely we would replace this with a pk-based
        getter before trying that.
        """
        paper_obj = Paper.objects.get(paper_number=paper)
        tasks = MarkingTask.objects.filter(paper=paper_obj, question_index=question_idx)
        # many tasks could match edition; we want the unique non-out-of-date one.
        # TODO: in principle, we could do some try-except to detect the edition
        # exists but is out-of-date: not sure its worth the effort.
        task = tasks.exclude(status=MarkingTask.OUT_OF_DATE).get()
        return Annotation.objects.get(task=task, edition=edition)

    def get_all_tags(self) -> list[tuple[int, str]]:
        """Get all of the saved tags.

        Returns:
            A list of pairs of primary keys and text, for each of the
            tags that exist.
        """
        return [(tag.pk, tag.text) for tag in MarkingTaskTag.objects.all()]

    def get_tags_for_task(self, code: str) -> list[str]:
        """Get a list of tags assigned to a marking task by its code.

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

    def get_tags_for_task_pk(self, task_pk: int) -> list[str]:
        """Get a list of tags assigned to a marking task by its pk.

        Args:
            task_pk: which task.

        Returns:
            A list of the text of all tags for this task.

        Raises:
            RuntimeError: no such code.
        """
        task = MarkingTask.objects.get(pk=task_pk)
        return [tag.text for tag in task.markingtasktag_set.all()]

    def get_tags_text_and_pk_for_task(self, task_pk: int) -> list[tuple[int, str]]:
        """Get a list of tag (text and pk) assigned to this marking task."""
        task = MarkingTask.objects.get(pk=task_pk)
        return [(tag.pk, tag.text) for tag in task.markingtasktag_set.all()]

    def sanitize_tag_text(self, tag_text):
        """Return a sanitized text from client input. Currently only entails a call to tag_text.strip().

        Args:
            tag_text: str, text that has come from a client request.

        Returns:
            str: sanitized version of the text.
        """
        return tag_text.strip()

    def create_tag(self, user: User, tag_text: str) -> MarkingTaskTag:
        """Create a new tag that can be associated with marking task.

        Args:
            user: reference to a User instance
            tag_text: str, the proposed text content of a tag.
                Assumes this input text has already been sanitized.

        Returns:
            MarkingTaskTag: reference to the newly created tag

        Raises:
            ValidationError: tag contains invalid characters.
        """
        if not is_valid_tag_text(tag_text):
            raise ValidationError(
                f'Invalid tag text: "{tag_text}"; contains disallowed characters'
            )
        new_tag = MarkingTaskTag.objects.create(user=user, text=tag_text)
        return new_tag

    def _add_tag(self, tag: MarkingTaskTag, task: MarkingTask) -> None:
        """Add a tag to a marking task. Assumes the input text has already been sanitized.

        Also assumes appropriate select_for_update's have been done although
        from glancing at the code I doubt that's true.

        Args:
            tag: reference to a MarkingTaskTag instance.
            task: reference to a MarkingTask instance.

        Returns:
            None
        """
        # TODO: port to select_for_update?
        tag.task.add(task)
        tag.save()

    @transaction.atomic
    def add_tag_to_task_via_pks(self, tag_pk: int, task_pk: int) -> None:
        """Add existing tag with given pk to the marking task with given pk.

        Raises:
            ValueError: no such task or tag.
        """
        try:
            the_task = MarkingTask.objects.select_for_update().get(pk=task_pk)
            the_tag = MarkingTaskTag.objects.get(pk=tag_pk)
        except (MarkingTask.DoesNotExist, MarkingTaskTag.DoesNotExist):
            raise ValueError("Cannot find task or tag with given pk")
        self._add_tag(the_tag, the_task)

    def _get_tag_from_text_for_update(self, text: str) -> MarkingTaskTag | None:
        """Get a tag object from its text contents.

        Assumes the input text has already been sanitized.
        Selects it for update.

        Args:
            text: the text contents of a tag.

        Returns:
            The tag if it exists, otherwise `None` if it does not exist.
        """
        text_tags = MarkingTaskTag.objects.filter(text=text)
        if not text_tags.exists():
            return None
        # Assuming the queryset will always have a length of one
        # grab its PK so we can get the tag with select_for_update
        tag_pk = text_tags.first().pk
        return MarkingTaskTag.objects.select_for_update().get(pk=tag_pk)

    @transaction.atomic
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
        the_task = self.get_task_from_code(code)
        the_tag = self._get_tag_from_text_for_update(tag_text)
        if not the_tag:
            the_tag = self.create_tag(user, tag_text)
        self._add_tag(the_tag, the_task)

    @transaction.atomic
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
        # note - is select_for_update
        the_tag = self._get_tag_from_text_for_update(tag_text)
        # does not raise exception - rather it returns a None if can't find the tag
        if not the_tag:
            raise ValueError(f'No such tag "{tag_text}"')
        the_task = self.get_task_from_code(code)
        # raises ValueError if the code is invalid
        # RuntimeError if the code is okay but the task does not exist

        self._remove_tag_from_task(the_tag, the_task)

    def _remove_tag_from_task(self, tag, task):
        """Backend to remove a tag from a marking task.

        Args:
            tag: reference to a MarkingTaskTag instance
                - should be selected for update since we
                  are going to modify it.
            task: reference to a MarkingTask instance
        """
        # check if the tag and task are linked - see #2810
        if tag.task.filter(pk=task.pk).exists():
            tag.task.remove(task)
            tag.save()  # tag is select for update
        else:
            raise ValueError(f'Task {task.code} does not have tag "{tag.text}"')

    @transaction.atomic
    def remove_tag_from_task_via_pks(self, tag_pk: int, task_pk: int) -> None:
        """Add existing tag with given pk to the marking task with given pk."""
        try:
            the_task = MarkingTask.objects.select_for_update().get(pk=task_pk)
            the_tag = MarkingTaskTag.objects.get(pk=tag_pk)
        except (MarkingTask.DoesNotExist, MarkingTaskTag.DoesNotExist):
            raise ValueError("Cannot find task or tag with given pk")
        self._remove_tag_from_task(the_tag, the_task)

    @transaction.atomic
    def set_paper_marking_task_outdated(
        self, paper_number: int, question_index: int
    ) -> None:
        """Set the marking task for the given paper/question as OUT_OF_DATE.

        When a page-image is removed or added to a paper/question, any
        existing annotations are now out of date (since the underlying
        pages have changed). This function is called when such changes occur.

        Args:
            paper_number: the paper
            question_index: the question

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
        ).filter(paper=paper_obj, question_index=question_index)
        valid_task_count = valid_tasks.exclude(status=MarkingTask.OUT_OF_DATE).count()
        # do a integrity check - there can only at most one valid task
        if valid_task_count > 1:
            # Note that we should not find ourselves here unless there is a serious error in the code
            # Any given question should have **at most** one valid task.
            # If we ever arrive here it indicates that there is a corruption of the database
            raise MultipleObjectsReturned(
                "Very serious error - have found multiple valid Marking-tasks"
                f" for paper {paper_number} question idx {question_index}"
            )
        # we know there is at most one valid task.
        if valid_task_count == 1:
            # there is an "in date" task - get it and set it as out of date, and set the assigned user to None.
            task_obj = valid_tasks.select_for_update().get()
            task_obj.assigned_user = None
            task_obj.status = MarkingTask.OUT_OF_DATE
            task_obj.save()
        else:
            # there is no "in date" task, so we don't have to mark anything as out of date.
            pass

        # now all existing tasks are out of date, so if the question is ready create a new marking task for it.
        if ibs.is_given_paper_question_ready(paper_obj, question_index):
            self.create_task(paper_obj, question_index)

    @transaction.atomic
    def create_tag_and_attach_to_task(
        self, user: User, task_pk: int, tag_text: str
    ) -> None:
        """Create a tag with given text and attach to given task.

        Args:
            user: the user creating/attaching the tag.
            task_pk: the pk of the markingtask.
            tag_text: the text of the tag being created/attached.

        Returns:
            None

        Raises:
            ValidationError: if the tag text is not legal.
        """
        # clean up the text and see if such a tag already exists
        cleaned_tag_text = self.sanitize_tag_text(tag_text)
        tag_obj = self._get_tag_from_text_for_update(cleaned_tag_text)
        if tag_obj is None:  # no such tag exists, so create one
            # note - will raise validationerror if tag_text not legal
            tag_obj = self.create_tag(user, cleaned_tag_text)
        # finally - attach it.
        self.add_tag_to_task_via_pks(tag_obj.pk, task_pk)

    @transaction.atomic
    @staticmethod
    def reassign_task_to_user(task_pk: int, username: str) -> None:
        """Reassign a task to a different user.

        If tasks status is "COMPLETE" then the assigned_user will be updated,
        while if it is "OUT" or "TO_DO", then assigned user will be set to None.
        ie - this function assumes that the task will also be tagged with
        an appropriate @username tag (by the caller; we don't do it for you!)

        Note: this looks superficially like :method:`assign_task_to_user` but
        its used in a different way.  That method is about claiming tasks.
        This current method is most useful for "unclaiming" tasks, and---with
        extra tagging effort described above---pushing them toward a different
        user.

        Args:
            task_pk: the primary key of a task.
            username: a string of a username.

        Returns:
            None.

        Raises:
            ValueError: cannot find user, or cannot find marking task.
        """
        # make sure the given username corresponds to a marker
        try:
            new_user = User.objects.get(username=username, groups__name="marker")
        except ObjectDoesNotExist:
            raise ValueError(f"Cannot find a marker-user {username}")
        # grab the task
        try:
            with transaction.atomic():
                task_obj = MarkingTask.objects.select_for_update().get(pk=task_pk)
                if task_obj.assigned_user == new_user:
                    # already assigned to new_user, nothing needs done
                    return
                if task_obj.status == MarkingTask.COMPLETE:
                    task_obj.assigned_user = new_user
                elif task_obj.status == MarkingTask.OUT_OF_DATE:
                    # log.warn(f"Uselessly reassigning OUT_OF_DATE task {task_obj}")
                    task_obj.assigned_user = new_user
                elif task_obj.status in (MarkingTask.OUT, MarkingTask.TO_DO):
                    # if out then set it as todo and clear the assigned_user.
                    # Note: this makes it available to anyone; the caller
                    # might want to additionally tag it for new_user.
                    task_obj.status = MarkingTask.TO_DO
                    task_obj.assigned_user = None
                else:
                    raise AssertionError(
                        f'Tertium non datur: impossible status "{task_obj.status}"'
                    )
                task_obj.save()
        except ObjectDoesNotExist:
            raise ValueError(f"Cannot find marking task {task_pk}")
