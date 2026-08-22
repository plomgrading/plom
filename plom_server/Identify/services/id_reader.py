# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2020-2026 Colin B. Macdonald
# Copyright (C) 2024-2025 Andrew Rechnitzer
# Copyright (C) 2024-2026 Deep Shah
# Copyright (C) 2026 Aidan Murphy

"""Services for extracting ID boxes and predicting paper/student IDs."""

import hashlib
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Literal, cast

import cv2 as cv
import numpy as np
from scipy.optimize import linear_sum_assignment

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db import transaction
from django_huey import db_task
import huey
import huey.api

from plom_server.Base.models import HueyTaskTracker
from plom_server.ML.services.client import (
    DigitCrop,
    PlomDigitServiceClient,
    PlomDigitServiceError,
)
from plom_server.Papers.models import Paper
from plom_server.Papers.services import SpecificationService, PaperInfoService
from plom_server.Preparation.services import StagingStudentService
from plom_server.Rectangles.services import RectangleExtractor
from plom_server.Rectangles.contour_detection import (
    adaptive_threshold_foreground,
    find_sorted_contours,
    largest_contour_bounding_rect,
)
from ..models import (
    PaperIDTask,
    IDPrediction,
    IDPredictionHeatmap,
    IDReadingHueyTaskTracker,
)
from ..services import IdentifyTaskService, ClasslistService

# the default certainty of prenaming predictions
_default_prenaming_prediction_confidence = 0.9

HeatmapMode = Literal["fresh", "resume", "reuse"]
HEATMAP_MODE_FRESH: HeatmapMode = "fresh"
HEATMAP_MODE_RESUME: HeatmapMode = "resume"
HEATMAP_MODE_REUSE: HeatmapMode = "reuse"
_heatmap_modes: set[HeatmapMode] = {
    HEATMAP_MODE_FRESH,
    HEATMAP_MODE_RESUME,
    HEATMAP_MODE_REUSE,
}


def _validate_heatmap_mode(heatmap_mode: str) -> HeatmapMode:
    """Validate and return a supported heatmap mode."""
    if heatmap_mode not in _heatmap_modes:
        raise ValueError(
            f'Unknown heatmap mode "{heatmap_mode}". '
            f"Expected one of {sorted(_heatmap_modes)}."
        )
    return cast(HeatmapMode, heatmap_mode)


class IDReaderService:
    """Functions for ID reading and related helper functions."""

    default_prenaming_prediction_confidence = _default_prenaming_prediction_confidence

    @staticmethod
    def get_already_matched_sids() -> list:
        """Return the list of all student IDs that have been matched with a paper."""
        sid_list = []
        id_task_service = IdentifyTaskService()
        IDed_tasks = PaperIDTask.objects.filter(status=PaperIDTask.COMPLETE)
        for task in IDed_tasks:
            latest = id_task_service.get_latest_id_results(task)
            if latest:
                sid_list.append(latest.student_id)
        return sid_list

    @staticmethod
    def get_unidentified_papers() -> list:
        """Return a list of all unidentified papers."""
        paper_list = []
        not_IDed_tasks = PaperIDTask.objects.filter(status=PaperIDTask.TO_DO)
        for task in not_IDed_tasks:
            paper_list.append(task.paper.paper_number)
        return paper_list

    @staticmethod
    def _get_prenamed_paper_numbers() -> list[int]:
        """Get a list of paper numbers that are prenamed according to the IDPredictions table.

        Careful with this versus `StagingStudentService.get_prenamed_papers`
        which consults the raw classlist.  This code looks at the predictions
        list.  Issue #4164.  I'm not entirely clear of the distinction but it
        seems a multiple sources of truth problem.
        """
        return list(
            IDPrediction.objects.filter(predictor="prename").values_list(
                "paper__paper_number", flat=True
            )
        )

    @staticmethod
    @transaction.atomic
    def get_ID_predictions(
        predictor: str | None = None,
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

    @staticmethod
    @transaction.atomic
    def add_or_change_ID_prediction(
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

    @classmethod
    def add_or_change_ID_prediction_cmd(
        cls,
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
        cls.add_or_change_ID_prediction(
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
        """Return the predictor names used by machine-learning ID prediction."""
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
        # get dict of prenamed papers (as per classlist, not IDPredictions)
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

    @staticmethod
    def get_id_reader_background_chore_status() -> dict[str, str]:
        """Return the status and human-readable message about the background ID reader chore."""
        try:
            idht_obj = IDReadingHueyTaskTracker.objects.exclude(obsolete=True).get()
        except ObjectDoesNotExist:
            return {"status": "To Do", "message": "ID reader has not been run."}

        return {"status": idht_obj.get_status_display(), "message": idht_obj.message}

    @staticmethod
    def run_id_reader_in_background_via_huey(
        user: User,
        box_versions: dict[int, dict[str, float] | None],
        heatmap_mode: HeatmapMode = HEATMAP_MODE_RESUME,
    ):
        """Run the ID reading process in the background.

        Raises:
            MultipleObjectsReturned: if the user tries to run multiple such tasks.
            ValueError: if the heatmap mode is unsupported.
        """
        heatmap_mode = _validate_heatmap_mode(heatmap_mode)
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
            heatmap_mode=heatmap_mode,
            tracker_pk=tracker_pk,
        )
        # and update the status
        HueyTaskTracker.transition_to_queued_or_running(tracker_pk, res.id)


# The decorated function returns a ``huey.api.Result``
@db_task(queue="chores", context=True)
def huey_id_reading_task(
    user: User,
    box_versions: dict[int, dict[str, float] | None],
    heatmap_mode: HeatmapMode,
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
        heatmap_mode: how to use saved digit probability heatmaps.

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
    heatmap_mode = _validate_heatmap_mode(heatmap_mode)
    HueyTaskTracker.transition_to_running(
        tracker_pk, task.id, msg="ID Reading task has started. Getting ID boxes."
    )

    HueyTaskTracker.set_message(tracker_pk, "Extracting ID boxes from scanned pages.")
    id_box_image_dict = IDBoxProcessorService.save_all_id_boxes(
        box_versions,
        progress_callback=lambda msg: HueyTaskTracker.set_message(tracker_pk, msg),
    )
    HueyTaskTracker.set_message(
        tracker_pk, f"Extracted {len(id_box_image_dict)} ID boxes from scanned pages."
    )
    # check if we got any ID boxes (eg no scanned papers, or all prenamed)
    if len(id_box_image_dict) == 0:
        HueyTaskTracker.transition_to_complete(
            tracker_pk, msg="No ID-boxes found. Cannot make predictions."
        )
        return True

    HueyTaskTracker.set_message(
        tracker_pk, "ID boxes images saved. Computing prediction heatmaps..."
    )

    try:
        probabilities = IDBoxProcessorService.get_or_compute_probability_heatmaps(
            id_box_image_dict, heatmap_mode=heatmap_mode
        )
    except PlomDigitServiceError as e:
        HueyTaskTracker.transition_chore_to_error(
            tracker_pk, f"Digit recognition service error: {e}"
        )
        return True

    HueyTaskTracker.set_message(
        tracker_pk, "Heatmaps saved.  Computing ID predictions..."
    )

    try:
        if not probabilities:
            raise ValueError("No digit probability heatmaps available")
        IDBoxProcessorService.compute_id_predictions(user, probabilities)
    except ValueError as e:
        HueyTaskTracker.transition_chore_to_error(
            tracker_pk, f"ID prediction failed: {e}"
        )
        return True

    # short pause, unlikely to help w/ Issue #4165 (cannot reproduce)
    time.sleep(0.1)

    HueyTaskTracker.transition_to_complete(tracker_pk, msg="ID predictions complete.")
    return True


class IDBoxProcessorService:
    """Service for dealing with the ID box and processing it into ID predictions."""

    @staticmethod
    def save_all_id_boxes(
        box_versions: dict[int, dict[str, float] | None],
        *,
        exclude_prenamed_papers: bool = True,
        save_dir: Path | None = None,
        progress_callback: Callable[[str], None] | None = None,
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
            progress_callback: optional callable invoked with a status
                message as extraction progresses.

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
            exclude_papers = IDReaderService._get_prenamed_paper_numbers()
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
            total = len(paper_numbers)
            for index, pn in enumerate(paper_numbers, start=1):
                if progress_callback:
                    progress_callback(
                        f"Extracting ID box {index}/{total} for version {v}, paper {pn}."
                    )
                id_box_filename = id_box_folder / f"id_box_{pn:04}.png"
                try:
                    id_box_bytes = rex.extract_rect_region(pn, *box)
                except ValueError:
                    # just leave them out when rex cannot compute appropriate transforms
                    continue
                id_box_filename.write_bytes(id_box_bytes)
                img_file_dict[pn] = id_box_filename

        return img_file_dict

    # problem with cv2.typing - see MR 3050.
    # comment out the cv2.typing.MatLike hint here.
    # TODO - fix the cv2.typing issue in dev sometime.
    @staticmethod
    def resize_ID_box_and_extract_digit_strip(id_box_file: Path):
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
    @staticmethod
    def get_digit_images(
        # ID_box: cv.typing.MatLike, num_digits: int
        # ) -> list[cv.typing.MatLike]:
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
            thresholded_digit = adaptive_threshold_foreground(
                blurred_digit,
                block_size=127,  # pretty aggressively threshold here to get rid of dust
                c=1,
                blur_kernel=None,
            )
            # extract the bounding box around the largest contour
            contours = find_sorted_contours(thresholded_digit, cv.RETR_EXTERNAL)
            # if couldn't find contours then return an empty list.
            bbox = largest_contour_bounding_rect(contours)
            if bbox is None:
                return []

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

    @staticmethod
    def encode_digit_image_as_png(digit_image) -> bytes:
        """Encode a prepared digit image as PNG bytes for the digit service."""
        success, buffer = cv.imencode(".png", digit_image)
        if not success:
            raise ValueError("Could not encode digit crop as PNG")
        return buffer.tobytes()

    @staticmethod
    def clear_probability_heatmaps(paper_numbers: Iterable[int]) -> None:
        """Delete saved digit probability heatmaps for the given paper numbers."""
        IDPredictionHeatmap.objects.filter(
            paper__paper_number__in=list(paper_numbers)
        ).delete()

    @staticmethod
    def hash_id_box_image(id_box_file: Path) -> str:
        """Return a stable fingerprint of an extracted ID-box image."""
        return hashlib.sha256(id_box_file.read_bytes()).hexdigest()

    @staticmethod
    def is_complete_probability_heatmap(
        probabilities: Any, *, student_id_length: int
    ) -> bool:
        """Return whether a saved heatmap has all digit positions and classes."""
        return (
            isinstance(probabilities, list)
            and len(probabilities) == student_id_length
            and all(isinstance(row, list) and len(row) == 11 for row in probabilities)
        )

    @staticmethod
    def save_probability_heatmap_for_paper(
        paper_number: int,
        probabilities: list[list[float]],
        *,
        source_image_hash: str,
    ) -> None:
        """Persist one complete paper's digit probability heatmap."""
        paper = Paper.objects.get(paper_number=paper_number)
        IDPredictionHeatmap.objects.update_or_create(
            paper=paper,
            defaults={
                "source_image_hash": source_image_hash,
                "probabilities": probabilities,
            },
        )

    @staticmethod
    def load_probability_heatmaps(
        source_image_hashes: dict[int, str],
    ) -> dict[int, list[list[float]]]:
        """Load complete heatmaps whose source images have not changed."""
        student_id_length = settings.PLOM_STUDENT_ID_LENGTH
        rows = IDPredictionHeatmap.objects.filter(
            paper__paper_number__in=list(source_image_hashes)
        ).select_related("paper")
        return {
            row.paper.paper_number: row.probabilities
            for row in rows
            if (
                row.source_image_hash == source_image_hashes.get(row.paper.paper_number)
                and IDBoxProcessorService.is_complete_probability_heatmap(
                    row.probabilities, student_id_length=student_id_length
                )
            )
        }

    @classmethod
    def get_or_compute_probability_heatmaps(
        cls,
        id_box_files: dict[int, Path],
        *,
        heatmap_mode: HeatmapMode = HEATMAP_MODE_RESUME,
    ) -> dict[int, list[list[float]]]:
        """Send prepared digit crops to the digit service and persist probabilities.

        Plom extracts and segments each ID box locally, posts each prepared
        digit crop to ``PLOM_ML_SERVICE_URL``, and saves each complete
        per-paper heatmap to the database as soon as all digit positions for
        that paper have been predicted.

        Heatmap modes:
            fresh: compute all papers, replacing saved heatmaps after the
                digit service is known to be reachable.
            resume: reuse complete saved heatmaps and compute only missing papers.
            reuse: do not call the digit service; only return saved heatmaps.

        Raises:
            PlomDigitServiceError: the external service is not configured or fails.
        """
        heatmap_mode = _validate_heatmap_mode(heatmap_mode)
        student_id_length = settings.PLOM_STUDENT_ID_LENGTH
        source_image_hashes = {
            paper_number: cls.hash_id_box_image(id_box_file)
            for paper_number, id_box_file in id_box_files.items()
        }
        if heatmap_mode == HEATMAP_MODE_REUSE:
            return cls.load_probability_heatmaps(source_image_hashes)

        if heatmap_mode == HEATMAP_MODE_FRESH:
            heatmap: dict[int, list[list[float]]] = {}
        else:
            heatmap = cls.load_probability_heatmaps(source_image_hashes)

        missing_id_box_files = {
            paper_number: id_box_file
            for paper_number, id_box_file in id_box_files.items()
            if paper_number not in heatmap
        }
        if not missing_id_box_files:
            return heatmap

        if not settings.PLOM_ML_SERVICE_URL:
            raise PlomDigitServiceError(
                "PLOM_ML_SERVICE_URL must be configured: "
                "ID prediction requires the external Plom digit recognition service."
            )
        client = PlomDigitServiceClient(
            settings.PLOM_ML_SERVICE_URL,
            token=settings.PLOM_ML_SERVICE_TOKEN,
            timeout=settings.PLOM_ML_SERVICE_TIMEOUT,
        )
        client.check_ready()
        if heatmap_mode == HEATMAP_MODE_FRESH:
            cls.clear_probability_heatmaps(id_box_files.keys())

        for paper_number, id_box_file in missing_id_box_files.items():
            id_box = cls.resize_ID_box_and_extract_digit_strip(id_box_file)
            if id_box is None:
                continue
            digit_images = cls.get_digit_images(id_box, student_id_length)
            if len(digit_images) != student_id_length:
                continue

            crops: list[DigitCrop] = []
            for index, digit_image in enumerate(digit_images, start=1):
                crop_id = f"paper{paper_number}-pos{index}"
                crops.append(
                    DigitCrop(
                        image_bytes=cls.encode_digit_image_as_png(digit_image),
                        crop_id=crop_id,
                        paper_number=paper_number,
                        digit_position=index,
                    )
                )
            digit_probabilities = client.predict_digits(crops)
            paper_probabilities = [
                digit_probabilities[(paper_number, position)]
                for position in range(1, student_id_length + 1)
            ]
            cls.save_probability_heatmap_for_paper(
                paper_number,
                paper_probabilities,
                source_image_hash=source_image_hashes[paper_number],
            )
            heatmap[paper_number] = paper_probabilities

        return heatmap

    @classmethod
    def compute_id_predictions(
        cls,
        user: User,
        probabilities: dict[int, list[list[float]]],
    ) -> None:
        """Predict which IDs correspond to which SID from the classlist.

        Args:
            user: which user is running these predictions.
            probabilities: dict keyed by papernum containing matrices,
                each matrix is a list of lists of floats.

        Raises:
            ValueError: no classlist.
        """
        student_ids = ClasslistService.get_classlist_sids_for_ID_matching()
        if not student_ids:
            raise ValueError("No student IDs provided")

        sliced_probabilities = {
            paper_num: [digit_probs[:10] for digit_probs in all_probs]
            for paper_num, all_probs in probabilities.items()
        }

        cls.run_greedy(user, student_ids, sliced_probabilities)
        cls.run_lap_solver(user, student_ids, sliced_probabilities)
        cls.run_best_guess_predictor(user, probabilities)

    @classmethod
    def run_best_guess_predictor(cls, user: User, probabilities: dict) -> None:
        """Runs the best-guess predictor and saves its results."""
        best_guess_predictions = cls._best_guess_predictor(probabilities)
        for prediction in best_guess_predictions:
            IDReaderService.add_or_change_ID_prediction(
                user, prediction[0], prediction[1], prediction[2], "MLBestGuess"
            )

    @classmethod
    def run_greedy(cls, user: User, student_ids: list[str], probabilities) -> None:
        # start by removing any IDs that have already been used
        for ided_stu in IDReaderService.get_already_matched_sids():
            try:
                student_ids.remove(ided_stu)
            except ValueError:
                pass
        # do not use papers that are already ID'd
        unidentified_papers = IDReaderService.get_unidentified_papers()
        papers_to_id = [n for n in unidentified_papers if n in probabilities]
        if len(papers_to_id) == 0 or len(student_ids) == 0:
            raise IndexError(
                f"Greedy assignment is degenerate: {len(papers_to_id)} unidentified "
                f"machine-read papers and {len(student_ids)} unused students."
            )
        # Different predictors go here.
        greedy_predictions = cls._greedy_predictor(student_ids, probabilities)
        for prediction in greedy_predictions:
            IDReaderService.add_or_change_ID_prediction(
                user, prediction[0], prediction[1], prediction[2], "MLGreedy"
            )

    @classmethod
    def run_lap_solver(cls, user: User, student_ids: list[str], probabilities) -> None:
        """Run the linear-assignment student-ID matcher and save its predictions."""
        # start by removing any IDs that have already been used.
        for ided_stu in IDReaderService.get_already_matched_sids():
            try:
                student_ids.remove(ided_stu)
            except ValueError:
                pass
        # do not use papers that are already ID'd
        unidentified_papers = IDReaderService.get_unidentified_papers()
        papers_to_id = [n for n in unidentified_papers if n in probabilities]
        if len(papers_to_id) == 0 or len(student_ids) == 0:
            raise IndexError(
                f"Assignment problem is degenerate: {len(papers_to_id)} unidentified "
                f"machine-read papers and {len(student_ids)} unused students."
            )
        lap_predictions = cls._lap_predictor(papers_to_id, student_ids, probabilities)
        for prediction in lap_predictions:
            IDReaderService.add_or_change_ID_prediction(
                user, prediction[0], prediction[1], prediction[2], "MLLAP"
            )

    @staticmethod
    def _best_guess_predictor(
        probabilities: dict[int, list[list[float]]],
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

    @staticmethod
    def _greedy_predictor(
        student_IDs: list[str], probabilities: dict[int, Any]
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

    @staticmethod
    def _assemble_cost_matrix(paper_numbers, student_IDs, probabilities):
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

    @classmethod
    def _lap_predictor(
        cls, paper_numbers: list[int], student_IDs: list[str], probabilities
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
        cost_matrix = cls._assemble_cost_matrix(
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
