# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov

from __future__ import annotations

import logging

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django_huey import db_task

from plom.plom_exceptions import PlomDatabaseCreationError
from Preparation.services.preparation_dependency_service import (
    assert_can_modify_qv_mapping_database,
)
from ..services import SpecificationService
from ..models import (
    Paper,
    IDPage,
    DNMPage,
    QuestionPage,
    PopulateEvacuateDBChore,
    NumberOfPapersToProduceSetting,
)

log = logging.getLogger("PaperCreatorService")


@db_task(queue="tasks", context=True)
def huey_populate_whole_db(
    qv_map: dict[int, dict[int, int]], *, tracker_pk: int, task=None
) -> bool:
    PopulateEvacuateDBChore.transition_to_running(tracker_pk, task.id)
    N = len(qv_map)

    id_page_number = SpecificationService.get_id_page_number()
    dnm_page_numbers = SpecificationService.get_dnm_pages()
    question_page_numbers = SpecificationService.get_question_pages()

    # TODO - move much of this loop back into paper-creator.
    for idx, (paper_number, qv_row) in enumerate(qv_map.items()):
        PaperCreatorService._create_single_paper_from_qvmapping_and_pages(
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
    # TODO - decide if we should delete by table rather than by paper.
    # Table delete code follows below
    # with transaction.atomic():
    #     DNMPage.objects.all().delete()
    #     IDPage.objects.all().delete()
    #     QuestionPage.objects.all().delete()
    # with transaction.atomic():
    #     Paper.objects.all().delete()

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

    No need to instantiate: all methods can be called from the class.
    """

    @staticmethod
    def _set_number_to_produce(numberToProduce: int) -> None:
        nop = NumberOfPapersToProduceSetting.load()
        nop.number_of_papers = numberToProduce
        nop.save()

    @staticmethod
    def _increment_number_to_produce() -> None:
        nop = NumberOfPapersToProduceSetting.load()
        nop.number_of_papers += 1
        nop.save()

    @classmethod
    def _reset_number_to_produce(cls) -> None:
        cls._set_number_to_produce(0)

    @staticmethod
    @transaction.atomic()
    def _create_single_paper_from_qvmapping_and_pages(
        paper_number: int,
        qv_row: dict[int, int],
        *,
        id_page_number: int | None = None,
        dnm_page_numbers: list[int] | None = None,
        question_page_numbers: dict[int, list[int]] | None = None,
    ) -> None:
        """Creates tables for the given paper number from supplied information.

        Note that this (optionally) takes several kwargs so that the spec does
        not have to be polled for each paper.

        Args:
            paper_number: The number of the paper being created
            qv_row: Mapping from each question index to
                version for this particular paper. Of the form ``{q: v}``.

        Keyword Args:
            id_page_number: (optionally) the id-page page-number
            dnm_page_numbers: (optionally) a list of the dnm pages
            question_page_numbers: (optionally) the pages of each question

        Returns:
            None

        Raises:
            ObjectDoesNotExist: no spec.
            IntegrityError: that paper number already exists.
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

    @staticmethod
    def assert_no_existing_chore():
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

    @staticmethod
    def is_chore_in_progress():
        return PopulateEvacuateDBChore.objects.filter(obsolete=False).exists()

    @staticmethod
    def is_populate_in_progress():
        return PopulateEvacuateDBChore.objects.filter(
            obsolete=False, action=PopulateEvacuateDBChore.POPULATE
        ).exists()

    @staticmethod
    def is_evacuate_in_progress():
        return PopulateEvacuateDBChore.objects.filter(
            obsolete=False, action=PopulateEvacuateDBChore.EVACUATE
        ).exists()

    @staticmethod
    def get_chore_message():
        try:
            return PopulateEvacuateDBChore.objects.get(obsolete=False).message
        except ObjectDoesNotExist:
            return None

    @classmethod
    def add_all_papers_in_qv_map(
        cls,
        qv_map: dict[int, dict[int, int]],
        *,
        background: bool = True,
        _testing: bool = False,
    ):
        """Build all the Paper and associated tables from the qv-map, but not the PDF files.

        Args:
            qv_map: For each paper give the question-version map.
                Of the form `{paper_number: {q: v}}`

        Keyword Args:
            background: populate the database in the background, or, if false,
                as a blocking huey process
            _testing: when set true, blocking is ignored, and the db-build is done as
                a foreground process without huey involved.

        Raises:
            PlomDependencyConflict: if preparation dependencies are not met.
            PlomDatabaseCreationError: if there are papers already in the database.
        """
        assert_can_modify_qv_mapping_database()
        if Paper.objects.filter().exists():
            raise PlomDatabaseCreationError("Already papers in the database.")
        # check if there is an existing non-obsolete task
        cls.assert_no_existing_chore()
        cls._set_number_to_produce(len(qv_map))

        if not _testing:
            cls._populate_whole_db_huey_wrapper(qv_map, background=background)
        else:
            # log(f"Adding {len(qv_map)} papers via foreground process for testing")
            id_page_number = SpecificationService.get_id_page_number()
            dnm_page_numbers = SpecificationService.get_dnm_pages()
            question_page_numbers = SpecificationService.get_question_pages()
            for idx, (paper_number, qv_row) in enumerate(qv_map.items()):
                cls._create_single_paper_from_qvmapping_and_pages(
                    paper_number,
                    qv_row,
                    id_page_number=id_page_number,
                    dnm_page_numbers=dnm_page_numbers,
                    question_page_numbers=question_page_numbers,
                )

    @classmethod
    def append_papers_to_qv_map(
        cls,
        qv_map: dict[int, dict[int, int]],
        *,
        force: bool = False,
    ):
        """Build all the Paper and associated tables from the qv-map, but not the PDF files.

        Args:
            qv_map: For each paper give the question-version map.
                Of the form `{paper_number: {q: v}}`

        Keyword Args:
            force: if true, we don't check if we can modify the map, just try it.

        Raises:
            PlomDependencyConflict: if preparation dependencies are not met.
            PlomDatabaseCreationError: if there are papers already in the database.
            IntegrityError: already have that row.
        """
        if not force:
            assert_can_modify_qv_mapping_database()
            if Paper.objects.filter().exists():
                raise PlomDatabaseCreationError("Already papers in the database.")

        # even with force you don't get to bully; other people are playing here!
        # check if there is an existing non-obsolete task
        cls.assert_no_existing_chore()

        for idx, (paper_number, qv_row) in enumerate(qv_map.items()):
            with transaction.atomic(durable=True):
                # todo: is durable correct?  I want both to fail or both succeed
                cls._increment_number_to_produce()
                cls._create_single_paper_from_qvmapping_and_pages(
                    paper_number,
                    qv_row,
                )

    @staticmethod
    def _populate_whole_db_huey_wrapper(
        qv_map: dict[int, dict[int, int]], *, background: bool = True
    ) -> None:
        # TODO - add seatbelt logic here
        with transaction.atomic(durable=True):
            tr = PopulateEvacuateDBChore.objects.create(
                status=PopulateEvacuateDBChore.STARTING,
                action=PopulateEvacuateDBChore.POPULATE,
            )
            tracker_pk = tr.pk

        res = huey_populate_whole_db(qv_map, tracker_pk=tracker_pk)
        print(f"Just enqueued Huey populate-database task id={res.id}")
        if background is False:
            print("Running the task in foreground - will block until completed.")
            res.get(blocking=True)
            print("Completed.")
        else:
            PopulateEvacuateDBChore.transition_to_queued_or_running(tracker_pk, res.id)

    @classmethod
    def remove_all_papers_from_db(
        cls, *, background: bool = True, _testing: bool = False
    ) -> None:
        """Remove all the papers and associated objects from the database.

        Keyword Args:
            background: de-populate the database in the background, or, if false,
                as a blocking huey process
            _testing: when set true, blocking is ignored, and the db depopulation is done as
                a foreground process without huey involved.

        Raises:
            PlomDependencyConflict: if preparation dependencies are not met.
            PlomDatabaseCreationError: if a database populate/evacuate chore already underway.
        """
        assert_can_modify_qv_mapping_database()
        # check if there is an existing non-obsolete task
        cls.assert_no_existing_chore()
        cls._reset_number_to_produce()

        if not _testing:
            cls._evacuate_whole_db_huey_wrapper(background=background)
        else:
            # for testing purposes we delete in foreground
            with transaction.atomic():
                DNMPage.objects.all().delete()
                IDPage.objects.all().delete()
                QuestionPage.objects.all().delete()
            with transaction.atomic():
                Paper.objects.all().delete()

    @staticmethod
    def _evacuate_whole_db_huey_wrapper(*, background: bool = True) -> None:
        # TODO - add seatbelt logic here
        with transaction.atomic(durable=True):
            tr = PopulateEvacuateDBChore.objects.create(
                status=PopulateEvacuateDBChore.STARTING,
                action=PopulateEvacuateDBChore.EVACUATE,
            )
            tracker_pk = tr.pk

        res = huey_evacuate_whole_db(tracker_pk=tracker_pk)
        print(f"Just enqueued Huey evacuate-database task id={res.id}")
        if background is False:
            print("Running the task in foreground - will block until completed.")
            res.get(blocking=True)
            print("Completed.")
        else:
            PopulateEvacuateDBChore.transition_to_queued_or_running(tracker_pk, res.id)
