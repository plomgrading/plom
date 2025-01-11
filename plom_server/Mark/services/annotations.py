# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2024 Aden Chan
# Copyright (C) 2024 Aidan Murphy

from __future__ import annotations

"""Services for annotations and annotation images."""

from typing import Any

import pathlib

from django.db import transaction
from django.core.files.uploadedfile import InMemoryUploadedFile

from Rubrics.models import Rubric
from ..models import Annotation, AnnotationImage, MarkingTask
from plom.plom_exceptions import PlomConflict


@transaction.atomic
def create_new_annotation_in_database(
    task: MarkingTask,
    score: float,
    time: int,
    annot_img_md5sum: str,
    annot_img_file: InMemoryUploadedFile,
    data: dict[str, Any],
    *,
    require_uptodate_rubrics: bool = True,
) -> Annotation:
    """Save an annotation.

    TODO: `data` should be converted into a dataclass of some kind

    Args:
        task: the relevant MarkingTask. Assumes that task.assigned_user is
            the user who submitted this annotation.
            *Caution*: this task is also modified; you should probably
            have called `select_for_update` on it.
        score: the points awarded in the annotation.
        time: the amount of time it took to mark the question.
        annot_img_md5sum: the annotation image's hash.
        annot_img_file: the annotation image file in memory.
            The filename including extension is taken from this.
        data: came from a JSON blob of SVG data, but should be dict of
            string keys by the time we see it.

    Keyword Args:
        require_uptodate_rubrics: if True (the default), we check if the
            rubrics in-use are (a) the latest and (b) published and
            fail if those conditions are not satisfied.

    Returns:
        A reference to the new Annotation object, but there are various
        side effects noted above.

    Raises:
        ValueError: unsupported type of image, based on extension.
        KeyError: uses non-existent rubrics.
        PlomConflict: uses the non-latest or unpublished rubrics.
    """
    annotation_image = _add_new_annotation_image_to_database(
        annot_img_md5sum,
        annot_img_file,
    )
    # implementation details abstracted for testing purposes
    return _create_new_annotation_in_database(
        task,
        score,
        time,
        annotation_image,
        data,
        require_uptodate_rubrics=require_uptodate_rubrics,
    )


def _create_new_annotation_in_database(
    task: MarkingTask,
    score: float,
    time: int,
    annotation_image: AnnotationImage,
    data: dict[str, Any],
    *,
    require_uptodate_rubrics: bool = True,
) -> Annotation:
    if task.latest_annotation:
        last_annotation_edition = task.latest_annotation.edition
        old_time = task.latest_annotation.marking_time
    else:  # there was no previous annotation
        last_annotation_edition = 0
        old_time = 0

    new_annotation = Annotation(
        edition=last_annotation_edition + 1,
        score=score,
        image=annotation_image,
        annotation_data=data,
        marking_time=time,
        marking_delta_time=time - old_time,
        task=task,
        user=task.assigned_user,
    )
    new_annotation.save()
    _add_annotation_to_rubrics(
        new_annotation, require_uptodate_rubrics=require_uptodate_rubrics
    )

    # caution: we are writing to an object given as an input
    task.latest_annotation = new_annotation
    task.save()

    return new_annotation


def _extract_rubric_rid_rev_pairs(raw_annot_data) -> list[tuple[int, int]]:
    scene_items = raw_annot_data["sceneItems"]
    rubric_rid_rev_pairs = [
        (x[3]["rid"], x[3]["revision"]) for x in scene_items if x[0] == "Rubric"
    ]
    return rubric_rid_rev_pairs


def _add_annotation_to_rubrics(
    annotation: Annotation, *, require_uptodate_rubrics: bool
) -> None:
    """Add a relation to this annotation for every rubric that this annotation uses.

    Raises:
        KeyError: one or more non-existent rubrics where used.
    """
    rid_rev_pairs = _extract_rubric_rid_rev_pairs(annotation.annotation_data)

    # TODO: update this query to respect the revisions directly?  My DB-fu is weak
    # so I'll "fix it in postprocessing"; unlikely to make practical difference.
    rids = [rid for rid, rev in rid_rev_pairs]
    rubrics = Rubric.objects.filter(rid__in=rids)  # .select_for_update()

    found = {(rid, rev): False for (rid, rev) in rid_rev_pairs}
    for rubric in rubrics:
        # we have drawn too many rubrics above due to Colin's sloppy DB skills
        # so filter out any that don't match something in rid_rev_pairs
        for rid, rev in rid_rev_pairs:
            if (rid, rev) == (rubric.rid, rubric.revision):
                found[(rid, rev)] = True
                if require_uptodate_rubrics and not rubric.latest:
                    raise PlomConflict(
                        f"rubric rid {rid} revision {rev} is not the latest revision: "
                        "refresh your rubrics and try again"
                    )
                if require_uptodate_rubrics and not rubric.published:
                    raise PlomConflict(
                        f"rubric rid {rid} revision {rev} is the latest but its "
                        "currently not published.  Someone has taken it offline "
                        "possible for editing.  Try again later, ask your marking "
                        "team, or use a different rubric."
                    )
                rubric.annotations.add(annotation)
                # TODO: do these *need* saved?  We're creating entries in a
                # many-to-many, not modifying any rubric per se.
                # rubric.save()

    if not all(found.values()):
        raise KeyError(
            "Unexpectedly, some non-existent Rubrics were used.  "
            f"Please report the following: {found}"
        )


def _add_new_annotation_image_to_database(
    md5sum: str, annot_img: InMemoryUploadedFile
) -> AnnotationImage:
    """Save an annotation image to disk and the database.

    Args:
        md5sum: the annotation image's hash.
        annot_img: the annotation image file.
            The filename including extension is taken from this.

    Returns:
        Reference to the database object.

    Raises:
        VaueError: unsupported type of image, based on extension.
    """
    imgtype = pathlib.Path(annot_img.name).suffix.casefold()
    if imgtype not in (".png", ".jpg", ".jpeg"):
        raise ValueError(
            f"Unsupported image type: expected png or jpeg, got '{imgtype}'"
        )
    img = AnnotationImage.objects.create(hash=md5sum, image=annot_img)
    return img
