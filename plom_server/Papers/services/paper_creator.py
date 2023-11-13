# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov

import logging
from typing import Dict, List, Tuple

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction, IntegrityError
from django_huey import db_task

from Base.models import HueyTaskTracker
from ..models import (
    Specification,
    Paper,
    Image,
    FixedPage,
    IDPage,
    DNMPage,
    QuestionPage,
)


log = logging.getLogger("PaperCreatorService")


# The decorated function returns a ``huey.api.Result``
@db_task(queue="tasks", context=True)
@transaction.atomic
def huey_create_paper_with_qvmapping(
    spec_obj: Specification,
    paper_number: int,
    qv_mapping: Dict[int, int],
    *,
    tracker_pk: int,
    task=None,
) -> None:
    """Creates a paper with the given paper number and the given question-version mapping.

    Also initializes prename ID predictions in DB, if applicable.

    Args:
        spec_obj: The test specification
        paper_number: The number of the paper being created
        qv_mapping: Mapping from each question-number to
            version for this particular paper. Of the form ``{q: v}``.

    Keyword Args:
        tracker_pk: a key into the database for anyone interested in
            our progress.
        task: includes our ID in the Huey process queue.

    Returns:
        None
    """
    with transaction.atomic():
        tr = HueyTaskTracker.objects.get(pk=tracker_pk)
        tr.status = HueyTaskTracker.RUNNING
        tr.huey_id = task.id
        tr.save()

    paper_obj = Paper(paper_number=paper_number)
    try:
        paper_obj.save()
    except IntegrityError as err:
        log.warn(f"Cannot create Paper {paper_number}: {err}")
        raise IntegrityError(
            f"An entry paper {paper_number} already exists in the database"
        )
    # TODO - idpage and dnmpage versions might be not one in future.
    # For time being assume that IDpage and DNMPage are always version 1.
    id_page = IDPage(
        paper=paper_obj, image=None, page_number=int(spec_obj.idPage), version=1
    )
    id_page.save()

    for dnm_idx in spec_obj.doNotMarkPages:
        dnm_page = DNMPage(
            paper=paper_obj, image=None, page_number=int(dnm_idx), version=1
        )
        dnm_page.save()

    for index, question in spec_obj.question.items():
        index = int(index)
        version = qv_mapping[index]
        for q_page in question.pages:
            question_page = QuestionPage(
                paper=paper_obj,
                image=None,
                page_number=int(q_page),
                question_number=index,
                version=version,  # I don't like having to double-up here, but....
            )
            question_page.save()
    with transaction.atomic():
        tr = HueyTaskTracker.objects.get(pk=tracker_pk)
        tr.status = HueyTaskTracker.COMPLETE
        tr.save()


class PaperCreatorService:
    """Class to encapsulate functions to build the test-papers and groups in the DB.

    DB must have a validated test spec before we can use this.
    """

    def __init__(self):
        try:
            self.spec_obj = Specification.load()
            # want the db object not the spec as a dict
        except Specification.DoesNotExist as e:
            raise ObjectDoesNotExist(
                "The database does not contain a test specification."
            ) from e

    def create_paper_with_qvmapping(self, paper_number: int, qv_mapping: Dict) -> None:
        with transaction.atomic(durable=True):
            tr = HueyTaskTracker.objects.create(huey_id=None)
            tr.status = HueyTaskTracker.STARTING
            tr.save()
            tracker_pk = tr.pk

        _ = huey_create_paper_with_qvmapping(
            self.spec_obj, paper_number, qv_mapping, tracker_pk=tracker_pk
        )
        print(f"Just enqueued Huey create paper task id={_.id}")

        with transaction.atomic(durable=True):
            task = HueyTaskTracker.objects.get(pk=tracker_pk)
            # if its still starting, it is safe to change to queued
            assert task.status != HueyTaskTracker.TO_DO
            if task.status == HueyTaskTracker.STARTING:
                task.status = HueyTaskTracker.QUEUED
                task.save()

    def add_all_papers_in_qv_map(
        self, qv_map: Dict, *, background: bool = True
    ) -> Tuple[bool, List]:
        """Build all the papers given by the qv-map.

        Args:
            qv_map: For each paper give the question-version map.
                Of the form `{paper_number: {q: v}}`

        Keyword Args:
            background (optional, bool): Run in the background. If false,
                run with `call_local`.

        Returns:
            A pair such that if all papers added to DB without errors then
            return `(True, [])` else return `(False, list_of_errors)` where
            the list of errors is a list of pairs `(paper_number, error)`.
        """
        errors = []
        for paper_number, qv_mapping in qv_map.items():
            try:
                if background:
                    self.create_paper_with_qvmapping(paper_number, qv_mapping)
                else:
                    # Note call_local to just do it without invoking the queue
                    huey_create_paper_with_qvmapping.call_local(
                        self.spec_obj, paper_number, qv_mapping
                    )
            except ValueError as err:
                errors.append((paper_number, err))
        if errors:
            return False, errors
        else:
            return True, []

    def remove_all_papers_from_db(self) -> None:
        # hopefully we don't actually need to call this outside of testing.
        # Have to use a loop because of a bug/quirk in django_polymorphic
        # see https://github.com/django-polymorphic/django-polymorphic/issues/34
        for page in FixedPage.objects.all():
            page.delete()
        Paper.objects.all().delete()

    def update_page_image(
        self, paper_number: int, page_index: int, image: Image
    ) -> None:
        """Add a reference to an Image instance.

        Args:
            paper_number: a Paper instance id.
                TODO: which is it?  not sure paper number will always be
                the same as the pk of the paper!
            page_index: the page number
            image: the page-image
        """
        paper = Paper.objects.get(paper_number=paper_number)
        page = FixedPage.objects.get(paper=paper, page_number=page_index)
        page.image = image
        page.save()
