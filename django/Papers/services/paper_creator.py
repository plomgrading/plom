# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Andrew Rechnitzer
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

import logging

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction, IntegrityError
from django_huey import db_task

from Papers.models import (
    Specification,
    Paper,
    BasePage,
    IDPage,
    DNMPage,
    QuestionPage,
    CreatePaperTask,
)


log = logging.getLogger("PaperCreatorService")


class PaperCreatorService:
    """Class to encapsulate all the functions to build the test-papers and
    groups in the db. DB must have a validated test spec before we can use
    this.
    """

    def __init__(self):
        try:
            self.spec = Specification.load().spec_dict
        except Specification.DoesNotExist:
            raise ObjectDoesNotExist(
                "The database does not contain a test specification."
            )

    @transaction.atomic
    def create_paper_with_qvmapping(self, paper_number, qv_mapping):
        paper_task = self._create_paper_with_qvmapping(
            self.spec, paper_number, qv_mapping
        )
        paper_task_obj = CreatePaperTask(
            huey_id=paper_task.id, paper_number=paper_number
        )
        paper_task_obj.status = "queued"
        paper_task_obj.save()

    @db_task(queue="tasks")
    @transaction.atomic
    def _create_paper_with_qvmapping(spec, paper_number, qv_mapping):
        """Creates a paper with the given paper number and the given
        question-version mapping.

        spec (dict): The test specification
        paper_number (int): The number of the paper being created
        qv_mapping (dict): Mapping from each question-number to
            version for this particular paper. Of the form {q: v}



        """
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
            paper=paper_obj, image=None, page_number=int(spec["idPage"]), _version=1
        )
        id_page.save()

        for dnm_idx in spec["doNotMarkPages"]:
            dnm_page = DNMPage(
                paper=paper_obj, image=None, page_number=int(dnm_idx), _version=1
            )
            dnm_page.save()

        for q_id, question in spec["question"].items():
            index = int(q_id)
            version = qv_mapping[index]
            for q_page in question["pages"]:
                question_page = QuestionPage(
                    paper=paper_obj,
                    image=None,
                    page_number=int(q_page),
                    question_number=index,
                    question_version=version,
                    _version=version,  # I don't like having to double-up here, but....
                )
                question_page.save()

    def add_all_papers_in_qv_map(self, qv_map, background=True):
        """Build all the papers given by the qv-map

        qv_map (dict): For each paper give the question-version map.
            Of the form {paper_number: {q: v}}

        background (optional, bool): Run in the background. If false,
        run with call_local.

        returns (pair): If all papers added to DB without errors then
            return (True, []) else return (False, list of errors) where
            the list of errors is a list of pairs (paper_number, error)
        """

        errors = []
        for paper_number, qv_mapping in qv_map.items():
            try:
                if background:
                    self.create_paper_with_qvmapping(paper_number, qv_mapping)
                else:
                    self._create_paper_with_qvmapping.call_local(
                        self.spec, paper_number, qv_mapping
                    )
            except ValueError as err:
                errors.append((paper_number, err))
        if errors:
            return False, errors
        else:
            return True, []

    def remove_all_papers_from_db(self):
        # hopefully we don't actually need to call this outside of testing.
        # Have to use a loop because of a bug/quirk in django_polymorphic
        # see https://github.com/django-polymorphic/django-polymorphic/issues/34
        for page in BasePage.objects.all():
            page.delete()
        Paper.objects.all().delete()

    def update_page_image(self, paper_number, page_index, image):
        """
        Add a reference to an Image instance.

        Args:
            paper_number: (int) a Paper instance id
            page_index: (int) the page number
            image: (Image) the page-image
        """

        paper = Paper.objects.get(paper_number=paper_number)
        page = BasePage.objects.get(paper=paper, page_number=page_index)
        page.image = image
        page.save()
