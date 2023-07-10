# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from Identify.models import PaperIDTask, PaperIDAction
from Identify.services import IdentifyTaskService
from Papers.models import IDPage, Image, Paper


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
        for id_paper in identified_papers.values():
            if id_paper is not None:
                identified_papers_count += 1
            else:
                identified_papers_count = identified_papers_count
        return identified_papers_count

    @transaction.atomic
    def get_all_identified_papers(self, all_scanned_id_papers):
        # TODO: Needs to optimize this
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

    @transaction.atomic
    def set_id__task_todo_and_clear_specific_id(self, paper_pk):
        paper_ID_task_obj = PaperIDTask.objects.get(paper=paper_pk)
        paper_ID_task_obj.status = PaperIDTask.TO_DO
        paper_ID_task_obj.save()

        sid = PaperIDAction.objects.get(task=paper_ID_task_obj.pk)
        sid.delete()

    @transaction.atomic
    def set_id__task_todo_and_clear_specific_id_cmd(self, paper_number):
        paper = Paper.objects.get(paper_number=int(paper_number))
        self.set_id__task_todo_and_clear_specific_id(paper.pk)

    @transaction.atomic
    def set_all_id__task_todo_and_clear_all_id_cmd(self):
        for paper_id_task in PaperIDTask.objects.all():
            paper_id_task.status = PaperIDTask.TO_DO
            paper_id_task.save()
            
        PaperIDAction.objects.all().delete()
