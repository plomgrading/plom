# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2020-2026 Colin B. Macdonald
# Copyright (C) 2024-2025 Andrew Rechnitzer
# Copyright (C) 2024-2025 Deep Shah

import json
from pathlib import Path
from typing import Any, Iterable

import cv2 as cv

# import cv2.typing - problems importing this - see MR 3050.
import numpy as np
from scipy.optimize import linear_sum_assignment

import onnxruntime  # type: ignore

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db import transaction
from django_huey import db_task
import huey
import huey.api

from plom.idreader.model_utils import (
    load_model,
    is_model_present,
    ensure_model_available,
)
from plom_server.Base.models import HueyTaskTracker
from plom_server.Papers.models import Paper
from plom_server.Papers.services import SpecificationService, PaperInfoService
from plom_server.Preparation.services import StagingStudentService
from plom_server.Rectangles.services import RectangleExtractor
from ..models import PaperIDTask, IDPrediction, IDReadingHueyTaskTracker
from ..services import IdentifyTaskService, ClasslistService


# the default certainty of prenaming predictions
_default_prenaming_prediction_confidence = 0.9


class IDReaderService:
    """Functions for ID reading and related helper functions."""

    default_prenaming_prediction_confidence = _default_prenaming_prediction_confidence

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

    def get_prenamed_paper_numbers(self) -> list[int]:
        return list(
            IDPrediction.objects.filter(predictor="prename").values_list(
                "paper__paper_number", flat=True
            )
        )

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
            for pred in (
                IDPrediction.objects.filter(predictor=predictor)
                .order_by("paper__paper_number")
                .prefetch_related("paper")
            ):
                predictions[pred.paper.paper_number] = {
                    "student_id": pred.student_id,
                    "certainty": pred.certainty,
                    "predictor": pred.predictor,
                }
            return predictions

        # else we want all predictors
        allpred: dict[int, list[dict[str, Any]]] = {}
        for pred in (
            IDPrediction.objects.all()
            .order_by("paper__paper_number")
            .prefetch_related("paper")
        ):
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

        IdentifyTaskService.update_task_priority(paper)

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

    @staticmethod
    def delete_ID_predictions(predictor: str | None = None) -> None:
        """Delete all ID predictions, or optionally all from a particular predictor."""
        if predictor:
            IDPrediction.objects.filter(predictor=predictor).delete()
        else:
            IDPrediction.objects.all().delete()

    @classmethod
    def delete_all_ML_ID_predictions(cls) -> None:
        """Delete all ID predictions related to machine-learning methods."""
        for predictor_name in cls.all_ML_ID_predictor_names():
            cls.delete_ID_predictions(predictor_name)

    @staticmethod
    def all_ML_ID_predictor_names() -> Iterable[str]:
        return ("MLLAP", "MLGreedy", "MLBestGuess")

    @staticmethod
    def bulk_add_or_update_prename_ID_predictions(
        user: User,
        papers: list[Paper],
    ) -> None:
        """Update the system for changes to prenamed papers.

        Args:
            user: who should new prenames be associated with. Any
                existing prenames are updated with this user.
            papers: a list of Paper objects that have been updated
                (elsewhere in the system - eg ID page uploaded or changed)
                and so need their prename-predictions updated.
        """
        # get dict of all prenamed papers (as per classlist)
        prenamed_papers = StagingStudentService.get_prenamed_papers()

        # find existing prename-predictions from these papers
        existing_prename_prediction = {}
        for pred in IDPrediction.objects.filter(
            predictor="prename", paper__in=papers
        ).prefetch_related("paper"):
            existing_prename_prediction[pred.paper.paper_number] = pred

        # mapping of any existing predictions (not just prenames) from these papers
        existing_all_predictions_for_paper: dict[int, list[IDPrediction]] = {}
        for pred in IDPrediction.objects.filter(paper__in=papers).prefetch_related(
            "paper"
        ):
            try:
                existing_all_predictions_for_paper[pred.paper.paper_number].append(pred)
            except KeyError:
                existing_all_predictions_for_paper[pred.paper.paper_number] = [pred]

        # loop over papers making two lists: things to make and things to update
        new_predictions = []
        predictions_to_update = []
        for paper in papers:
            # check if paper is actually prenamed.
            if paper.paper_number not in prenamed_papers:
                continue
            if paper.paper_number in existing_prename_prediction.keys():
                pred = existing_prename_prediction[paper.paper_number]
                pred.student_id = prenamed_papers[paper.paper_number][0]
                pred.user = user  # update the associated user too.
                predictions_to_update.append(pred)
            else:
                # this does not immediately create a DB entry, we do it in bulk later
                new_predictions.append(
                    IDPrediction(
                        user=user,
                        paper=paper,
                        predictor="prename",
                        student_id=prenamed_papers[paper.paper_number][0],
                        certainty=_default_prenaming_prediction_confidence,
                    )
                )
        # now update the priorities of the associated IDtasks
        # note that the updated IDPredictions did not change certainties, so
        # they don't change the associated priorities
        priority_updates = []
        for task in PaperIDTask.objects.filter(paper__in=papers).prefetch_related(
            "paper"
        ):
            n = task.paper.paper_number
            try:
                # the minimum of all predictions determines the overall confidence
                c = min([X.certainty for X in existing_all_predictions_for_paper[n]])
            except KeyError:
                c = _default_prenaming_prediction_confidence
            task.iding_priority = c
            # no idt_obj.save() here b/c we are deferring these for a bulk change
            priority_updates.append(task)
        # Finally actually create + update all the predictions and tasks
        with transaction.atomic():
            IDPrediction.objects.bulk_update(
                predictions_to_update, ["student_id", "user"]
            )
            IDPrediction.objects.bulk_create(new_predictions)
            # Some existing ID tasks will need their priorities updated too.
            PaperIDTask.objects.bulk_update(priority_updates, ["iding_priority"])

    def run_the_id_reader_in_foreground(
        self,
        user: User,
        box_versions: dict[int, dict[str, float] | None],
        *,
        recompute_heatmap: bool = True,
    ):
        id_box_image_dict = IDBoxProcessorService().save_all_id_boxes(box_versions)
        IDBoxProcessorService().make_id_predictions(
            user, id_box_image_dict, recompute_heatmap=recompute_heatmap
        )

    def get_id_reader_background_task_status(self):
        try:
            idht_obj = IDReadingHueyTaskTracker.objects.exclude(obsolete=True).get()
        except ObjectDoesNotExist:
            return {"status": "To Do", "message": "ID reader has not been run."}

        return {"status": idht_obj.get_status_display(), "message": idht_obj.message}

    def run_the_id_reader_in_background_via_huey(
        self,
        user: User,
        box_versions: dict[int, dict[str, float] | None],
        recompute_heatmap: bool | None = True,
    ):
        """Run the ID reading process in the background.

        Raises:
            MultipleObjectsReturned: if the user tries to run multiple such tasks.
        """
        # Note that we should only have 1 task running at a time.
        # if there is already one then check its status carefully
        # Note that the status should never be TO_DO since this
        # is the only function that creates the tracker and only
        # does so in state STARTING
        try:
            idht_obj = IDReadingHueyTaskTracker.objects.exclude(obsolete=True).get()
            # if its status is STARTING, QUEUD, RUNNING, then do not create a
            # new task - return a "Hey it is already running error."
            if idht_obj.status in [
                HueyTaskTracker.STARTING,
                HueyTaskTracker.QUEUED,
                HueyTaskTracker.RUNNING,
            ]:
                raise MultipleObjectsReturned(
                    "Can only have 1 running ID reading process at a time."
                )
            # if the task is complete or error then set it as obsolete
            if idht_obj.status in [HueyTaskTracker.COMPLETE, HueyTaskTracker.ERROR]:
                with transaction.atomic(durable=True):
                    idht_obj.set_as_obsolete()
        except ObjectDoesNotExist:
            # there is no existing non-obsolete tracker, so pass
            # we'll create one in a moment.
            pass
        # now we create a new tracker.
        new_idht = IDReadingHueyTaskTracker.objects.create(
            status=HueyTaskTracker.STARTING, message="ID reading task queued."
        )
        tracker_pk = new_idht.pk
        # now build the actual huey task
        res = huey_id_reading_task(
            user,
            box_versions,
            recompute_heatmap=recompute_heatmap,
            tracker_pk=tracker_pk,
        )
        # and update the status
        HueyTaskTracker.transition_to_queued_or_running(tracker_pk, res.id)


# The decorated function returns a ``huey.api.Result``
@db_task(queue="chores", context=True)
def huey_id_reading_task(
    user: User,
    box_versions: dict[int, tuple[float, float, float, float] | None],
    recompute_heatmap: bool,
    *,
    tracker_pk: int,
    task: huey.api.Task | None = None,
) -> bool:
    """Run the id reading process in the background via Huey.

    It is important to understand that running this function starts an
    async task in queue that will run sometime in the future.

    Args:
        user: the user who triggered this process and so who will be associated with the predictions.
        box_versions: a dict keyed by version of the coordinates of the ID box to extract.
        recompute_heatmap: whether or not to recompute the digit probability heatmap.

    Keyword Args:
        tracker_pk: a key into the database for anyone interested in
            our progress.
        task: includes our ID in the Huey process queue.  This kwarg is
            passed by `context=True` in decorator: callers should not
            pass this in!

    Returns:
        True, no meaning, just as per the Huey docs: "if you need to
        block or detect whether a task has finished".
    """
    assert task is not None
    HueyTaskTracker.transition_to_running(tracker_pk, task.id)
    IDReadingHueyTaskTracker.set_message_to_user(
        tracker_pk, "ID Reading task has started. Getting ID boxes."
    )

    id_box_image_dict = IDBoxProcessorService().save_all_id_boxes(box_versions)
    # check if we got any ID boxes (eg no scanned papers, or all prenamed)
    if len(id_box_image_dict) == 0:
        IDReadingHueyTaskTracker.set_message_to_user(
            tracker_pk, "No ID-boxes found. Cannot make predictions."
        )
        HueyTaskTracker.transition_to_complete(tracker_pk)
        return True

    IDReadingHueyTaskTracker.set_message_to_user(
        tracker_pk, "ID boxes from page images saved. Computing predictions."
    )

    try:
        IDBoxProcessorService().make_id_predictions(
            user, id_box_image_dict, recompute_heatmap=recompute_heatmap
        )
    except ValueError as e:
        HueyTaskTracker.transition_chore_to_error(
            tracker_pk, f"Did you upload a classlist?  {e}"
        )
        return True

    IDReadingHueyTaskTracker.set_message_to_user(tracker_pk, "ID predictions complete.")

    HueyTaskTracker.transition_to_complete(tracker_pk)
    return True


class IDBoxProcessorService:
    """Service for dealing with the ID box and processing it into ID predictions."""

    @transaction.atomic
    def save_all_id_boxes(
        self,
        box_versions: dict[int, dict[str, float] | None],
        *,
        exclude_prenamed_papers: bool = True,
        save_dir: Path | None = None,
    ) -> dict[int, Path]:
        """Extract the id box, or really any rectangular part of the id page.

        Notice that this code makes use of the general 'extract a rectangle' code
        and so uses qr-code positions to rotate and find the given rectangle.

        Args:
            box_versions: A dict keyed by version of dict giving coords
                of the box to extract. Dict of coords has keys 'left_f', 'right_f',
                'top_f', 'bottom_f', with float values.

        Keyword Args:
            exclude_prenamed_papers: by default we don't extract the id
                box from prenamed papers.
            save_dir: what directory to save to, or a default if omitted.

        Returns:
            dict: a dict of paper_number -> ID box path and filename (temporary)
        """
        if not save_dir:
            id_box_folder = settings.MEDIA_ROOT / "id_box_images"
        else:
            id_box_folder = Path(save_dir)
        id_box_folder.mkdir(exist_ok=True, parents=True)
        # get the ID page-number and the papers which have it scanned.
        id_page_number = SpecificationService.get_id_page_number()
        # but exclude any prenamed papers
        if exclude_prenamed_papers:
            exclude_papers = IDReaderService().get_prenamed_paper_numbers()
        else:
            exclude_papers = []
        # Note this gets all id pages regardless of version
        img_file_dict = {}
        for v, box_as_dict in box_versions.items():
            # do each id page version separately
            if box_as_dict is None:
                # if no box for that version then skip it.
                continue
            box = [
                box_as_dict["left_f"],
                box_as_dict["top_f"],
                box_as_dict["right_f"],
                box_as_dict["bottom_f"],
            ]
            paper_numbers = [
                pn
                for pn in PaperInfoService.get_paper_numbers_containing_page(
                    id_page_number, version=v, scanned=True
                )
                if pn not in exclude_papers
            ]
            # use the rectangle extractor to then get all the rectangles from those pages and save them
            rex = RectangleExtractor(v, id_page_number)
            for pn in paper_numbers:
                id_box_filename = id_box_folder / f"id_box_{pn:04}.png"
                id_box_bytes = rex.extract_rect_region(pn, *box)
                if id_box_bytes is None:
                    # just leave them out when rex cannot compute appropriate transforms
                    continue
                id_box_filename.write_bytes(id_box_bytes)
                img_file_dict[pn] = id_box_filename

        return img_file_dict

    # problem with cv2.typing - see MR 3050.
    # comment out the cv2.typing.MatLike hint here.
    # TODO - fix the cv2.typing issue in dev sometime.
    def resize_ID_box_and_extract_digit_strip(self, id_box_file: Path):
        # ) -> cv2.typing.MatLike | None:
        """Extract the strip of digits from the ID box from the given image file."""
        # WARNING: contains many magic numbers - must be updated if the IDBox
        # template is changed.
        template_id_box_width = 1250
        # read the given file into an np.array.
        id_box = cv.imread(str(id_box_file))
        assert id_box is not None, f"Unexpectedly could not read id box {id_box_file}"
        assert len(id_box.shape) in (2, 3), f"Unexpected numpy shape {id_box.shape}"
        # third entry 1 (grayscale) or 3 (colour)
        height: int = id_box.shape[0]
        width: int = id_box.shape[1]
        if height < 32 or width < 32:  # check if id_box is too small
            return None
        # scale height to retain aspect ratio of image
        new_height = int(template_id_box_width * height / width)
        scaled_id_box = cv.resize(
            id_box, (template_id_box_width, new_height), interpolation=cv.INTER_CUBIC
        )
        # extract the top strip of the IDBox template
        # which only contains the digits
        return scaled_id_box[25:130, 355:1230]

    # note that numpy and mypy typing don't always play nicely together
    # thankfully cv2 has some typing that will take care of us passing
    # these images as np arrays.
    # see https://stackoverflow.com/questions/73260250/how-do-i-type-hint-opencv-images-in-python
    # problem with cv2.typing - see MR 3050.
    # comment out the cv2.typing.MatLike hint here.
    # TODO - fix the cv2.typing issue in dev sometime.
    def get_digit_images(
        # self, ID_box: cv.typing.MatLike, num_digits: int
        # ) -> list[cv.typing.MatLike]:
        self,
        ID_box,
        num_digits: int,
    ):
        """Find the digit images and return them in a list.

        Args:
            ID_box: Image containing the student ID.
            num_digits: Number of digits in the student ID.

        Returns:
            list: A list of images for each digit. In case of errors, returns an empty list
        """
        # WARNING - contains many magic numbers. Will need updating if the
        # IDBox template is changed.
        processed_digits_images_list = []
        for digit_index in range(num_digits):
            # extract single digit by dividing ID box into num_digits equal boxes

            assert len(ID_box.shape) in (2, 3), f"Unexpected box shape {ID_box.shape}"
            ID_box_height = ID_box.shape[0]
            ID_box_width = ID_box.shape[1]
            # ignored third entry 1 (grayscale) or 3 (colour)

            digit_box_width = ID_box_width / num_digits
            side_crop = 5
            top_bottom_crop = 4
            left = int(digit_index * digit_box_width + side_crop)
            right = int((digit_index + 1) * digit_box_width - side_crop)
            single_digit = ID_box[
                0 + top_bottom_crop : ID_box_height - top_bottom_crop, left:right
            ]
            blurred_digit = cv.GaussianBlur(single_digit, (3, 3), 0)
            thresholded_digit = cv.adaptiveThreshold(
                cv.cvtColor(blurred_digit, cv.COLOR_BGR2GRAY),
                255,
                cv.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv.THRESH_BINARY_INV,
                127,  # pretty aggressively threshold here to get rid of dust
                1,
            )
            # extract the bounding box around largest 3 contours
            contours, _ = cv.findContours(
                thresholded_digit, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE
            )
            # if couldn't find contours then return an empty list.
            if len(contours) == 0:
                return []

            # get the largest contour (by area)
            contours = sorted(contours, key=cv.contourArea, reverse=True)
            bbox = cv.boundingRect(contours[0])
            crop_pad = 4
            xrange = (max(bbox[0] - crop_pad, 0), bbox[0] + bbox[2] + crop_pad)
            yrange = (max(bbox[1] - crop_pad, 0), bbox[1] + bbox[3] + crop_pad)
            cropped_digit = thresholded_digit[
                yrange[0] : yrange[1], xrange[0] : xrange[1]
            ]

            # now need to resize image to height or width =28 (depending on aspect ratio)
            # the "28" comes from mnist dataset, mnist digits are 28 x 28
            digit_img_height, digit_img_width = cropped_digit.shape
            aspect_ratio = digit_img_height / digit_img_width
            if aspect_ratio > 1:
                h = 28
                w = int(28 // aspect_ratio)
            else:
                h = int(28 * aspect_ratio)
                w = 28
            resized_digit = cv.resize(
                cropped_digit, (w, h), interpolation=cv.INTER_AREA
            )
            # add black border around the digit image to make the dimensions 28 x 28 pixels
            top_border = int((28 - h) // 2)
            bottom_border = 28 - h - top_border
            left_border = int((28 - w) // 2)
            right_border = 28 - w - left_border
            bordered_image = cv.copyMakeBorder(
                resized_digit,
                top_border,
                bottom_border,
                left_border,
                right_border,
                cv.BORDER_CONSTANT,
                value=[0, 0, 0],
            )
            processed_digits_images_list.append(bordered_image)
        return processed_digits_images_list

    def _np_softmax(self, x: np.ndarray, axis: int = -1) -> np.ndarray:
        x = x - np.max(x, axis=axis, keepdims=True)
        e = np.exp(x)
        return e / np.sum(e, axis=axis, keepdims=True)

    def get_digit_probabilities(
        self,
        prediction_model: tuple["onnxruntime.InferenceSession", str],
        id_box_file: Path,
        num_digits: int,
        *,
        debug: bool = True,
    ) -> list[list[float]]:
        """Return a list of probability predictions for the student ID digits on the cropped image.

        Args:
            prediction_model: PyTorch CNN Prediction model (ONNX).
            id_box_file (str/pathlib.Path): File path for the image of the ID box.
            num_digits (int): Number of digits in the student ID.

        Keyword Args:
            debug (bool): output the trimmed images into "debug_id_reader/"

        Returns:
            list: A list of lists of probabilities.  The outer list is over
            the 8 positions.  Inner lists have length 11: the probability
            that the digit is a 0, 1, 2, ..., 9, blank.
            In case of errors it returns an empty list
        """
        model, device = prediction_model

        debugdir = None
        id_page_file = Path(id_box_file)
        # TODO - sort out cv.typing
        # ID_box: cv.typing.MatLike | None = self.resize_ID_box_and_extract_digit_strip(
        #     id_page_file
        # )
        ID_box = self.resize_ID_box_and_extract_digit_strip(id_page_file)
        if ID_box is None:
            return []
        if debug:
            debugdir = Path(settings.MEDIA_ROOT / "debug_id_reader")
            debugdir.mkdir(exist_ok=True)
            p = debugdir / f"idbox_{id_page_file.stem}.png"
            cv.imwrite(str(p), ID_box)
        processed_digits_images = self.get_digit_images(ID_box, num_digits)
        if len(processed_digits_images) == 0:
            # TODO - put in warning
            # self.stdout.write("Trouble finding digits inside the ID box")
            return []
        if debugdir:
            for n, digit_image in enumerate(processed_digits_images):
                p = debugdir / f"digit_{id_page_file.stem}-pos{n}.png"
                cv.imwrite(str(p), digit_image)
        prob_lists = []
        input_name = model.get_inputs()[0].name
        output_name = model.get_outputs()[0].name
        for digit_image in processed_digits_images:
            # get it into format needed by model predictor
            x = (digit_image.astype(np.float32) / 255.0)[None, None, :, :]
            logits = model.run([output_name], {input_name: x})[0]
            probs = self._np_softmax(logits, axis=1)[0].tolist()
            prob_lists.append(probs)

        return prob_lists

    def compute_probability_heatmap_for_idbox_images(
        self, image_file_paths: dict[int, Path], num_digits: int
    ) -> dict[int, list[list[float]]]:
        """Return probabilities for digits for each paper in the given dictionary of images files.

        Args:
            image_file_paths: A dictionary  {paper_number: path_to_id_box_image_file}
            num_digits: how many digits in a student ID.

        Returns:
            dict: A dictionary which gives the probability that the number in the ID on a given paper is a particular digit.
        """
        prediction_model = load_model()
        probabilities = {}
        for paper_number, image_file in image_file_paths.items():
            prob_lists = self.get_digit_probabilities(
                prediction_model, image_file, num_digits
            )
            if len(prob_lists) == 0:
                # TODO - put in warning
                # self.stdout.write(
                #     f"Test{paper_number}: could not read digits, excluding from calculations"
                # )
                continue
            elif len(prob_lists) != num_digits:
                # TODO - put in warning
                # self.stdout.write(
                #     f"Test{paper_number}: unexpectedly len={len(prob_lists)}: {prob_lists}"
                # )
                probabilities[paper_number] = prob_lists
            else:
                probabilities[paper_number] = prob_lists
        return probabilities

    def compute_and_save_probability_heatmap(self, id_box_files: dict[int, Path]):
        """Use classifier to compute and save a probability heatmap for the ids.

        This downloads a pre-trained random forest classier to compute the probability
        that the given number in the ID on the given paper is a particular digit.
        The resulting heatmap is saved for use by predictor algorithms.
        """
        if not is_model_present():
            ensure_model_available()
        student_id_length = 8
        heatmap = self.compute_probability_heatmap_for_idbox_images(
            id_box_files, student_id_length
        )

        # probs_as_list = {k: [x.tolist() for x in v] for k, v in heatmap.items()}
        with open(settings.MEDIA_ROOT / "id_prob_heatmaps.json", "w") as fh:
            json.dump(heatmap, fh, indent="  ")
        return heatmap

    def make_id_predictions(
        self,
        user: User,
        id_box_files: dict[int, Path],
        *,
        recompute_heatmap: bool = True,
    ) -> None:
        """Predict whxich IDs correspond to which SID from the classlist.

        Raises:
            ValueError: no classlist.
        """
        if recompute_heatmap:
            probabilities = self.compute_and_save_probability_heatmap(id_box_files)
        else:
            heatmaps_file = settings.MEDIA_ROOT / "id_prob_heatmaps.json"
            with open(heatmaps_file, "r") as fh:
                probabilities = json.load(fh)
            probabilities = {int(k): v for k, v in probabilities.items()}

        student_ids = ClasslistService.get_classlist_sids_for_ID_matching()
        if not student_ids:
            raise ValueError("No student IDs provided")

        sliced_probabilities = {
            paper_num: [digit_probs[:10] for digit_probs in all_probs]
            for paper_num, all_probs in probabilities.items()
        }

        self.run_greedy(user, student_ids, sliced_probabilities)
        self.run_lap_solver(user, student_ids, sliced_probabilities)
        self.run_best_guess_predictor(user, probabilities)

    def run_best_guess_predictor(self, user: User, probabilities: dict) -> None:
        """Runs the best-guess predictor and saves its results."""
        id_reader_service = IDReaderService()
        best_guess_predictions = self._best_guess_predictor(probabilities)
        for prediction in best_guess_predictions:
            id_reader_service.add_or_change_ID_prediction(
                user, prediction[0], prediction[1], prediction[2], "MLBestGuess"
            )

    def run_greedy(self, user: User, student_ids: list[str], probabilities) -> None:
        # start by removing any IDs that have already been used
        id_reader_service = IDReaderService()
        for ided_stu in id_reader_service.get_already_matched_sids():
            try:
                student_ids.remove(ided_stu)
            except ValueError:
                pass
        # do not use papers that are already ID'd
        unidentified_papers = id_reader_service.get_unidentified_papers()
        papers_to_id = [n for n in unidentified_papers if n in probabilities]
        if len(papers_to_id) == 0 or len(student_ids) == 0:
            raise IndexError(
                f"Greedy assignment is degenerate: {len(papers_to_id)} unidentified "
                f"machine-read papers and {len(student_ids)} unused students."
            )
        # Different predictors go here.
        greedy_predictions = self._greedy_predictor(student_ids, probabilities)
        for prediction in greedy_predictions:
            id_reader_service.add_or_change_ID_prediction(
                user, prediction[0], prediction[1], prediction[2], "MLGreedy"
            )

    def run_lap_solver(self, user: User, student_ids: list[str], probabilities) -> None:
        # start by removing any IDs that have already been used.
        id_reader_service = IDReaderService()
        for ided_stu in id_reader_service.get_already_matched_sids():
            try:
                student_ids.remove(ided_stu)
            except ValueError:
                pass
        # do not use papers that are already ID'd
        unidentified_papers = id_reader_service.get_unidentified_papers()
        papers_to_id = [n for n in unidentified_papers if n in probabilities]
        if len(papers_to_id) == 0 or len(student_ids) == 0:
            raise IndexError(
                f"Assignment problem is degenerate: {len(papers_to_id)} unidentified "
                f"machine-read papers and {len(student_ids)} unused students."
            )
        lap_predictions = self._lap_predictor(papers_to_id, student_ids, probabilities)
        for prediction in lap_predictions:
            id_reader_service.add_or_change_ID_prediction(
                user, prediction[0], prediction[1], prediction[2], "MLLAP"
            )

    def _best_guess_predictor(
        self, probabilities: dict[int, list[list[float]]]
    ) -> list[tuple[int, str, float]]:
        """Generates direct 'best guess' predictions from the full heatmap."""
        predictions = []
        for paper_num, prob_lists in probabilities.items():
            best_guess_id = ""
            char_probabilities = []
            for digit_probs in prob_lists:
                predicted_index = np.argmax(digit_probs)
                char_probabilities.append(digit_probs[predicted_index])
                if predicted_index == 10:
                    best_guess_id += "X"
                else:
                    best_guess_id += str(predicted_index)
            certainty = np.array(char_probabilities).prod() ** (
                1.0 / len(char_probabilities)
            )
            predictions.append((paper_num, best_guess_id, round(certainty, 2)))
        return predictions

    def _greedy_predictor(
        self, student_IDs: list[str], probabilities: dict[int, Any]
    ) -> list[tuple[int, str, float]]:
        """Generate greedy predictions for student ID numbers.

        Args:
            student_IDs: list of student ID numbers as strings of integers.

            probabilities: dict with paper_number -> probability matrix.
            Each matrix contains probabilities that the ith ID char is matched with digit j.

        Returns:
            list: a list of tuples (paper_number, id_prediction, certainty)

        Algorithm:
            For each entry in probabilities, check each student id in the classlist
            against the matrix. The probabilities corresponding to the digits in the
            student id are extracted. Calculate a mean of those digit probabilities,
            and choose the student id that yielded the highest mean value.
            The calculated digit probabilities mean is returned as the "certainty".
        """
        predictions = []

        for paper_num in probabilities:
            sid_probs = []

            for id_num in student_IDs:
                sid = str(id_num)
                digit_probs = []
                for i in range(len(sid)):
                    # find the probability of digit i in sid
                    i_prob = probabilities[paper_num][i][int(sid[i])]
                    digit_probs.append(i_prob)

                # calculate the geometric mean of all digit probabilities
                mean = np.array(digit_probs).prod() ** (1.0 / len(digit_probs))
                sid_probs.append(mean)

            # choose the sid with the highest mean digit probability
            largest_prob = sid_probs.index(max(sid_probs))
            predictions.append(
                (paper_num, student_IDs[largest_prob], round(max(sid_probs), 2))
            )

        return predictions

    def _assemble_cost_matrix(self, paper_numbers, student_IDs, probabilities):
        """Compute the cost matrix between list of papers and list of student IDs.

        Args:
            paper_numbers (list): int, the ones we want to match.
            student_IDs (list): A list of student ID numbers
            probabilities (dict): keyed by papernum (int), to list of lists of floats.

        Returns:
            list: list of lists of floats representing a matrix.

        Raises:
            KeyError: If probabilities is missing data for one of the paper numbers.
        """

        def _log_likelihood(student_ID, prediction_probs):
            if len(prediction_probs) != len(student_ID):
                raise ValueError("Wrong length")
            log_likelihood = 0
            for digit_index in range(0, len(student_ID)):
                digit_predicted = int(student_ID[digit_index])
                log_likelihood -= np.log(
                    max(prediction_probs[digit_index][digit_predicted], 1e-30)
                )  # avoids taking log of 0.

            return log_likelihood

        # could precompute big cost matrix, then select rows/columns: more complex
        costs = []
        for pn in paper_numbers:
            row = []
            for student_ID in student_IDs:
                row.append(_log_likelihood(student_ID, probabilities[pn]))
            costs.append(row)
        return costs

    def _lap_predictor(
        self, paper_numbers: list[int], student_IDs: list[str], probabilities
    ) -> list[tuple[int, str, float]]:
        """Run SciPy's linear sum assignment problem solver, return prediction results.

        Args:
            paper_numbers: int, the ones we want to match.
            student_IDs: A list of student ID numbers.
            probabilities: dict with keys that contain a paper number
                and values that contain a probability matrix,
                which is a list of lists of floats.

        Returns:
            List of triples of (`paper_number`, `student_ID`, `certainty`),
            where certainty is the mean of digit probabilities for the student_ID
            selected by LAP solver.
        """
        cost_matrix = self._assemble_cost_matrix(
            paper_numbers, student_IDs, probabilities
        )
        row_IDs, column_IDs = linear_sum_assignment(cost_matrix)

        predictions = []
        for r, c in zip(row_IDs, column_IDs):
            pn = paper_numbers[r]
            sid = student_IDs[c]

            # calculate the geometric mean of all digit probabilities
            # use that as a certainty measure
            digit_probs = []
            for i in range(len(sid)):
                i_prob = probabilities[pn][i][int(sid[i])]
                digit_probs.append(i_prob)
            certainty = np.array(digit_probs).prod() ** (1.0 / len(digit_probs))
            predictions.append((pn, sid, round(certainty, 2)))
        return predictions
