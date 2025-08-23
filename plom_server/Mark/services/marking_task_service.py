# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2023-2025 Andrew Rechnitzer
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2024 Aden Chan
# Copyright (C) 2024 Aidan Murphy
# Copyright (C) 2024 Bryan Tanady

import json
import pathlib
import random
from typing import Any

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db.models import QuerySet
from django.db import transaction
from rest_framework import serializers

from plom.tagging import is_valid_tag_text
from plom_server.Papers.services import ImageBundleService, PaperInfoService
from plom_server.Papers.models import Paper

from . import MarkingPriorityService, mark_task
from ..models import MarkingTask, MarkingTaskTag, Annotation


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
            paper: a Paper instance, the paper of the task.
            question_index: the question of the task, by 1-based index.

        Keyword Args:
            user: optional, User instance of user assigned to the task.
            copy_old_tags: copy any tags from the latest old task to the new task.

        Returns:
            The newly created marking task object.

        Raises:
            KeyError: cannot create tasks for non-positive question index,
                as those are used as a DNM indicator.
            RuntimeError: for "good" input data, this would indicate no
                question-version map, although for nonsense input it could
                also just mean invalid paper number or invalid question index.
        """
        if question_index <= 0:
            raise KeyError(f"Invalid question index: {question_index}")
        # get the version of the given paper/question
        try:
            question_version = PaperInfoService().get_version_from_paper_question(
                paper.paper_number, question_index
            )
        except ValueError as err:
            raise RuntimeError(f"Server does not have a question-version map - {err}")

        task_code = f"{paper.paper_number:04}g{question_index}"

        # other tasks with this code are now 'out of date'
        # as per #3220 do not erase assigned user.
        MarkingTask.objects.filter(code=task_code).exclude(
            status=MarkingTask.OUT_OF_DATE
        ).update(status=MarkingTask.OUT_OF_DATE)

        # get priority of latest old task to assign to new task, but
        # if no previous priority exists, set a new value based on the current strategy
        latest_old_task = (
            MarkingTask.objects.filter(code=task_code).order_by("-time").first()
        )
        if latest_old_task:
            priority = latest_old_task.marking_priority
        else:
            strategy = MarkingPriorityService.get_mark_priority_strategy()
            if strategy == "paper_number":
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

    @staticmethod
    @transaction.atomic
    def bulk_create_and_update_marking_tasks(
        paper_question_version_list: list[tuple[int, int, int]],
        *,
        copy_old_tags: bool = True,
    ) -> None:
        """In an efficient way, create and update all marking tasks at once.

        This was added for DB performance reasons, and the caller presumably
        does some work to pre-assemble the inputs, rather than looping one
        at a time.

        Args:
            paper_question_version_list: each entry is a tuple of
                `paper_number`, `question_index`, and `version`.

        Keyword Args:
            copy_old_tags: copy over any old tags from the previous tasks.
                Note this currently may have a performance hit as it uses
                a loop.
        """
        # create all the task codes
        task_codes = [f"{X[0]:04}g{X[1]}" for X in paper_question_version_list]
        # use this to get all existing marking tasks
        existing_tasks = (
            MarkingTask.objects.filter(code__in=task_codes)
            .exclude(status=MarkingTask.OUT_OF_DATE)
            .prefetch_related("markingtasktag_set")
        )
        # set all as out of date but keep any priorities and tags
        priorities = {}
        existing_tags = {}
        for X in existing_tasks:
            X.status = MarkingTask.OUT_OF_DATE
            X.assigned_user = None
            priorities[X.code] = X.marking_priority
            existing_tags[X.code] = X.markingtasktag_set.all()
        # get priority strategy for new tasks
        strategy = MarkingPriorityService.get_mark_priority_strategy()
        total_papers = Paper.objects.count()
        # create new tasks using any existing priorities
        # unfortunately we need the associated paper-objects
        # and need to be able to look-up from paper-number
        updated_paper_numbers = set(X[0] for X in paper_question_version_list)
        updated_papers = Paper.objects.filter(paper_number__in=updated_paper_numbers)
        pn_to_paper = {X.paper_number: X for X in updated_papers}
        # finally get on with building things
        new_tasks = []
        for pn, qi, v in paper_question_version_list:
            code = f"{pn:04}g{qi}"
            if code in priorities:
                priority = priorities[code]
            elif strategy == "paper_number":
                priority = total_papers - pn
            else:
                priority = random.randint(0, 1000)
            new_tasks.append(
                MarkingTask(
                    assigned_user=None,
                    code=code,
                    paper=pn_to_paper[pn],
                    question_index=qi,
                    question_version=v,
                    marking_priority=priority,
                )
            )
        # now bulk-update existing tasks and bulk_create the new ones
        MarkingTask.objects.bulk_update(existing_tasks, ["assigned_user", "status"])
        MarkingTask.objects.bulk_create(new_tasks)
        # copy over any old tags - unfortunately this is O(n) not O(1)
        if copy_old_tags:
            for X in new_tasks:
                if X.code in existing_tags:
                    for tag_obj in existing_tags[X.code]:
                        X.markingtasktag_set.add(tag_obj)
                    X.save()

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
        paper_number, question_idx = mark_task.unpack_code(code)
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

    @staticmethod
    def surrender_all_tasks(user: User) -> None:
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
    ) -> tuple[dict[str, Any], dict]:
        """Validate the incoming marking data.

        Note this doesn't actually touch the database.  Its more like type checking
        of the inputs and in-expensive things like that.  There is one exception:
        it confirms that all the underlying images actually exist on the server.
        This is a file system (later object store) hit, which will have some IO cost.

        Args:
            code (str): key of the associated task.
            data (dict): information about the mark, rubrics, and annotation images.
            plomfile (str): a JSON field representing annotation data.

        Returns:
            Two things in a tuple;
            `cleaned_data`: dict of the cleaned request data.
            `annot_data`: dict of the annotation-image data parsed from
            a JSON string.

        Raises:
            serializers.ValidationError
        """
        annot_data = json.loads(plomfile)
        cleaned_data: dict[str, Any] = {}

        try:
            cleaned_data["pg"] = int(data["pg"])
        except IndexError as e:
            raise serializers.ValidationError(
                'Multiple values for "pg", expected 1.'
            ) from e
        except (ValueError, TypeError) as e:
            raise serializers.ValidationError(
                f'Could not cast "pg" as int: {data["pg"]}'
            ) from e

        try:
            cleaned_data["ver"] = int(data["ver"])
        except IndexError as e:
            raise serializers.ValidationError(
                'Multiple values for "ver", expected 1.'
            ) from e
        except (ValueError, TypeError) as e:
            raise serializers.ValidationError(
                f'Could not cast "ver" as int: {data["ver"]}'
            ) from e

        try:
            cleaned_data["score"] = float(data["score"])
        except IndexError as e:
            raise serializers.ValidationError(
                'Multiple values for "score", expected 1.'
            ) from e
        except (ValueError, TypeError) as e:
            raise serializers.ValidationError(
                f'Could not cast "score" as float: {data["score"]}'
            ) from e

        try:
            cleaned_data["marking_time"] = float(data["marking_time"])
        except (ValueError, TypeError) as e:
            raise serializers.ValidationError(
                f"Could not cast 'marking_time' as float: {e}"
            ) from e

        try:
            cleaned_data["integrity_check"] = int(data["integrity_check"])
        except (ValueError, TypeError) as e:
            raise serializers.ValidationError(
                f"Could not get 'integrity_check' as a int: {e}"
            ) from e

        # We used to unpack the rubrics and ensure they all exist in the DB.
        # That will happen later when we try to save: I'm not sure its worth
        # the overhead of checking twice: smells like asking permission...

        src_img_data = annot_data["base_images"]
        for image_data in src_img_data:
            img_path = pathlib.Path(image_data["server_path"])
            if not img_path.exists():
                raise serializers.ValidationError("Invalid original-image in request.")

        return cleaned_data, annot_data

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

    @transaction.atomic
    def get_or_create_tag(self, user: User, tag_text: str) -> MarkingTaskTag:
        """Get an existing tag, or create if necessary, based on the given text.

        Args:
            user: the user creating/attaching the tag.
            tag_text: the text of the tag.

        Returns:
            MarkingTaskTag: reference to the tag

        Raises:
            serializers.ValidationError: if the tag text is not legal.
        """
        if not is_valid_tag_text(tag_text):
            raise serializers.ValidationError(
                f'Invalid tag text: "{tag_text}"; contains disallowed characters'
            )
        try:
            tag_obj = MarkingTaskTag.objects.get(text=tag_text)
        except MarkingTaskTag.DoesNotExist:
            # no such tag exists, so create one
            tag_obj = MarkingTaskTag.objects.create(user=user, text=tag_text)
        return tag_obj

    def _add_tag(self, tag: MarkingTaskTag, task: MarkingTask) -> None:
        """Add an existing tag to an existing marking task.

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
        # grab its PK so we can get the tag with select_for_update
        tag_pk = text_tags.get().pk
        return MarkingTaskTag.objects.select_for_update().get(pk=tag_pk)

    @transaction.atomic
    def add_tag_text_from_task_code(self, tag_text: str, code: str, user: str) -> None:
        """Add a tag to a task, creating the tag if it does not exist.

        Args:
            tag_text: which tag to add, creating it if necessary.
            code: from which task, for example ``"0123g5"`` for paper
                123 question 5.
            user: who is doing the tagging.
                TODO: record who tagged: Issue #2840.

        Returns:
            None

        Raises:
            ValueError: invalid task code
            RuntimeError: task not found
            serializers.ValidationError: invalid tag text
        """
        the_task = self.get_task_from_code(code)
        the_tag = self.get_or_create_tag(user, tag_text)
        self._add_tag(the_tag, the_task)

    @transaction.atomic
    def remove_tag_text_from_task_code(self, tag_text: str, code: str) -> None:
        """Remove a tag from a marking task.

        Args:
            tag_text: which tag to remove.
            code: from which task, for example ``"0123g5"`` for paper
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
        """Remove tag with given pk from the marking task with given pk."""
        try:
            the_task = MarkingTask.objects.select_for_update().get(pk=task_pk)
            the_tag = MarkingTaskTag.objects.get(pk=tag_pk)
        except (MarkingTask.DoesNotExist, MarkingTaskTag.DoesNotExist):
            raise ValueError("Cannot find task or tag with given pk")
        self._remove_tag_from_task(the_tag, the_task)

    @classmethod
    def _tag_task_pk_for_user(
        cls, task_pk: int, username: str, calling_user: User, unassign_others: bool
    ) -> None:
        """Tag a task for a user, removing other user tags."""
        task = MarkingTask.objects.get(pk=task_pk)
        # TODO: maybe these many-to-many things don't need select_for_update
        # task = MarkingTask.objects.select_for_update().get(pk=task_pk)
        if unassign_others:
            for tag in task.markingtasktag_set.all():
                if tag.text.startswith("@"):
                    # TODO: colin doesn't understand this notation
                    tag.task.remove(task)
        attn_user_tag_text = f"@{username}"
        cls().create_tag_and_attach_to_task(calling_user, task_pk, attn_user_tag_text)

    @transaction.atomic
    def set_paper_marking_task_outdated(
        self, paper_number: int, question_index: int
    ) -> None:
        """Set the marking tasks for the given paper/question as OUT_OF_DATE.

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
        pq_pair = (paper_obj.paper_number, question_index)
        if ibs.are_paper_question_pairs_ready([pq_pair])[pq_pair]:
            self.create_task(paper_obj, question_index)

    @transaction.atomic
    def create_tag_and_attach_to_task(
        self, user: User, task_pk: int, tag_text: str
    ) -> None:
        """Tag a task with the given text, creating the new tag if necessary.

        Args:
            user: the user creating/attaching the tag.
            task_pk: the pk of the markingtask.
            tag_text: the text of the tag being created/attached.
                If a tag with this text already exists, we'll use it.

        Returns:
            None

        Raises:
            serializers.ValidationError: if the tag text is not legal.
        """
        tag_obj = self.get_or_create_tag(user, tag_text)
        self.add_tag_to_task_via_pks(tag_obj.pk, task_pk)

    @staticmethod
    def _reassign_task_to_user(task_pk: int, username: str) -> None:
        """Reassign a task to a different user, low level routine.

        If tasks status is "COMPLETE" then the assigned_user will be updated,
        while if it is "OUT" or "TO_DO", then assigned user will be set to None.
        ie - this function assumes that the task will also be tagged with
        an appropriate @username tag (by the caller; we don't do it for you!)

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

    @classmethod
    def reassign_task_to_user(
        cls,
        task_pk: int,
        *,
        new_username: str,
        calling_user: User,
        unassign_others: bool = False,
    ) -> None:
        """Reassign a task to a different user.

        If tasks status is "COMPLETE" then the assigned_user will be updated.
        If it is "OUT" or "TO_DO", then assigned user will be set to None
        and the task will be tagged with an appropriate @username tag.

        Note: this looks superficially like :method:`assign_task_to_user` but
        its used in a different way.  That method is about claiming tasks.
        This current method is most useful for "unclaiming" tasks, and pushing
        them toward a different user.

        Args:
            task_pk: the primary key of a task.

        Keyword Args:
            new_username: a string of a username to reassign to.
            calling_user: the user who is doing the reassigning.
            unassign_others: untag any other users assigned to this task,
                defaults to False.

        Returns:
            None.

        Raises:
            ValueError: cannot find user, or cannot find marking task.
            serializers.ValidationError: tag name failure, unexpected as
                we make the tag.
        """
        with transaction.atomic():
            # first reassign the task - this checks if the username
            # corresponds to an existing marker-user
            cls._reassign_task_to_user(task_pk, new_username)
            cls._tag_task_pk_for_user(
                task_pk, new_username, calling_user, unassign_others
            )
