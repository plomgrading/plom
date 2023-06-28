# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from Identify.models import PaperIDTask
from Identify.services import IdentifyTaskService
from Papers.models import IDPage, Image


class IDService:
    """Functions for Identify HTML page."""

    @transaction.atomic
    def get_all_id_papers(self):
        return IDPage.objects.all().order_by("paper")

    @transaction.atomic
    def get_id_papers(self):
        return IDPage.objects.exclude(image=None).order_by("paper")

    @transaction.atomic
    def get_no_id_papers(self):
        return IDPage.objects.exclude(image__isnull=False)

    @transaction.atomic
    def get_id_image_object(self, image_pk):
        try:
            id_image_obj = Image.objects.get(pk=image_pk)
            return id_image_obj
        except Image.DoesNotExist:
            return None
    
    @transaction.atomic
    def get_identified_papers_count(self, identified_papers):
        identified_papers_count = 0
        for i in identified_papers.values():
            if i is not None:
                identified_papers_count += 1
            else:
                identified_papers_count = identified_papers_count
        return identified_papers_count

    @transaction.atomic
    def get_all_identified_papers(self, all_scanned_id_papers):
        # TODO: Future needs to optimize this
        completed_id_task_list = {}
        for scanned_id_paper in all_scanned_id_papers:
            try:
                IDed_paper_task = PaperIDTask.objects.get(
                    paper=scanned_id_paper.paper.pk, status=PaperIDTask.COMPLETE
                )
                completed_id_task_list[scanned_id_paper] = IDed_paper_task
            except ObjectDoesNotExist:
                completed_id_task_list[scanned_id_paper] = None

        for id_paper, id_task in completed_id_task_list.items():
            latest_id_result = IdentifyTaskService().get_latest_id_results(task=id_task)
            completed_id_task_list.update({id_paper: latest_id_result})

        return completed_id_task_list
