# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2023-2024 Colin B. Macdonald

from __future__ import annotations

import pathlib
from typing import Any
from warnings import warn

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from ..models import PaperIDTask, IDPrediction
from ..services import IdentifyTaskService
from Papers.models import IDPage, Paper
from Scan.services.image_process import PageImageProcessor


class IDReaderService:
    """Functions for ID reading and related helper functions."""

    @transaction.atomic
    def get_id_box_cmd(
        self,
        box: None | tuple[float, float, float, float],
        *,
        dur: pathlib.Path | None = None,
    ) -> dict[int, pathlib.Path]:
        """Extract the id box, or really any rectangular part of the id page, rotation corrected.

        Args:
            box: A list of the box to extract or a default if ``None``.
                This is of the form "top bottom left right", each how
                much of the page as a float ``[0.0, 1.0]``.

        Keyword Args:
            dur: what directory to save to, or a default if omitted.

        Returns:
            dict: a dict of paper_number -> ID box path and filename (temporary)
        """
        if not dur:
            id_box_folder = settings.MEDIA_ROOT / "id_box_images"
        else:
            id_box_folder = pathlib.Path(dur)
        if not box:
            box = (0.1, 0.9, 0.0, 1.0)
        id_box_folder.mkdir(exist_ok=True, parents=True)

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

    def get_already_matched_sids(self) -> list:
        """Return the list of all student IDs that have been matched with a paper."""
        sid_list = []
        id_task_service = IdentifyTaskService()
        IDed_tasks = PaperIDTask.objects.filter(status=PaperIDTask.COMPLETE)
        for task in IDed_tasks:
            latest = id_task_service.get_latest_id_results(task)
            if latest:
                sid_list.append(latest.student_id)
        return sid_list

    def get_unidentified_papers(self) -> list:
        """Return a list of all unidentified papers."""
        paper_list = []
        not_IDed_tasks = PaperIDTask.objects.filter(status=PaperIDTask.TO_DO)
        for task in not_IDed_tasks:
            paper_list.append(task.paper.paper_number)
        return paper_list

    @transaction.atomic
    def get_ID_predictions(
        self, predictor: str | None = None
    ) -> dict[int, dict[str, Any]] | dict[int, list[dict[str, Any]]]:
        """Get ID predictions for a particular predictor, or all predictions if no predictor specified.

        Keyword Args:
            predictor: predictor whose predictions are returned.
                If None, all predictions are returned.

        Returns:
            If returning all predictions, a dict of lists of dicts.
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
            return predictions

        # else we want all predictors
        allpred: dict[int, list[dict[str, Any]]] = {}
        pred_query = IDPrediction.objects.all()
        for pred in pred_query:
            if allpred.get(pred.paper.paper_number) is None:
                allpred[pred.paper.paper_number] = []
            allpred[pred.paper.paper_number].append(
                {
                    "student_id": pred.student_id,
                    "certainty": pred.certainty,
                    "predictor": pred.predictor,
                }
            )
        return allpred

    @transaction.atomic
    def add_or_change_ID_prediction(
        self,
        user: User,
        paper_num: int,
        student_id: str,
        certainty: float,
        predictor: str,
    ) -> None:
        """Add a new ID prediction or change an existing prediction in the DB.

        Also update the `iding_priority` field for the relevant PaperIDTask.

        Args:
            user: user associated with te prediction.
            paper_num: number of the paper whose prediction is updated.
            student_id: predicted student ID.
            certainty: confidence value to associate with the prediction.
            predictor: identifier for type of prediction.
        """
        paper = Paper.objects.get(paper_number=paper_num)
        try:
            existing_pred = IDPrediction.objects.get(paper=paper, predictor=predictor)
        except IDPrediction.DoesNotExist:
            existing_pred = None
        if not existing_pred:
            new_prediction = IDPrediction(
                user=user,
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

        id_task_service = IdentifyTaskService()
        id_task_service.update_task_priority(paper)

    def add_or_change_ID_prediction_cmd(
        self,
        username: str,
        paper_num: int,
        student_id: str,
        certainty: float,
        predictor: str,
    ) -> None:
        """Wrapper around add_or_change_ID_prediction for use by the management command-line tool.

        Checks whether username is valid and fetches the corresponding User from the DB.

        Args:
            username: the username to associate with the new prediction.
            paper_num: the paper number of the ID page whose ID prediction to add/change.
            student_id: the student ID with which to update the predictions in the DB.
            certainty: the confidence value associated with the prediction.
            predictor: identifier defining the type of prediction that is being added/changed.

        Raises:
            ValueError: if the username provided is not valid, or is not part of the manager group.
        """
        try:
            user = User.objects.get(username__iexact=username, groups__name="manager")
        except ObjectDoesNotExist as e:
            raise ValueError(
                f"User '{username}' does not exist or has wrong permissions!"
            ) from e
        self.add_or_change_ID_prediction(
            user, paper_num, student_id, certainty, predictor
        )

    @transaction.atomic
    def delete_ID_predictions(self, predictor: str | None = None) -> None:
        """Delete all ID predictions from a particular predictor."""
        if predictor:
            IDPrediction.objects.filter(predictor=predictor).delete()
        else:
            IDPrediction.objects.all().delete()

    def add_prename_ID_prediction(
        self, user: User, student_id: str, paper_number: int
    ) -> None:
        """Add ID prediction for a prenamed paper."""
        self.add_or_change_ID_prediction(user, paper_number, student_id, 0.9, "prename")
