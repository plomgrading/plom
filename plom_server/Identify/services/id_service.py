# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Natalie Balashov

from typing import Dict, Union

from django.db import transaction
from django.db.models import QuerySet

from Identify.models import PaperIDTask, PaperIDAction
from Identify.services import IdentifyTaskService
from Papers.models import IDPage, Image, Paper


class IDService:
    """Functions for Identify HTML page."""

    @transaction.atomic
    def get_all_id_papers(self) -> QuerySet[IDPage]:
        """Get all the ID papers.

        Returns:
            A PolymorphicQuerySet of all IDPage objects that is iterable.

        Raises:
            Not expected to raise any exceptions.
        """
        return IDPage.objects.all().order_by("paper")

    @transaction.atomic
    def get_id_papers(self) -> QuerySet[IDPage]:
        """Get all the scanned ID papers.

        Returns:
            A PolymorphicQuerySet of all scanned IDPage objects that is iterable.

        Raises:
            Not expected to raise any exceptions.
        """

        return IDPage.objects.exclude(image=None).order_by("paper")

    @transaction.atomic
    def get_no_id_papers(self) -> QuerySet[IDPage]:
        """Get all the unscanned ID papers.

        Returns:
            A PolymorphicQuerySet of all unscanned IDPage objects that is iterable.

        Raises:
            Not expected to raise any exceptions.
        """
        return IDPage.objects.exclude(image__isnull=False)

    @transaction.atomic
    def get_id_image_object(self, image_pk: int) -> Union[Image, None]:
        """Get the ID page image based on the image's pk value.

        Args:
            image_pk: The primary key of an image.

        Returns:
            The Image object if it exists,
            or None if the Image does not exist.

        Note:
            If the Image does not exist, the function will return None
            instead of raising the ObjectDoesNotExist exception.
        """
        try:
            id_image_obj = Image.objects.get(pk=image_pk)
            return id_image_obj
        except Image.DoesNotExist:
            return None

    @transaction.atomic
    def get_identified_papers_count(self) -> int:
        return PaperIDTask.objects.filter(status=PaperIDTask.COMPLETE).count()


    @transaction.atomic
    def get_all_identified_papers(
        self, all_scanned_id_papers: QuerySet[IDPage]
    ) -> Dict:
        """Get all the identified paper instances as a dictionary.

        This method is to help with getting all the correct instances to display
        into Identifying progress view, such as IDPage and PaperIDAction model.

        Args:
            all_scanned_id_papers (PolymorphicQuerySet): A collection of all
                the scanned IDPage objects that is iterable.

        Returns:
            dict: A dictionary of all the PaperIDAction(Value) corresponding with IDPage(key).

        Note:
            If PaperIDTask does not exist, the dictionary value corresponding with IDPage(key)
            will be None instead of raising the ObjectDoesNotExist exception.
        """
        # TODO: Needs to optimize this
        completed_id_task_list = {}
        for scanned_id_paper in all_scanned_id_papers:
            try:
                completed_id_paper_task = PaperIDTask.objects.get(
                    paper=scanned_id_paper.paper.pk, status=PaperIDTask.COMPLETE
                )
                completed_id_task_list[scanned_id_paper] = completed_id_paper_task
            except PaperIDTask.DoesNotExist:
                completed_id_task_list[scanned_id_paper] = None

        for id_paper, id_task in completed_id_task_list.items():
            if not id_task:
                continue
            latest_id_result = IdentifyTaskService().get_latest_id_results(task=id_task)
            completed_id_task_list.update({id_paper: latest_id_result})

        return completed_id_task_list

    @transaction.atomic
    def set_id_task_todo_and_clear_specific_id(self, paper_pk: int) -> None:
        """Set PaperIDTask as TO_DO and clear the PaperIDAction corresponding for that task.

        Args:
            paper_pk: The primary key of a paper.

        Returns:
            None

        Raises:
            ObjectDoesNotExist: This is raised when an instance of the PaperIDTask or
                PaperIDAction does not exist.
        """
        paper_ID_task_obj = PaperIDTask.objects.get(paper=paper_pk)
        sid = PaperIDAction.objects.get(task=paper_ID_task_obj.pk)

        paper_ID_task_obj.status = PaperIDTask.TO_DO
        paper_ID_task_obj.save()

        sid.delete()

    @transaction.atomic
    def set_id_task_todo_and_clear_specific_id_cmd(self, paper_number: int) -> None:
        """Set PaperIDTask as TO_DO and clear the PaperIDAction corresponding for that task.

        This method is used in ``clear_id.py``.

        Args:
            paper_number: The paper number of a paper.

        Returns:
            None

        Raises:
            ObjectDoesNotExist: This is raised when an instance of the Paper or PaperIDTask or
                PaperIDAction does not exist.
        """
        paper = Paper.objects.get(paper_number=int(paper_number))
        self.set_id_task_todo_and_clear_specific_id(paper.pk)

    @transaction.atomic
    def set_all_id_task_todo_and_clear_all_id_cmd(self) -> None:
        """Set all the PaperIDTask as TO_DO and clear all the PaperIDAction.

        This method is used in the ``clear_id.py``.
        """
        for paper_id_task in PaperIDTask.objects.all():
            paper_id_task.status = PaperIDTask.TO_DO
            paper_id_task.save()

        PaperIDAction.objects.all().delete()

    # @transaction.atomic:
    # def get_all_paper_id_info(self) -> Dict:
        # for paper_obj in Paper.objects.all():
