# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2026 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2026 Aidan Murphy

from collections.abc import Iterator
import logging
from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.db.utils import IntegrityError
from django.db import transaction
from django_huey import db_task
import huey
import huey.api

from plom.common.exceptions import PlomDatabaseCreationError
from plom_server.Preparation.services.preparation_dependency_service import (
    assert_can_modify_qv_mapping_database,
)
from ..services import SpecificationService
from ..models import Paper, FixedPage, PopulateEvacuateDBChore

log = logging.getLogger(__name__)


# The decorated function returns a ``huey.api.Result``
@db_task(queue="chores", context=True)
def huey_populate_whole_db(
    qv_map: dict[int, dict[int | str, int]],
    *,
    tracker_pk: int,
    task: huey.api.Task | None = None,
) -> bool:
    """Populate the database in a background Huey chore.

    Args:
        qv_map: the question-version map.

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
    N = len(qv_map)
    PopulateEvacuateDBChore.transition_to_running(
        tracker_pk, task.id, msg=f"Populating {N} papers in database..."
    )

    try:
        for idx, qv_row in PaperCreatorService._populate_from_qvmapping(qv_map):
            if idx % 16 == 0:
                PopulateEvacuateDBChore.set_message(
                    tracker_pk, f"Populated {idx} of {N} papers in database"
                )
                log.info(f"Populated {idx} of {N} papers in database")
    except KeyError as e:
        # increase verbosity, else it just prints like "4"
        PopulateEvacuateDBChore.set_message(
            tracker_pk, f"Populated {idx} of {N} papers in database"
        )
        raise KeyError(
            f"KeyError {e}: perhaps not enough columns in your upload?"
        ) from e
    except (ObjectDoesNotExist, IntegrityError):
        PopulateEvacuateDBChore.set_message(
            tracker_pk, f"Populated {idx} of {N} papers in database"
        )
        raise

    # TODO: currently we let the catch-all in Base/models.py handle exceptions but
    # we could do so here, avoiding errors in Huey logs... Which is better?
    # except Exception as e:
    #     PopulateEvacuateDBChore.transition_chore_to_error(
    #          tracker_pk,
    #          f"Something went wrong building database: {e}",
    #     )
    #     return True

    PopulateEvacuateDBChore.transition_to_complete(
        tracker_pk, msg=f"Populated all {N} papers in database"
    )
    log.info(f"Populated all {N} papers in database")
    return True


# The decorated function returns a ``huey.api.Result``
@db_task(queue="chores", context=True)
def huey_evacuate_whole_db(
    *, tracker_pk: int, task: huey.api.Task | None = None
) -> bool:
    """Populate the database in a background Huey chore.

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
    PopulateEvacuateDBChore.transition_to_running(
        tracker_pk, task.id, msg="Deleting all papers from database..."
    )
    all_papers = Paper.objects.all().prefetch_related("fixedpage_set")
    N = all_papers.count()
    for idx, papernum in PaperCreatorService._evacuate_qvmapping():
        if idx % 16 == 0:
            PopulateEvacuateDBChore.set_message(
                tracker_pk, f"Deleted {idx} of {N} papers from database"
            )
            log.info(f"Deleted {idx} of {N} papers from database")

    PopulateEvacuateDBChore.transition_to_complete(
        tracker_pk, msg=f"Deleted all {N} papers from database"
    )
    log.info(f"Deleted all {N} papers from database")
    return True


# The decorated function returns a ``huey.api.Result``
@db_task(queue="chores", context=True)
def huey_evacuate_then_populate_whole_db(
    qv_map: dict[int, dict[int | str, int]],
    *,
    tracker_pk: int,
    task: huey.api.Task | None = None,
) -> bool:
    """Evacuate then populate the database in a background Huey chore.

    Args:
        qv_map: the question-version map.

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
    # EVACUATE
    assert task is not None

    PopulateEvacuateDBChore.transition_to_running(
        tracker_pk, task.id, msg="Deleting all papers from database..."
    )
    all_papers = Paper.objects.all().prefetch_related("fixedpage_set")
    num_papers_old = all_papers.count()

    for idx, papernum in PaperCreatorService._evacuate_qvmapping():
        if idx % 16 == 0:
            PopulateEvacuateDBChore.set_message(
                tracker_pk, f"Deleted {idx} of {num_papers_old} papers from database"
            )
            log.info(f"Deleted {idx} of {num_papers_old} papers from database")

    PopulateEvacuateDBChore.set_message(
        tracker_pk, f"Deleted all {num_papers_old} papers from database"
    )
    log.info(f"Deleted all {num_papers_old} papers from database")

    # POPULATE
    # update chore.action from EVACUATE to POPULATE and lock the chore while doing this
    with transaction.atomic():
        chore = PopulateEvacuateDBChore.objects.select_for_update().get(pk=tracker_pk)
        chore.action = PopulateEvacuateDBChore.POPULATE
        chore.save()

    # assert task is not None
    num_papers_new = len(qv_map)
    PopulateEvacuateDBChore.set_message(
        tracker_pk, f"Populating {num_papers_new} papers in database..."
    )

    try:
        for idx, qv_row in PaperCreatorService._populate_from_qvmapping(qv_map):
            if idx % 16 == 0:
                PopulateEvacuateDBChore.set_message(
                    tracker_pk,
                    f"Populated {idx} of {num_papers_new} papers in database",
                )
                log.info(f"Populated {idx} of {num_papers_new} papers in database")
    except KeyError as e:
        # increase verbosity, else it just prints like "4"
        PopulateEvacuateDBChore.set_message(
            tracker_pk, f"Populated {idx} of {num_papers_new} papers in database"
        )
        raise KeyError(
            f"KeyError {e}: perhaps not enough columns in your upload?"
        ) from e
    except (ObjectDoesNotExist, IntegrityError):
        PopulateEvacuateDBChore.set_message(
            tracker_pk, f"Populated {idx} of {num_papers_new} papers in database"
        )
        raise

    # TODO: currently we let the catch-all in Base/models.py handle exceptions but
    # we could do so here, avoiding errors in Huey logs... Which is better?
    # except Exception as e:
    #     PopulateEvacuateDBChore.transition_chore_to_error(
    #          tracker_pk,
    #          f"Something went wrong building database: {e}",
    #     )
    #     return True

    PopulateEvacuateDBChore.transition_to_complete(
        tracker_pk, msg=f"Populated all {num_papers_new} papers in database"
    )
    log.info(f"Populated all {num_papers_new} papers in database")
    return True


class PaperCreatorService:
    """Class to encapsulate functions to build the test-papers and groups in the DB.

    No need to instantiate: all methods can be called from the class.
    """

    @classmethod
    def _populate_from_qvmapping(
        cls, qv_map: dict[int, dict[int | str, int]]
    ) -> Iterator[tuple[int, dict]]:
        """Populate the DB from a qvmap.

        We yield information so huey can record progress when calling this function.
        Unfortunately this means we can't use a transaction decorator; callers are
        responsible for rolling back changes on failure.

        Args:
            qv_map: The question version map.

        Yields:
            A tuple containing the index and an informational dict for the
            most recently populated paper.
        """
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
            yield idx, qv_row

    @staticmethod
    @transaction.atomic()
    def _create_single_paper_from_qvmapping_and_pages(
        paper_number: int,
        qv_row: dict[Any, int],
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
                Optionally contains the key `"id"`, the value of which
                is assumed to be 1 if omitted.

        Keyword Args:
            id_page_number: (optionally) the id-page page-number
            dnm_page_numbers: (optionally) a list of the dnm pages
            question_page_numbers: (optionally) the pages of each question

        Returns:
            None

        Raises:
            ObjectDoesNotExist: no spec.
            IntegrityError: that paper number already exists.
            KeyError: problem with qvmap input.
        """
        if id_page_number is None:
            id_page_number = SpecificationService.get_id_page_number()
        if dnm_page_numbers is None:
            dnm_page_numbers = SpecificationService.get_dnm_pages()
        if question_page_numbers is None:
            question_page_numbers = SpecificationService.get_question_pages()

        paper_obj = Paper.objects.create(paper_number=paper_number)

        # we do this to improve race conditions
        paper_obj = Paper.objects.select_for_update().get(id=paper_obj.id)

        fixed_pages = []
        fixed_pages.append(
            FixedPage(
                page_type=FixedPage.IDPAGE,
                paper=paper_obj,
                image=None,
                page_number=id_page_number,
                version=qv_row.get("id", 1),
            )
        )
        # currently DNM pages are always taken from version 1
        for pg in dnm_page_numbers:
            fixed_pages.append(
                FixedPage(
                    page_type=FixedPage.DNMPAGE,
                    paper=paper_obj,
                    image=None,
                    page_number=pg,
                    version=1,
                )
            )
        for index, q_pages in question_page_numbers.items():
            q_idx = int(index)
            version = int(qv_row[q_idx])
            for pg in q_pages:
                fixed_pages.append(
                    FixedPage(
                        page_type=FixedPage.QUESTIONPAGE,
                        paper=paper_obj,
                        image=None,
                        page_number=int(pg),
                        question_index=q_idx,
                        version=version,
                    )
                )
        FixedPage.objects.bulk_create(fixed_pages)

    @staticmethod
    def _evacuate_qvmapping() -> Iterator[tuple[int, int]]:
        """Remove all papers from the DB.

        We yield information so huey can record progress when calling this function.
        Unfortunately this means we can't use a transaction decorator; callers are
        responsible for rolling back changes on failure.

        Yields:
            As a tuple: the running count of the number of papers removed and the
            paper number of the most recently removed paper.
        """
        all_papers = Paper.objects.all().prefetch_related("fixedpage_set")

        for idx, paper_obj in enumerate(all_papers):
            for fp in paper_obj.fixedpage_set.all():
                fp.delete()
            papernum = paper_obj.paper_number
            paper_obj.delete()
            yield idx, papernum
        # TODO - decide if we should delete by table rather than by paper.
        # Table delete code follows below
        # with transaction.atomic():
        #     FixedPage.objects.all().delete()
        #     Paper.objects.all().delete()

    @staticmethod
    def assert_no_running_chore():
        """Check for currently-running populate / evacuate database chores.

        Note, even if the chores are obsolete we still say chores are underway.
        This is b/c they would finish and change the database.

        Raises:
            PlomDatabaseCreationError: when there is a chore already underway.
        """
        # Error or Complete are not running: all other states could soon be running
        for chore in PopulateEvacuateDBChore.objects.filter(
            status__in=(
                PopulateEvacuateDBChore.TO_DO,
                PopulateEvacuateDBChore.STARTING,
                PopulateEvacuateDBChore.QUEUED,
                PopulateEvacuateDBChore.RUNNING,
            )
        ):
            if chore.action == PopulateEvacuateDBChore.POPULATE:
                raise PlomDatabaseCreationError("Papers are being populated.")
            else:
                raise PlomDatabaseCreationError("Papers are being deleted.")

    @staticmethod
    def obselete_all_existing_chores():
        """Set the "obsolete" flag to True on all Huey chores."""
        PopulateEvacuateDBChore.objects.filter(obsolete=False).update(obsolete=True)
        # TODO: check that this doesn't do superclass as well!
        # TODO: can probably verify by `print(cls)` in the superclass code
        # PopulateEvacuateDBChore.set_every_task_obsolete()

    @staticmethod
    def is_background_chore_in_progress() -> bool:
        """Are any populate/evacuate chores currently running in the background?"""
        return PopulateEvacuateDBChore.objects.filter(
            obsolete=False,
            status__in=(
                PopulateEvacuateDBChore.TO_DO,
                PopulateEvacuateDBChore.STARTING,
                PopulateEvacuateDBChore.QUEUED,
                PopulateEvacuateDBChore.RUNNING,
            ),
        ).exists()

    @staticmethod
    def is_populate_in_progress() -> bool:
        """Are any populate chores currently running?"""
        return PopulateEvacuateDBChore.objects.filter(
            obsolete=False,
            action=PopulateEvacuateDBChore.POPULATE,
            status__in=(
                PopulateEvacuateDBChore.TO_DO,
                PopulateEvacuateDBChore.STARTING,
                PopulateEvacuateDBChore.QUEUED,
                PopulateEvacuateDBChore.RUNNING,
            ),
        ).exists()

    @staticmethod
    def is_evacuate_in_progress() -> bool:
        """Are any evacuate chores currently running?"""
        return PopulateEvacuateDBChore.objects.filter(
            obsolete=False,
            action=PopulateEvacuateDBChore.EVACUATE,
            status__in=(
                PopulateEvacuateDBChore.TO_DO,
                PopulateEvacuateDBChore.STARTING,
                PopulateEvacuateDBChore.QUEUED,
                PopulateEvacuateDBChore.RUNNING,
            ),
        ).exists()

    @staticmethod
    def get_chore_message() -> str | None:
        """Return the current message or None if there are no non-obsolete chores."""
        try:
            return PopulateEvacuateDBChore.objects.get(obsolete=False).message
        except ObjectDoesNotExist:
            return None

    @staticmethod
    def get_chore_status() -> str | None:
        """Get the chore status string, or None if there are no non-obsolete chores.

        The chore status is autorendered from IntegerChoices in the parent model.
        """
        try:
            the_chore = PopulateEvacuateDBChore.objects.filter(obsolete=False).get()
        except PopulateEvacuateDBChore.DoesNotExist:
            return None
        return the_chore.get_status_display()

    @classmethod
    def add_all_papers_in_qv_map(
        cls,
        qv_map: dict[int, dict[int | str, int]],
        *,
        background: bool = True,
    ):
        """Build all the Paper and associated tables from the qv-map, but not the PDF files.

        Args:
            qv_map: For each paper give the question-version map.
                Of the form `{paper_number: {q: v}}`

        Keyword Args:
            background: populate the database in the background, or, if false,
                as a synchronous, non-huey, process

        Raises:
            PlomDependencyConflict: if preparation dependencies are not met.
            PlomDatabaseCreationError: if there are papers already in the database
                or a task is in an error state.
        """
        assert_can_modify_qv_mapping_database()
        if Paper.objects.filter().exists():
            raise PlomDatabaseCreationError("Already papers in the database.")
        # check if there is an existing non-obsolete task
        cls.assert_no_running_chore()
        cls.obselete_all_existing_chores()

        if background:
            cls._populate_whole_db_huey_wrapper(qv_map)
        else:
            log.info(
                "Running populate task in foreground - will block until completed."
            )
            with transaction.atomic():
                for _ in cls._populate_from_qvmapping(qv_map):
                    pass
            log.info("Populate task finished!")

    @classmethod
    def append_papers_to_qv_map(
        cls,
        qv_map: dict[int, dict[int | str, int]],
    ):
        """Build additional Papers and associated tables from the qv-map, but not the PDF files.

        This method is used to add additional papers (rather than working
        from an empty state).  It might be less efficient for a large
        number of papers, as each work is done sequentially rather than in
        bulk.  If this becomes a bottleneck, this function could probably
        be improved.

        Args:
            qv_map: For each paper give the question-version map.
                Of the form `{paper_number: {q: v}}`

        Raises:
            PlomDependencyConflict: if preparation dependencies are not met.
            PlomDatabaseCreationError: if there are papers already in the database.
            IntegrityError: already have that row.
        """
        # even with force you don't get to bully; other people are playing here!
        cls.assert_no_running_chore()
        cls.obselete_all_existing_chores()

        for idx, (paper_number, qv_row) in enumerate(qv_map.items()):
            with transaction.atomic(durable=True):
                # todo: is durable correct?  I want both to fail or both succeed

                # loop hammers the Settings database: how many might we be appending?
                cls._create_single_paper_from_qvmapping_and_pages(
                    paper_number,
                    qv_row,
                )

    @staticmethod
    def _populate_whole_db_huey_wrapper(
        qv_map: dict[int, dict[int | str, int]],
    ) -> None:
        """Instantiate a huey tracker, then start the task."""
        # TODO - add seatbelt logic here
        with transaction.atomic(durable=True):
            tr = PopulateEvacuateDBChore.objects.create(
                status=PopulateEvacuateDBChore.STARTING,
                action=PopulateEvacuateDBChore.POPULATE,
            )
            tracker_pk = tr.pk

        res = huey_populate_whole_db(qv_map, tracker_pk=tracker_pk)
        log.info(f"Just enqueued Huey populate-database task id={res.id}")

        PopulateEvacuateDBChore.transition_to_queued_or_running(tracker_pk, res.id)

    @classmethod
    def remove_all_papers_from_db(cls, *, background: bool = True) -> None:
        """Remove all the papers and associated objects from the database.

        Keyword Args:
            background: de-populate the database in the background, or, if false,
                as a synchronous, non-huey process.

        Raises:
            PlomDependencyConflict: if preparation dependencies are not met.
            PlomDatabaseCreationError: if a database populate/evacuate chore already underway.
        """
        assert_can_modify_qv_mapping_database(deleting=True)
        cls.assert_no_running_chore()
        cls.obselete_all_existing_chores()

        if background:
            cls._evacuate_whole_db_huey_wrapper()
        else:
            log.info(
                "Running evacuate task in foreground - will block until completed."
            )
            with transaction.atomic():
                for _ in cls._evacuate_qvmapping():
                    pass
            log.info("Evacuate task finished!")

    @staticmethod
    def _evacuate_whole_db_huey_wrapper() -> None:
        """Instantiate a huey tracker, then start the task."""
        # TODO - add seatbelt logic here
        with transaction.atomic(durable=True):
            tr = PopulateEvacuateDBChore.objects.create(
                status=PopulateEvacuateDBChore.STARTING,
                action=PopulateEvacuateDBChore.EVACUATE,
            )
            tracker_pk = tr.pk

        res = huey_evacuate_whole_db(tracker_pk=tracker_pk)
        log.info(f"Just enqueued Huey evacuate-database task id={res.id}")

        PopulateEvacuateDBChore.transition_to_queued_or_running(tracker_pk, res.id)

    @classmethod
    def replace_all_papers_in_qv_map(
        cls,
        qv_map: dict[int, dict[int | str, int]],
        *,
        background: bool = True,
    ):
        """Remove existing Papers and pages from the db, then repopulate.

        Args:
            qv_map: For each paper give the question-version map.
                Of the form `{paper_number: {q: v}}`

        Keyword Args:
            background: evacuate then populate the database in the background, or,
                if false, as a synchronous, non-huey process

        Raises:
            PlomDependencyConflict: if preparation dependencies are not met.
            PlomDatabaseCreationError: if there are papers already in the database
                or a task is in an error state.
        """
        assert_can_modify_qv_mapping_database()
        # check if there is an existing non-obsolete task
        cls.assert_no_running_chore()
        cls.obselete_all_existing_chores()

        if background:
            cls._evacuate_then_populate_whole_db_huey_wrapper(qv_map)
        else:
            log.info(
                "Running evacuate-then-populate task in foreground - will block until completed."
            )
            with transaction.atomic():
                for _ in cls._evacuate_qvmapping():
                    pass
                for _ in cls._populate_from_qvmapping(qv_map):
                    pass
            log.info("Evacuate-then-populate task finished!")

    @staticmethod
    def _evacuate_then_populate_whole_db_huey_wrapper(
        qv_map: dict[int, dict[int | str, int]],
    ) -> None:
        """Instantiate a huey tracker, then start the task."""
        # TODO - add seatbelt logic here
        # ^^ What does this mean?
        with transaction.atomic(durable=True):
            tr = PopulateEvacuateDBChore.objects.create(
                status=PopulateEvacuateDBChore.STARTING,
                action=PopulateEvacuateDBChore.EVACUATE,
            )
            tracker_pk = tr.pk

        res = huey_evacuate_then_populate_whole_db(qv_map, tracker_pk=tracker_pk)
        log.info(f"Just enqueued Huey evacuate-populate-database task id={res.id}")

        PopulateEvacuateDBChore.transition_to_queued_or_running(tracker_pk, res.id)
