# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Natalie Balashov

"""Services for annotations and annotation images."""

import pathlib

from django.db import transaction
from django.core.files.uploadedfile import InMemoryUploadedFile

from Rubrics.models import Rubric
from ..models import Annotation, AnnotationImage, MarkingTask


@transaction.atomic
def save_annotation(
    task: MarkingTask, score: int, time: int, image: AnnotationImage, data: str
) -> Annotation:
    """Save an annotation.

    TODO: `data` should be converted into a dataclass of some kind

    Args:
        task: the relevant MarkingTask. Assumes that task.assigned_user is
            the user who submitted this annotation.
        score: the points awarded in the annotation.
        time: the amount of time it took to mark the question.
        image: reference to an AnnotationImage.
        data: JSON blob of SVG data.

    Returns:
        A reference to the new Annotation object.
    """
    if task.latest_annotation:
        last_annotation_edition = task.latest_annotation.edition
    else:  # there was no previous annotation
        last_annotation_edition = 0

    new_annotation = Annotation(
        edition=last_annotation_edition + 1,
        score=score,
        image=image,
        annotation_data=data,
        marking_time=time,
        task=task,
        user=task.assigned_user,
    )
    new_annotation.save()
    add_annotation_to_rubrics(new_annotation)

    task.latest_annotation = new_annotation
    task.save()

    return new_annotation


@transaction.atomic
def add_annotation_to_rubrics(annotation: Annotation):
    """Add a relation to this annotation for every rubric that this annotation uses."""
    scene_items = annotation.annotation_data["sceneItems"]
    rubric_keys = [item[3] for item in scene_items if item[0] == "GroupDeltaText"]
    rubrics = Rubric.objects.filter(key__in=rubric_keys)
    for rubric in rubrics:
        rubric.annotations.add(annotation)
        rubric.save()


@transaction.atomic
def save_annotation_image(
    md5sum: str, annot_img: InMemoryUploadedFile
) -> AnnotationImage:
    """Save an annotation image to disk and the database.

    Args:
        md5sum: the annotation image's hash.
        annot_img: (InMemoryUploadedFile) the annotation image file.
            The filename including extension is taken from this.

    Return:
        Reference to the database object.
    """
    imgtype = pathlib.Path(annot_img.name).suffix.casefold()
    if imgtype not in (".png", ".jpg", ".jpeg"):
        raise ValueError(
            f"Unsupported image type: expected png or jpeg, got '{imgtype}'"
        )
    img = AnnotationImage(hash=md5sum, image=annot_img)
    img.save()
    return img
