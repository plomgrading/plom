# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov

import logging
from typing import Dict

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
    PopulateEvacuateDBChore,
)
from Preparation.services.preparation_dependency_service import (
    assert_can_modify_qv_mapping_database,
)
from plom.plom_exceptions import PlomDependencyConflict

log = logging.getLogger("PaperCreatorService")


@db_task(queue="tasks", context=True)
def huey_populate_whole_db(
    qv_map: Dict[int, Dict[int, int]], *, tracker_pk: int, task=None
) -> bool:
    PopulateEvacuateDBChore.transition_to_running(tracker_pk, task.id)
    N = len(qv_map)

    spec_obj = Specification.load()
    id_page_number = int(spec_obj.idPage)
    dnm_page_numbers = [int(pg) for pg in spec_obj.doNotMarkPages]

    for idx, (paper_number, qv_row) in enumerate(qv_map.items()):
        log.info(f"Constructing paper {paper_number} with {qv_row}")
        paper_obj = Paper.objects.create(paper_number=paper_number)
        # TODO - change how DNM and ID pages taken from versions
        # currently ID page and DNM page both taken from version 1
        IDPage.objects.create(
            paper=paper_obj, image=None, page_number=id_page_number, version=1
        )
        for pg in dnm_page_numbers:
            DNMPage.objects.create(
                paper=paper_obj, image=None, page_number=pg, version=1
            )
        for index, question in spec_obj.question.items():
            q_idx = int(index)
            version = int(qv_row[q_idx])
            for q_page in question.pages:
                QuestionPage.objects.create(
                    paper=paper_obj,
                    image=None,
                    page_number=int(q_page),
                    question_index=q_idx,
                    version=version,
                )

        if idx % 16 == 0:
            PopulateEvacuateDBChore.set_message_to_user(
                tracker_pk, f"Populated {idx} of {N} papers in database"
            )
            print(f"Populated {idx} of {N} papers in database")

    PopulateEvacuateDBChore.set_message_to_user(
        tracker_pk, f"Populated all {N} papers in database"
    )
    PopulateEvacuateDBChore.transition_to_complete(tracker_pk)
    return True


@db_task(queue="tasks", context=True)
def huey_evacuate_whole_db(*, tracker_pk: int, task=None) -> bool:
    PopulateEvacuateDBChore.transition_to_running(tracker_pk, task.id)
    all_papers = Paper.objects.all().prefetch_related("fixedpage_set")
    N = all_papers.count()

    for idx, paper_obj in enumerate(all_papers):
        for fp in paper_obj.fixedpage_set.all():
            fp.delete()
        paper_obj.delete()
        if idx % 16 == 0:
            PopulateEvacuateDBChore.set_message_to_user(
                tracker_pk, f"Deleted {idx} of {N} papers from database"
            )
            print(f"Deleted {idx} of {N} papers from database")

    PopulateEvacuateDBChore.set_message_to_user(
        tracker_pk, f"Deleted all {N} papers from database"
    )
    PopulateEvacuateDBChore.transition_to_complete(tracker_pk)
    return True


class PaperCreatorService:
    """Class to encapsulate functions to build the test-papers and groups in the DB.

    DB must have a validated test spec before we can use this.
    """

    def __init__(self):
        try:
            _ = Specification.load()
        except Specification.DoesNotExist as e:
            raise ObjectDoesNotExist(
                "The database does not contain a test specification."
            ) from e

    def _create_paper_with_qvmapping(
        self,
        paper_number: int,
        qv_mapping: Dict[int, int],
    ) -> None:
        """(DEPRECATED) Creates tables for the given paper number and the given question-version mapping.

        Args:
            paper_number: The number of the paper being created
            qv_mapping: Mapping from each question index to
                version for this particular paper. Of the form ``{q: v}``.

        Returns:
            None
        """
        spec_obj = Specification.load()
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
                    question_index=index,
                    version=version,  # I don't like having to double-up here, but....
                )
                question_page.save()

    def add_all_papers_in_qv_map(self, qv_map: Dict[int, Dict[int, int]]):
        """Build all the Paper and associated tables from the qv-map, but not the PDF files.

        Args:
            qv_map: For each paper give the question-version map.
                Of the form `{paper_number: {q: v}}`

        Raises:
            PlomDependencyConflict: if there are papers already in the database.
        """
        assert_can_modify_qv_mapping_database()
        if Paper.objects.filter().exists():
            raise PlomDependencyConflict("Already papers in the database.")

        self.populate_whole_db_huey_wrapper(qv_map)

    def populate_whole_db_huey_wrapper(self, qv_map: Dict[int, Dict[int, int]]) -> None:
        # TODO - add seatbelt logic here
        with transaction.atomic(durable=True):
            tr = PopulateEvacuateDBChore.objects.create(
                status=PopulateEvacuateDBChore.STARTING,
                action=PopulateEvacuateDBChore.POPULATE,
            )
            tracker_pk = tr.pk

        res = huey_populate_whole_db(qv_map, tracker_pk=tracker_pk)
        print(f"Just enqueued Huey populate-database task id={res.id}")
        PopulateEvacuateDBChore.transition_to_queued_or_running(tracker_pk, res.id)

    def remove_all_papers_from_db(self) -> None:
        assert_can_modify_qv_mapping_database()
        self.evacuate_whole_db_huey_wrapper()

    def evacuate_whole_db_huey_wrapper(self) -> None:
        # TODO - add seatbelt logic here
        with transaction.atomic(durable=True):
            tr = PopulateEvacuateDBChore.objects.create(
                status=PopulateEvacuateDBChore.STARTING,
                action=PopulateEvacuateDBChore.EVACUATE,
            )
            tracker_pk = tr.pk

        res = huey_evacuate_whole_db(tracker_pk=tracker_pk)
        print(f"Just enqueued Huey evacuate-database task id={res.id}")
        PopulateEvacuateDBChore.transition_to_queued_or_running(tracker_pk, res.id)

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
