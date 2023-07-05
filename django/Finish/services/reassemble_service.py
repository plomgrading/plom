# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates

from django.utils import timezone

from Identify.models import PaperIDTask, PaperIDAction
from Mark.models import MarkingTask, Annotation
from Mark.services import MarkingTaskService
from Papers.models import Paper
from Papers.services import SpecificationService
from Preparation.services import PQVMappingService


class ReassembleService:
    """Class that contains helper functions for sending data to plom-finish."""

    def is_paper_marked(self, paper):
        """Return True if all of the marking tasks are completed.

        Args:
            paper: a reference to a Paper instance
        """
        paper_tasks = MarkingTask.objects.filter(paper=paper)
        completed_tasks = paper_tasks.filter(status=MarkingTask.COMPLETE)
        ood_tasks = paper_tasks.filter(status=MarkingTask.OUT_OF_DATE)
        return (
            completed_tasks.count() > 0
            and completed_tasks.count() + ood_tasks.count() == paper_tasks.count()
        )

    def get_last_updated_timestamp(self, paper):
        """Return the latest update timestamp from the IDActions or Annotations.

        Args:
            paper: a reference to a Paper instance
        """
        if self.get_paper_id_or_none(paper):
            paper_id_task = PaperIDTask.objects.get(paper=paper)
            paper_id_actions = PaperIDAction.objects.filter(task=paper_id_task)
            latest_action_instance = paper_id_actions.order_by("-time").first()
            latest_action = latest_action_instance.time
        else:
            latest_action = None

        if self.is_paper_marked(paper):
            paper_annotations = Annotation.objects.filter(task__paper=paper)
            latest_annotation_instance = paper_annotations.order_by("-time_of_last_update").first()
            latest_annotation = latest_annotation_instance.time_of_last_update
        else:
            latest_annotation = None

        if latest_action and latest_annotation:
            return max(latest_annotation, latest_action)
        elif latest_action:
            return latest_action
        elif latest_annotation:
            return latest_annotation
        else:
            # TODO: default to the current date for the time being
            return timezone.now()

    def get_paper_id_or_none(self, paper):
        """Return a tuple of (student ID, student name) if the paper has been identified. Otherwise, return None.

        Args:
            paper: a reference to a Paper instance

        Returns:
            a tuple (str, str) or None
        """
        paper_task = PaperIDTask.objects.filter(paper=paper).order_by("-time")
        if paper_task.count() == 0:
            return None
        latest_task = paper_task.first()
        if latest_task.status != PaperIDTask.COMPLETE:
            return None
        action = PaperIDAction.objects.get(task=latest_task)
        return action.student_id, action.student_name

    def paper_spreadsheet_dict(self, paper):
        """Return a dictionary representing a paper for the reassembly spreadsheet.

        Args:
            paper: a reference to a Paper instance
        """
        paper_dict = {}

        paper_id_info = self.get_paper_id_or_none(paper)
        if paper_id_info:
            student_id, student_name = paper_id_info
            paper_dict["sid"] = student_id
            paper_dict["sname"] = student_name
        else:
            paper_dict["sid"] = ""
            paper_dict["sname"] = ""
        paper_dict["identified"] = paper_id_info is not None

        n_questions = SpecificationService().get_n_questions()
        paper_marked = self.is_paper_marked(paper)
        if paper_marked:
            mts = MarkingTaskService()
            for i in range(1, n_questions + 1):
                annotation = mts.get_latest_annotation(paper.paper_number, i)
                paper_dict[f"q{i}m"] = annotation.score
        else:
            for i in range(1, n_questions + 1):
                paper_dict[f"q{i}m"] = 0
        qvmap = PQVMappingService().get_pqv_map_dict()
        for i in range(1, n_questions + 1):
            paper_dict[f"q{i}v"] = qvmap[paper.paper_number]
        paper_dict["marked"] = paper_marked

        paper_dict["last_update"] = self.get_last_updated_timestamp(paper)
        return paper_dict

    def get_spreadsheet_data(self):
        """Return a dictionary with all of the required data for a reassembly spreadsheet."""
        spreadsheet_data = {}
        papers = Paper.objects.all()
        for paper in papers:
            spreadsheet_data[paper.paper_number] = self.paper_spreadsheet_dict(paper)
        return spreadsheet_data

    def get_identified_papers(self):
        """Return a dictionary with all of the identified papers and their names and IDs.

        Returns:
            dictionary: keys are paper numbers, values are a list of [str, str]
        """
        spreadsheet_data = {}
        papers = Paper.objects.all()
        for paper in papers:
            paper_id_info = self.get_paper_id_or_none(paper)
            if paper_id_info:
                student_id, student_name = paper_id_info
                spreadsheet_data[paper.paper_number] = [student_id, student_name]
        return spreadsheet_data
