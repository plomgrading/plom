# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov

import logging
from typing import Dict, List, Tuple

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction, IntegrityError
from django_huey import db_task

from ..models import (
    Specification,
    Paper,
    Image,
    FixedPage,
    IDPage,
    DNMPage,
    QuestionPage,
    CreatePaperTask,
)


log = logging.getLogger("PaperCreatorService")


@db_task(queue="tasks")
@transaction.atomic
def _create_paper_with_qvmapping(
    spec: Dict, paper_number: int, qv_mapping: Dict, username: str
) -> None:
    """Creates a paper with the given paper number and the given question-version mapping.

    Also initializes prename ID predictions in DB, if applicable.

    Args:
        spec: The test specification
        paper_number: The number of the paper being created
        qv_mapping: Mapping from each question-number to
            version for this particular paper. Of the form {q: v}
        username: Name of user to be associated with prename predictions
            created during paper creation.

    Raises:
        ValueError: if provided username does not have a valid User object in DB.
    """
    # private to prevent circular imports
    from Preparation.services import StagingStudentService
    from Identify.services import IDReaderService

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
        paper=paper_obj, image=None, page_number=int(spec["idPage"]), version=1
    )
    id_page.save()

    for dnm_idx in spec["doNotMarkPages"]:
        dnm_page = DNMPage(
            paper=paper_obj, image=None, page_number=int(dnm_idx), version=1
        )
        dnm_page.save()

    student_service = StagingStudentService()
    prename_sid = student_service.get_prename_for_paper(paper_number)
    if prename_sid:
        try:
            user = User.objects.get(username__iexact=username)
        except ObjectDoesNotExist as e:
            raise ValueError(f"User '{username}' does not exist") from e
        id_reader_service = IDReaderService()
        id_reader_service.add_prename_ID_prediction(user, prename_sid, paper_number)

        for index, question in spec["question"].items():
            index = int(index)
            version = qv_mapping[index]
            for q_page in question["pages"]:
                question_page = QuestionPage(
                    paper=paper_obj,
                    image=None,
                    page_number=int(q_page),
                    question_number=index,
                    version=version,  # I don't like having to double-up here, but....
                )
                question_page.save()


class PaperCreatorService:
    """Class to encapsulate functions to build the test-papers and groups in the DB.

    DB must have a validated test spec before we can use this.
    """

    def __init__(self):
        try:
            self.spec = Specification.load().spec_dict
        except Specification.DoesNotExist as e:
            raise ObjectDoesNotExist(
                "The database does not contain a test specification."
            ) from e

    @transaction.atomic
    def create_paper_with_qvmapping(
        self, paper_number: int, qv_mapping: Dict, username: str
    ) -> None:
        paper_task = _create_paper_with_qvmapping(
            self.spec, paper_number, qv_mapping, username
        )
        paper_task_obj = CreatePaperTask(
            huey_id=paper_task.id, paper_number=paper_number
        )
        paper_task_obj.status = "queued"
        paper_task_obj.save()

    def add_all_papers_in_qv_map(
        self, qv_map: Dict, username: str, background: bool = True
    ) -> Tuple[bool, List]:
        """Build all the papers given by the qv-map.

        Args:
            qv_map: For each paper give the question-version map.
                Of the form `{paper_number: {q: v}}`
            username: Name of user to be associated with prename predictions
                created during paper creation.

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
                    self.create_paper_with_qvmapping(paper_number, qv_mapping, username)
                else:
                    _create_paper_with_qvmapping.call_local(
                        self.spec, paper_number, qv_mapping, username
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
