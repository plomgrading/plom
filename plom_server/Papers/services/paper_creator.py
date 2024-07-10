# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov

from __future__ import annotations

import logging
from typing import Dict, List

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
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
from Papers.services import SpecificationService

from Preparation.services.preparation_dependency_service import (
    assert_can_modify_qv_mapping_database,
)
from plom.plom_exceptions import PlomDependencyConflict, PlomDatabaseCreationError

log = logging.getLogger("PaperCreatorService")


@db_task(queue="tasks", context=True)
def huey_populate_whole_db(
    qv_map: Dict[int, Dict[int, int]], *, tracker_pk: int, task=None
) -> bool:
    PopulateEvacuateDBChore.transition_to_running(tracker_pk, task.id)
    N = len(qv_map)

    id_page_number = SpecificationService.get_id_page_number()
    dnm_page_numbers = SpecificationService.get_dnm_pages()
    question_page_numbers = SpecificationService.get_question_pages()
    pcs = PaperCreatorService()

    # TODO - move much of this loop back into paper-creator.
    for idx, (paper_number, qv_row) in enumerate(qv_map.items()):
        pcs._create_single_paper_from_qvmapping_and_pages(
            paper_number,
            qv_row,
            id_page_number=id_page_number,
            dnm_page_numbers=dnm_page_numbers,
            question_page_numbers=question_page_numbers,
        )

        if idx % 16 == 0:
            PopulateEvacuateDBChore.set_message_to_user(
                tracker_pk, f"Populated {idx} of {N} papers in database"
            )
            print(f"Populated {idx} of {N} papers in database")

    PopulateEvacuateDBChore.set_message_to_user(
        tracker_pk, f"Populated all {N} papers in database"
    )
    print(f"Populated all {N} papers in database")
    PopulateEvacuateDBChore.transition_to_complete(tracker_pk)
    # when chore is done it should be set to "obsolete"
    PopulateEvacuateDBChore.objects.filter(pk=tracker_pk).update(obsolete=True)
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
    print(f"Deleted all {N} papers from database")
    PopulateEvacuateDBChore.transition_to_complete(tracker_pk)
    # when chore is done it should be set to "obsolete"
    PopulateEvacuateDBChore.objects.filter(pk=tracker_pk).update(obsolete=True)
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

    @transaction.atomic()
    def _create_single_paper_from_qvmapping_and_pages(
        self,
        paper_number: int,
        qv_row: Dict[int, int],
        *,
        id_page_number: int | None = None,
        dnm_page_numbers: List[int] | None = None,
        question_page_numbers: Dict[int, List[int]] | None = None,
    ) -> None:
        """Creates tables for the given paper number from supplied information.

        Args:
            paper_number: The number of the paper being created
            qv_row: Mapping from each question index to
                version for this particular paper. Of the form ``{q: v}``.
        KWargs:
            id_page_number: (optionally) the id-page page-number
            dnm_page_numbers: (optionally) a list of the dnm pages
            question_page_numbers: (optionally) the pages of each question
        """
        if id_page_number is None:
            id_page_number = SpecificationService.get_id_page_number()
        if dnm_page_numbers is None:
            dnm_page_numbers = SpecificationService.get_dnm_pages()
        if question_page_numbers is None:
            question_page_numbers = SpecificationService.get_question_pages()

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
        for index, q_pages in question_page_numbers.items():
            q_idx = int(index)
            version = int(qv_row[q_idx])
            for pg in q_pages:
                QuestionPage.objects.create(
                    paper=paper_obj,
                    image=None,
                    page_number=int(pg),
                    question_index=q_idx,
                    version=version,
                )

    def assert_no_existing_chore(self):
        """Check that there is no existing (non-obsolate) populate / evacuate database chore.

        Raises:
            PlomDatabaseCreationError: when there is a chore already underway.
        """
        try:
            chore = PopulateEvacuateDBChore.objects.get(obsolete=False)
            if chore.action == PopulateEvacuateDBChore.POPULATE:
                raise PlomDatabaseCreationError("Papers are being populated.")
            else:
                raise PlomDatabaseCreationError("Papers are being deleted.")
        except ObjectDoesNotExist:
            pass
            # not currently being populated/evacuated.

    def is_chore_in_progress(self):
        return PopulateEvacuateDBChore.objects.filter(obsolete=False).exists()

    def is_populate_in_progress(self):
        return PopulateEvacuateDBChore.objects.filter(
            obsolete=False, action=PopulateEvacuateDBChore.POPULATE
        ).exists()

    def is_evacuate_in_progress(self):
        return PopulateEvacuateDBChore.objects.filter(
            obsolete=False, action=PopulateEvacuateDBChore.EVACUATE
        ).exists()

    def get_chore_message(self):
        try:
            return PopulateEvacuateDBChore.objects.get(obsolete=False).message
        except ObjectDoesNotExist:
            return None

    def add_all_papers_in_qv_map(
        self, qv_map: Dict[int, Dict[int, int]], *, background: bool = True
    ):
        """Build all the Paper and associated tables from the qv-map, but not the PDF files.

        Args:
            qv_map: For each paper give the question-version map.
                Of the form `{paper_number: {q: v}}`
        KWargs:
            background: populate the database in the background, or, if false,
                as a foreground process.

        Raises:
            PlomDependencyConflict: if there are papers already in the database.
        """
        assert_can_modify_qv_mapping_database()
        if Paper.objects.filter().exists():
            raise PlomDependencyConflict("Already papers in the database.")
        # check if there is an existing non-obsolete task
        self.assert_no_existing_chore()

        if background:
            self.populate_whole_db_huey_wrapper(qv_map)
        else:
            id_page_number = SpecificationService.get_id_page_number()
            dnm_page_numbers = SpecificationService.get_dnm_pages()
            question_page_numbers = SpecificationService.get_question_pages()
            for idx, (paper_number, qv_row) in enumerate(qv_map.items()):
                self._create_single_paper_from_qvmapping_and_pages(
                    paper_number,
                    qv_row,
                    id_page_number=id_page_number,
                    dnm_page_numbers=dnm_page_numbers,
                    question_page_numbers=question_page_numbers,
                )
                if idx % 16 == 0:
                    print(f"Added {idx} of {len(qv_map)} papers")
            print(f"Added all {len(qv_map)} papers")

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

    def remove_all_papers_from_db(self, *, background: bool = True) -> None:
        assert_can_modify_qv_mapping_database()
        # check if there is an existing non-obsolete task
        self.assert_no_existing_chore()

        if background:
            self.evacuate_whole_db_huey_wrapper()
        else:
            with transaction.atomic():
                DNMPage.objects.all().delete()
                IDPage.objects.all().delete()
                QuestionPage.objects.all().delete()
            with transaction.atomic():
                Paper.objects.all().delete()

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
