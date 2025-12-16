# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024-2025 Colin B. Macdonald
# Copyright (C) 2025 Deep Shah

from typing import Any

from django.db import transaction
from django.db.models import Count, Min, Max

from plom.misc_utils import pprint_score

from plom_server.Identify.models import PaperIDTask
from plom_server.Mark.models import MarkingTask
from plom_server.Papers.services import SpecificationService, PaperInfoService


class ProgressOverviewService:
    @transaction.atomic
    def get_id_task_status(self) -> list[dict]:
        id_info = []
        for task in PaperIDTask.objects.exclude(
            status=PaperIDTask.OUT_OF_DATE
        ).prefetch_related("paper", "latest_action", "assigned_user"):
            dat = {
                "paper": task.paper.paper_number,
                "status": task.get_status_display(),
            }
            if task.status in [PaperIDTask.OUT, PaperIDTask.COMPLETE]:
                dat["user"] = task.assigned_user.username
            if task.status == MarkingTask.COMPLETE:
                dat["sid"] = task.latest_action.student_id
            id_info.append(dat)

        return id_info

    @transaction.atomic
    def get_marking_task_status(self) -> list[dict]:
        marking_info = []
        for task in MarkingTask.objects.exclude(
            status=MarkingTask.OUT_OF_DATE
        ).prefetch_related("paper", "latest_annotation", "assigned_user"):
            # task status is one of to_do, out, complete
            dat = {
                "paper": task.paper.paper_number,
                "status": task.get_status_display(),
                "question": task.question_index,
                "version": task.question_version,
                "task_pk": task.pk,
            }
            if task.status == MarkingTask.OUT:
                dat["user"] = task.assigned_user.username
            if task.status == MarkingTask.COMPLETE:
                dat["user"] = task.assigned_user.username
                dat["score"] = task.latest_annotation.score
                dat["score_str"] = pprint_score(task.latest_annotation.score)

            marking_info.append(dat)
        return marking_info

    @transaction.atomic
    def get_task_overview(self) -> tuple[dict, dict]:
        """Return (id-info, marking-info) dicts with info for all id and marking tasks of every paper in use.

        Note that a paper is in use if it has at least one ID or marking task.

        ID-info dict is either {paper_number: None} if task not present, or {paper_number: data} where data is itself a dict of the form
          * {status: 'To do'} or
          * {'status': 'Out', 'user': username} - the name of the user who has the task
          * {status: 'Complete', 'user': username, 'sid': student_id} - user who did the id'ing and the student-id of that paper.

        Marking-info dict is of the form {paper_number: {1: dat, 2:dat, ..., n: dat} } with data for each question. For each question we have
          * {status: 'To do', 'task_pk': blah} or
          * {'status': 'Out', 'user': username, 'task_pk': blah} - the name of the user who has the task
          * {status: 'Complete', 'user': username, 'score': score, 'task_pk: blah} - user who did the marking'ing, the score, and the pk of the corresponding marking task.
        """
        id_task_overview: dict[int, None | dict[str, Any]] = {}
        marking_task_overview: dict[int, dict[int, None | dict[str, Any]]] = {}
        question_indices = SpecificationService.get_question_indices()

        id_info = self.get_id_task_status()
        marking_info = self.get_marking_task_status()
        # get all the paper numbers that have **some** task
        papers_with_id_task = [X["paper"] for X in id_info]
        papers_with_marking_task = [X["paper"] for X in marking_info]
        papers_with_some_task = list(
            set(papers_with_id_task + papers_with_marking_task)
        )
        # now set up the over-view dicts so that we know about any missing tasks
        for paper_number in papers_with_some_task:
            id_task_overview[paper_number] = None
            marking_task_overview[paper_number] = {qn: None for qn in question_indices}
        # now put the data into those dictionaries
        # we will have Nones where the tasks are missing
        for dat in id_info:
            id_task_overview[dat["paper"]] = dat
        for dat in marking_info:
            marking_task_overview[dat["paper"]][dat["question"]] = dat

        return (id_task_overview, marking_task_overview)

    @staticmethod
    def n_papers_with_at_least_one_marking_task() -> int:
        """The number of papers that are currently being marked."""
        # Note prefetch("papers") is unnecessary with values_list
        tasks = MarkingTask.objects.exclude(status=MarkingTask.OUT_OF_DATE)
        return tasks.values_list("paper__paper_number", flat=True).distinct().count()

    @staticmethod
    def n_papers_with_at_least_one_task() -> int:
        """The number of papers that are currently being marked and IDed."""
        # Note prefetch("papers") is unnecessary with values_list
        tasks1 = MarkingTask.objects.exclude(status=MarkingTask.OUT_OF_DATE)
        tasks2 = PaperIDTask.objects.exclude(status=PaperIDTask.OUT_OF_DATE)
        inuse_papers = set(
            tasks1.values_list("paper__paper_number", flat=True).distinct()
        )
        inuse_papers = inuse_papers.union(
            tasks2.values_list("paper__paper_number", flat=True).distinct()
        )
        return len(inuse_papers)

    @staticmethod
    def n_marking_tasks_for_each_question() -> dict[int, int]:
        """Return the number of marking tasks for each question, as a dict keyed by question index."""
        tasks = MarkingTask.objects.exclude(status=MarkingTask.OUT_OF_DATE)
        question_indices = SpecificationService.get_question_indices()
        # Perhaps fewer queries to work with pairs (qi, papernum):
        # tasks.values_list("question_index", "paper__paper_number")
        return {
            qi: tasks.filter(question_index=qi)
            .values_list("paper__paper_number", flat=True)
            .distinct()
            .count()
            for qi in question_indices
        }

    @staticmethod
    def _missing_task_pq_pairs() -> list[tuple[int, int]]:
        """Return which tasks (p, q) are missing from each question, compared against the in-use papers."""
        tasks = MarkingTask.objects.exclude(status=MarkingTask.OUT_OF_DATE)
        id_tasks = PaperIDTask.objects.exclude(status=PaperIDTask.OUT_OF_DATE)
        question_indices = SpecificationService.get_question_indices()
        # extract (qi, papernum) pairs from the database, for offline processing
        pairs = list(
            tasks.values_list("question_index", "paper__paper_number").distinct()
        )

        inuse_papers = set([pn for q, pn in pairs])
        # augment with ID tasks in case there are papers with no marking tasks
        inuse_papers = inuse_papers.union(
            id_tasks.values_list("paper__paper_number", flat=True).distinct()
        )

        notfound = {}
        for qi in question_indices:
            inuse_q = set([pn for q, pn in pairs if q == qi])
            notfound[qi] = list(inuse_papers.difference(inuse_q))
        missing_pairs = [(pn, qi) for qi, papers in notfound.items() for pn in papers]
        return missing_pairs

    @classmethod
    def _missing_task_pqv_triplets(cls) -> list[tuple[int, int, int]]:
        """Return which tasks (p, q, v) are missing from each question, compared against the in-use papers."""
        missing_pairs = cls._missing_task_pq_pairs()
        # TODO: N more DB queries, expensive if many missing: need a bulk version getter?
        # TODO: for example, one could get the qvmap and query offline, or just get the QuestionPages
        # (which exist even if the paper isn't in-use!)
        missing_triplets = [
            (pn, qi, PaperInfoService.get_version_from_paper_question(pn, qi))
            for pn, qi in missing_pairs
        ]
        return missing_triplets

    @staticmethod
    def n_missing_marking_tasks_for_each_question() -> dict[int, int]:
        """Return the number of missing marking tasks for each question, as a dict keyed by question index.

        Note: its harder to find this at the level of versions.  I think
        this would have to involve looking at the incomplete papers, to check
        which specific versions are missing.
        """
        tasks = MarkingTask.objects.exclude(status=MarkingTask.OUT_OF_DATE)
        question_indices = SpecificationService.get_question_indices()
        N = tasks.values_list("paper__paper_number", flat=True).distinct().count()
        return {
            qi: N
            - tasks.filter(question_index=qi)
            .values_list("paper__paper_number", flat=True)
            .distinct()
            .count()
            for qi in question_indices
        }

    @transaction.atomic
    def get_completed_id_task_count(self) -> int:
        """Return number of completed ID tasks."""
        return PaperIDTask.objects.filter(status=PaperIDTask.COMPLETE).count()

    @transaction.atomic
    def get_completed_marking_task_counts(self) -> dict:
        """Return dict of number of completed marking tasks for each question."""
        return {
            qi: MarkingTask.objects.filter(
                question_index=qi, status=PaperIDTask.COMPLETE
            ).count()
            for qi in SpecificationService.get_question_indices()
        }

    def get_completed_task_counts(self) -> dict:
        return {
            "id": self.get_completed_id_task_count(),
            "mk": self.get_completed_marking_task_counts(),
        }

    @classmethod
    @transaction.atomic
    def get_id_task_status_counts(
        cls,
        *,
        _n_papers: int | None = None,
    ) -> dict[str, int]:
        """Return a dict of counts of ID tasks by their status.

        Keyword Args:
            _n_papers: this speeds up "Missing" calculations b/c we avoid
                additional database queries.  If omitted, we compute it.

        Note that this excludes out-of-date tasks.
        """
        counts = {
            MarkingTask.TO_DO.label: 0,
            MarkingTask.COMPLETE.label: 0,
            MarkingTask.OUT.label: 0,
        }

        tasks_query = PaperIDTask.objects.exclude(status=PaperIDTask.OUT_OF_DATE)
        for X in tasks_query.values("status").annotate(count=Count("status")):
            status_label = MarkingTask.StatusChoices(X["status"]).label
            counts[status_label] = X["count"]

        if _n_papers is None:
            # Note: wrong if papers with id task but no marking task
            # n_papers = cls.n_papers_with_at_least_one_marking_task()
            n_papers = cls.n_papers_with_at_least_one_task()
        else:
            n_papers = _n_papers
        present = sum([v for x, v in counts.items()])
        counts.update({"Missing": n_papers - present, "total": n_papers})
        return counts

    @classmethod
    @transaction.atomic
    def get_mark_task_status_counts(
        cls, *, _n_papers: int | None = None
    ) -> dict[int, dict[str, int]]:
        """Return a dict of counts of marking tasks by their status for each question.

        Keyword Args:
            _n_papers: this speeds up "Missing" calculations b/c we avoid
                additional database queries.  If omitted, we compute it.

        Returns:
            A dict of dict - one for each question-index (and int).
            For each index the dict is "{status: count}" for each of
            "To Do", "Complete", "Out", "Missing" and "total".
        """
        qindices = SpecificationService.get_question_indices()
        assert len(MarkingTask.StatusChoices) == 4, "Code assumes 4 choices in enum"
        dict_of_counts = {
            qi: {
                MarkingTask.TO_DO.label: 0,
                MarkingTask.COMPLETE.label: 0,
                MarkingTask.OUT.label: 0,
            }
            for qi in qindices
        }

        tasks_query = MarkingTask.objects.exclude(status=MarkingTask.OUT_OF_DATE)

        for X in tasks_query.values("status", "question_index").annotate(
            count=Count("status")
        ):
            status_label = MarkingTask.StatusChoices(X["status"]).label
            dict_of_counts[X["question_index"]][status_label] = X["count"]

        if _n_papers is None:
            n_papers = cls.n_papers_with_at_least_one_task()
        else:
            n_papers = _n_papers
        for qi, d in dict_of_counts.items():
            present = sum([c for k, c in d.items()])
            # max 0 just in case of programming error
            d.update({"Missing": max(0, n_papers - present), "total": n_papers})

        return dict_of_counts

    @classmethod
    @transaction.atomic
    def get_mark_task_status_counts_by_qv(
        cls,
        question_index: int | None = None,
        version: int | None = None,
    ) -> dict[str, int]:
        """Return a dict of counts of marking tasks by their status for the given question/version.

        Args:
            question_index: restrict to a particular question.  If omitted
                (or None) then count without question restriction.
            version: restrict to a particular version.  If omitted (or None)
                then count without version restriction.

        Returns:
            A dict with keys "To Do", "Complete", "Out", "Missing" and "total".

        Note that this excludes out-of-date tasks.
        """
        assert len(MarkingTask.StatusChoices) == 4, "Code assumes 4 choices in enum"
        counts = {
            MarkingTask.TO_DO.label: 0,
            MarkingTask.COMPLETE.label: 0,
            MarkingTask.OUT.label: 0,
        }

        tasks_query = MarkingTask.objects.exclude(status=MarkingTask.OUT_OF_DATE)

        if question_index is not None:
            tasks_query = tasks_query.filter(question_index=question_index)
        if version is not None:
            tasks_query = tasks_query.filter(question_version=version)

        for X in tasks_query.values("status").annotate(count=Count("status")):
            status_label = MarkingTask.StatusChoices(X["status"]).label
            counts[status_label] = X["count"]

        if version is None:
            pairs = cls._missing_task_pq_pairs()
            if question_index is None:
                counts["Missing"] = len(pairs)
            else:
                counts["Missing"] = len([p for p, q in pairs if q == question_index])
        else:
            triplets = cls._missing_task_pqv_triplets()
            if question_index is None:
                counts["Missing"] = len([p for p, q, v in triplets if v == version])
            else:
                counts["Missing"] = len(
                    [p for p, q, v in triplets if (q, v) == (question_index, version)]
                )

        counts["total"] = sum([n for k, n in counts.items()])
        return counts

    @transaction.atomic
    def get_first_last_used_paper_number(self) -> tuple[int, int]:
        """Return the first/last paper that has some marking or iding task."""
        # include a default of 1 in case there are no valid id or marking tasks
        min_max_from_marking = MarkingTask.objects.exclude(
            status=MarkingTask.OUT_OF_DATE
        ).aggregate(
            Min("paper__paper_number", default=1), Max("paper__paper_number", default=1)
        )

        min_max_from_iding = PaperIDTask.objects.exclude(
            status=MarkingTask.OUT_OF_DATE
        ).aggregate(
            Min("paper__paper_number", default=1), Max("paper__paper_number", default=1)
        )

        pn_min = min(
            min_max_from_marking["paper__paper_number__min"],
            min_max_from_iding["paper__paper_number__min"],
        )
        pn_max = max(
            min_max_from_marking["paper__paper_number__max"],
            min_max_from_iding["paper__paper_number__max"],
        )

        return (pn_min, pn_max)
