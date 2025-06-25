# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady

from plom_server.QuestionClustering.models import (
    QuestionClusteringChore,
    QVClusterLink,
    QVCluster,
)

from plom_server.Papers.models import Paper
from plom_server.Papers.services import PaperInfoService
from plom_server.Rectangles.services import (
    RectangleExtractor,
    extract_rect_region_from_image,
)
from plom_server.Base.models import HueyTaskTracker
from django.db import transaction
from django_huey import db_task, get_queue
import huey
import huey.api
import numpy as np
from .image_processing_service import ImageProcessingService
from .inference_model import QuestionClusteringModel
import cv2
from sklearn.cluster import AgglomerativeClustering
import pandas as pd
from io import BytesIO
from PIL import Image
from django.db.models import Count


class QuestionClusteringService:

    def __init__(self):
        self.model = QuestionClusteringModel()

    def start_cluster_qv_job(
        self, question_idx: int, version: int, page_num: int, rects: dict
    ):
        """Run a background job to cluster papers for a (q, v) at the given page_num and bbox.

        question_idx: The question index used for clustering
        version: The question version used for clustering
        page_num: The page number used for clustering. Note: this is needed as there can be
            multi-pages question
        rects: the coordinates of the four corners of the rectangle used for clustering.
            Rects should have these keys: [top, left, bottom, right].
        """
        expected_keys = {"top", "left", "bottom", "right"}
        if expected_keys.intersection(set(rects.keys())) != expected_keys:
            raise ValueError(
                f"rects must have these keys: {expected_keys}, but received: {rects.keys()}"
            )

        with transaction.atomic(durable=True):
            x = QuestionClusteringChore.objects.create(
                question_idx=question_idx,
                version=version,
                page_num=page_num,
                top=rects["top"],
                left=rects["left"],
                bottom=rects["bottom"],
                right=rects["right"],
                status=HueyTaskTracker.STARTING,
            )
            tracker_pk = x.pk

        res = huey_cluster_single_qv(
            question_idx=question_idx,
            version=version,
            page_num=page_num,
            rects=rects,
            tracker_pk=tracker_pk,
            _debug_be_flaky=False,
        )
        # print(f"Just enqueued Huey parent_split_and_save task id={res.id}")
        HueyTaskTracker.transition_to_queued_or_running(tracker_pk, res.id)

    def cluster_qv(self, question_idx: int, version: int, page_num: int, rects: dict):
        top = rects["top"]
        left = rects["left"]
        bottom = rects["bottom"]
        right = rects["right"]

        # Get reference image within the rectangle
        rex = RectangleExtractor(version, page_num)
        ref_img = rex.rimg_obj
        cropped_ref_bytes = extract_rect_region_from_image(
            ref_img.image_file.path,
            ref_img.parsed_qr,
            left,
            top,
            right,
            bottom,
            (rex.LEFT, rex.TOP, rex.RIGHT, rex.BOTTOM),
        )

        # Convert bytes to NumPy array
        with BytesIO(cropped_ref_bytes) as fh:
            pil_img = Image.open(fh)
            cropped_ref = np.array(pil_img)

        # Get scanned images within the rectangle then run clustering system (get probabilities)
        paper_numbers = PaperInfoService.get_paper_numbers_containing_page(
            page_num, version=version, scanned=True
        )

        # Build df of probabilities
        data = []
        for pn in paper_numbers:
            cropped_scanned_bytes = rex.extract_rect_region(
                pn, left, top, right, bottom
            )
            with BytesIO(cropped_scanned_bytes) as fh:
                pil_img = Image.open(fh)
                cropped_scanned = np.array(pil_img)

            probs = self.predict(cropped_ref, cropped_scanned)
            datum = {i: p for i, p in enumerate(probs)}
            datum["paper_num"] = pn
            data.append(datum)
        df = pd.DataFrame(data)

        # Extract the probabilites that will be clustered on
        feature_cols = [i for i in range(11)]
        df[feature_cols] = df[feature_cols].fillna(0)
        X = df[feature_cols].values

        # Cluster based on the probabilities
        clustering_model = AgglomerativeClustering(
            n_clusters=None, distance_threshold=1.0, linkage="ward"
        )
        df["clusterId"] = clustering_model.fit_predict(X)

        # Store into db
        for pn, clusterId in zip(df["paper_num"], df["clusterId"]):
            paper = Paper.objects.get(paper_number=pn)
            qv_cluster, _ = QVCluster.objects.get_or_create(
                question_idx=question_idx,
                version=version,
                clusterId=clusterId,
                page_num=page_num,
                top=top,
                left=left,
                bottom=bottom,
                right=right,
            )
            QVClusterLink.objects.create(paper=paper, qv_cluster=qv_cluster)

    def predict(self, ref: np.ndarray, scanned: np.ndarray) -> list:
        """Predict handwritten answer by outputting vector of probability.

        Args:
            ref:
            scanned:

        Returns:

        """
        gap_tolerance = 10
        num_classes = 11

        imp = ImageProcessingService()
        diff = imp.get_diff(ref, scanned)

        # find raw components
        _, _, stats, _ = cv2.connectedComponentsWithStats(diff, connectivity=8)

        # merge nearby components
        groups = imp.merge_components_by_proximity(stats, tol=gap_tolerance)

        # pick best over each merged group
        bestConfidence, bestProbs = 0.0, [0] * num_classes
        for group in groups:
            # build union-bbox
            xs, ys, ws, hs = [], [], [], []
            for lab in group:
                x, y, w, h, _ = stats[lab]
                xs.append(x)
                ys.append(y)
                ws.append(w)
                hs.append(h)
            x0, y0 = min(xs), min(ys)
            x1 = max(x + w for x, w in zip(xs, ws))
            y1 = max(y + h for y, h in zip(ys, hs))
            area = (x1 - x0) * (y1 - y0)
            if area < 100:
                continue

            crop = diff[y0:y1, x0:x1]
            confidence, probs = self.model.predict(crop, thresh=0.55)
            if confidence > bestConfidence:
                bestConfidence = confidence
                bestProbs = probs

        return bestProbs

    def get_question_clustering_tasks(self) -> list[dict]:
        """Get all non-obsolete clustering tasks

        Returns:
            A list of dicts each representing a non-obsolete clustering task. The dict
            has these keys: [question_idx, version, status].
        """

        return [
            {
                "question_idx": task.question_idx,
                "version": task.version,
                "page_num": task.page_num,
                "status": task.get_status_display(),
            }
            for task in QuestionClusteringChore.objects.filter(obsolete=False)
        ]

    def get_cluster_groups_and_count(self, question_idx: int, version: int) -> dict:
        """Get."""
        qs = (
            QVClusterLink.objects.filter(
                qv_cluster__question_idx=question_idx, qv_cluster__version=version
            )
            .values("qv_cluster__clusterId")
            .annotate(count=Count("id"))
        )
        return {item["qv_cluster__clusterId"]: item["count"] for item in qs}

    def get_paper_nums_in_clusters(self, question_idx: int, version: int):
        qs = QVClusterLink.objects.filter(
            qv_cluster__question_idx=question_idx, qv_cluster__version=version
        ).prefetch_related("paper")

        result = {}
        for item in qs:
            cluster_id = item.qv_cluster.clusterId
            paper_num = item.paper.paper_number

            if cluster_id not in result:
                result[cluster_id] = []
            result[cluster_id].append(paper_num)

        return result

    def get_corners_used_for_clustering(self, question_idx: int, version: int):
        qvc = QVCluster.objects.filter(question_idx=question_idx, version=version)[0]
        return {
            "top": qvc.top,
            "left": qvc.left,
            "bottom": qvc.bottom,
            "right": qvc.right,
        }


# The decorated function returns a ``huey.api.Result``
@db_task(queue="chores", context=True)
def huey_cluster_single_qv(
    question_idx: int,
    version: int,
    page_num: int,
    rects: dict,
    *,
    tracker_pk: int,
    _debug_be_flaky: bool = False,
    task: huey.api.Task | None = None,
) -> bool:
    """Build a cluster mapping for a single question, version pair.

    Args:
        question_idx: The question to be clustered on.
        version: version of the question to be clustered on.
        page_num: page_num for the clustering, used to resolve ambiguity in multi-pages question.
        rects: dict of coordinates of the rectangle used for clustering. Ideally should primarily
        contain final answer.

    Keyword Args:
        tracker_pk: a key into the database for anyone interested in
            our progress.
        _debug_be_flaky: for debugging, all take a while and some
            percentage will fail.
        task: includes our ID in the Huey process queue.  This kwarg is
            passed by `context=True` in decorator: callers should not
            pass this in!

    Returns:
        True, no meaning, just as per the Huey docs: "if you need to
        block or detect whether a task has finished".
    """
    assert task is not None

    HueyTaskTracker.transition_to_running(tracker_pk, task.id)
    qcs = QuestionClusteringService()
    qcs.cluster_qv(question_idx, version, page_num, rects)

    HueyTaskTracker.transition_to_complete(tracker_pk)
    return True
