# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2023 Colin B. Macdonald

import pathlib
from warnings import warn

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from Identify.models import PaperIDTask, IDPrediction
from Identify.services import IdentifyTaskService
from Papers.models import IDPage, Paper
from Preparation.services import StagingStudentService
from Scan.services.image_process import PageImageProcessor


class IDReaderService:
    """Functions for ID reading and related helper functions."""

    @transaction.atomic
    def get_id_box_cmd(self, box, *, dur=None):
        """Extract the id box, or really any rectangular part of the id page, rotation corrected.

        Args:
            box (None/list): the box to extract or a default is empty/None.

        Keyword Args:
            dur (None/pathlib.Path): what directory to save to, or choose
                a internal default if omitted.

        Returns:
            dict: a dict of paper_number -> ID box filename (temporary)
        """
        if not dur:
            id_box_folder = settings.MEDIA_ROOT / "id_box_images"
        else:
            id_box_folder = pathlib.Path(dur)
        if not box:
            box = (0.28, 0.58, 0.09, 0.91)
        id_box_folder.mkdir(exist_ok=True)

        pipr = PageImageProcessor()
        id_pages = IDPage.objects.all()

        img_file_dict = {}
        for id_img in id_pages:
            if id_img.image and id_img.image.parsed_qr:
                img_path = id_img.image.image_file.path
                orientation = id_img.image.rotation
                qr_data = id_img.image.parsed_qr
                if len(qr_data) != 3:
                    warn(
                        "Fewer than 3 QR codes found, "
                        f"cannot extract ID box from paper {id_img.paper.paper_number}."
                    )
                    continue
                id_box = pipr.extract_rect_region(img_path, orientation, qr_data, *box)
                id_box_filename = (
                    id_box_folder / f"id_box_{id_img.paper.paper_number:04}.png"
                )
                id_box.save(id_box_filename)
                img_file_dict[id_img.paper.paper_number] = id_box_filename
        return img_file_dict

    def get_already_matched_sids(self):
        """Return the list of all student IDs that have been matched with a paper."""
        sid_list = []
        id_task_service = IdentifyTaskService()
        IDed_tasks = PaperIDTask.objects.filter(status=PaperIDTask.COMPLETE)
        for task in IDed_tasks:
            latest = id_task_service.get_latest_id_results(task)
            if latest:
                sid_list.append(latest.student_id)
        return sid_list

    def get_unidentified_papers(self):
        """Return a list of all unidentified papers."""
        paper_list = []
        not_IDed_tasks = PaperIDTask.objects.filter(status=PaperIDTask.TO_DO)
        for task in not_IDed_tasks:
            paper_list.append(task.paper.paper_number)
        return paper_list

    def get_classlist_sids_for_ID_matching(self):
        """Returns a list containing all student IDs on the classlist."""
        students = []
        student_service = StagingStudentService()
        classlist = student_service.get_students()
        for entry in classlist:
            students.append(entry.pop("student_id"))
        return students

    @transaction.atomic
    def get_ID_predictions(self, predictor=None):
        """Get ID predictions for a particular predictor, or all predictions if no predictor specified.

        Keyword Args:
            predictor (str): predictor whose predictions are returned.
                If None, all predictions are returned.

        Returns:
            dict: if returning all predictions, a dict of lists of dicts.
                If returning predictions for a specific predictor, a dict of dicts.
                Inner-most dicts contain prediction info (ie. SID, certainty, predictor).
                Outer-most dict is keyed by paper number.
        """
        predictions = {}
        if predictor:
            pred_query = IDPrediction.objects.filter(predictor=predictor)
            for pred in pred_query:
                predictions[pred.paper.paper_number] = {
                    "student_id": pred.student_id,
                    "certainty": pred.certainty,
                    "predictor": pred.predictor,
                }
        else:
            pred_query = IDPrediction.objects.all()
            for pred in pred_query:
                if predictions.get(pred.paper.paper_number) is None:
                    predictions[pred.paper.paper_number] = []
                predictions[pred.paper.paper_number].append(
                    {
                        "student_id": pred.student_id,
                        "certainty": pred.certainty,
                        "predictor": pred.predictor,
                    }
                )
        return predictions

    @transaction.atomic
    def add_or_change_ID_prediction(
        self, user, paper_num, student_id, certainty, predictor
    ):
        """Add a new ID prediction or change an existing prediction in the DB."""
        try:
            # TODO: hardcoded to use "first" manager user in DB
            user_obj = User.objects.filter(groups__name="manager").first()
        except ObjectDoesNotExist:
            raise ValueError(f"Manager user '{username}' does not exist")
        paper = Paper.objects.get(paper_number=paper_num)
        try:
            existing_pred = IDPrediction.objects.get(paper=paper, predictor=predictor)
        except IDPrediction.DoesNotExist:
            existing_pred = None
        if not existing_pred:
            new_prediction = IDPrediction(
                user=user_obj,
                paper=paper,
                predictor=predictor,
                student_id=student_id,
                certainty=certainty,
            )
            new_prediction.save()
        else:
            existing_pred.student_id = student_id
            existing_pred.certainty = certainty
            existing_pred.save()

    @transaction.atomic
    def delete_ID_predictions(self, user, predictor=None):
        """Delete all ID predictions from a particular predictor."""
        if predictor:
            prediction = IDPrediction.objects.filter(predictor=predictor).delete()
        else:
            prediction = IDPrediction.objects.all().delete()
