# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2023 Divy Patel
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2024 Aidan Murphy
# Copyright (C) 2024 Andreas Buttenschoen
# Copyright (C) 2025 Aden Chan
# Copyright (C) 2025 Aidan Murphy

import csv
import hashlib
from io import StringIO
from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Exists, OuterRef, Count
from django.db.models.query import QuerySet
from django.utils import timezone

from plom_server.Identify.models import PaperIDTask
from plom_server.Mark.services import MarkingTaskService
from plom_server.Mark.models import MarkingTask
from plom_server.Papers.models.paper_structure import Paper
from plom_server.Papers.services import SpecificationService, PaperInfoService
from plom_server.Scan.services import ManageScanService


class StudentMarkService:
    """Service for the Student Marks page."""

    # TODO: unit tests for many of these methods

    @staticmethod
    def _get_marked_unmarked_paper_querysets() -> tuple[QuerySet, QuerySet]:
        """Get a list of papers which are and aren't completely marked.

        This will only fetch 'used' papers, see
        :method:`ManageScanService._get_used_unused_paper_querysets()` for
        definitions of used and unused papers.
        A marked paper will have one complete marking
        task for each question.
        An unmarked paper is any used paper which isn't marked. This means
        'partially marked' papers are unmarked.

        Returns:
            A tuple of two querysets, the first contains all completely
            marked papers. The second contains the papers which aren't
            completely marked.

        """
        exam_question_indices: list = SpecificationService.get_question_indices()
        complete_tasks = MarkingTask.objects.filter(status=MarkingTask.COMPLETE)

        # a subquery to find papers which have at least one complete marking task
        # for each question. This returns a list of Paper.pk, not Paper.paper_number
        # I suspect the first filter isn't necessary, but better safe than sorry
        complete_tasks_counted = (
            complete_tasks.values("paper")
            .filter(question_index__in=exam_question_indices)
            .annotate(counts=Count("question_index", distinct=True))
            .filter(counts=len(exam_question_indices))
            .values_list("paper", flat=True)
        )

        marked_papers_queryset = Paper.objects.filter(pk__in=complete_tasks_counted)

        used_papers_queryset, _ = ManageScanService._get_used_unused_paper_querysets()

        # all used papers must be marked or unmarked
        unmarked_papers_queryset = used_papers_queryset.filter(
            ~Exists(
                marked_papers_queryset.filter(paper_number=OuterRef("paper_number"))
            )
        )

        # TODO: a previous inefficient (loops-based) function also checked that
        # all tasks are complete or out of date for a complete paper - perhaps
        # this function should do the same?

        # make sure one completed task for each question and that all tasks are complete or out of date.
        # return (n_completed_tasks == n_questions) and (
        #     n_completed_tasks + n_out_of_date_tasks == n_all_tasks
        # )

        return marked_papers_queryset, unmarked_papers_queryset

    @staticmethod
    def is_paper_marked(paper: Paper) -> bool:
        """Return True if all of the marking tasks are completed.

        Args:
            paper: a reference to a Paper instance

        Returns:
            bool: True when all questions in the given paper are marked.
        """
        # TODO: Is this the most efficient way to compute marked vs unmarked?
        paper_tasks = MarkingTask.objects.filter(paper=paper)
        n_completed_tasks = paper_tasks.filter(status=MarkingTask.COMPLETE).count()
        n_out_of_date_tasks = paper_tasks.filter(status=MarkingTask.OUT_OF_DATE).count()
        n_all_tasks = paper_tasks.count()
        n_questions = SpecificationService.get_n_questions()
        # make sure one completed task for each question and that all tasks are complete or out of date.
        return (n_completed_tasks == n_questions) and (
            n_completed_tasks + n_out_of_date_tasks == n_all_tasks
        )

    @classmethod
    def are_all_papers_marked(cls) -> bool:
        """Return True if all used papers are marked.

        See :method:`ManageScanService._get_used_unused_paper_querysets()` for
        definitions of used and unused papers.
        """
        _, unmarked_papers = cls._get_marked_unmarked_paper_querysets()
        return len(unmarked_papers) == 0

    @staticmethod
    def _get_n_questions_marked(paper: Paper) -> int:
        """Return the number of questions that are marked in a paper.

        Args:
            paper: a reference to a Paper instance
        """
        # each question has at most one complete task, and is marked if it has exactly one.
        return MarkingTask.objects.filter(
            paper=paper, status=MarkingTask.COMPLETE
        ).count()

    @staticmethod
    def _get_last_updated_timestamp(paper: Paper) -> timezone.datetime:
        """Return the latest update timestamp from the PaperIDTask or MarkingTask.

        Args:
            paper: a reference to a Paper instance

        Returns:
            datetime: the time of the latest update to any task in the paper.
            WARNING: If paper is not id'd and not marked then returns the current
            time.
        """
        # paper has at most one completed ID task
        try:
            last_id_time = PaperIDTask.objects.get(
                paper=paper, status=PaperIDTask.COMPLETE
            ).last_update
        except PaperIDTask.DoesNotExist:
            last_id_time = None

        # paper has multiple complete marking tasks, get the latest one
        if len(MarkingTask.objects.filter(status=MarkingTask.COMPLETE)):
            last_annotation_time = (
                MarkingTask.objects.filter(status=MarkingTask.COMPLETE)
                .order_by("-last_update")
                .first()
                .last_update
            )
        else:
            last_annotation_time = None

        if last_id_time and last_annotation_time:
            return max(last_id_time, last_annotation_time)
        elif last_id_time:
            return last_id_time
        elif last_annotation_time:
            return last_annotation_time
        else:
            return timezone.now()  # if no updates return the current time.

    @staticmethod
    def get_paper_id_or_none(paper: Paper) -> tuple[str | None, str] | None:
        """Return a tuple of (student ID, student name) if the paper has been identified. Otherwise, return None.

        Args:
            paper: a reference to a Paper instance

        Returns:
            A tuple (str, str) or None.  Note that a paper can be ID'd
            with sid `None`, in which case we get back ``(None, str)``
            where the second string is an explanation.
        """
        try:
            action = (
                PaperIDTask.objects.filter(paper=paper, status=PaperIDTask.COMPLETE)
                .get()
                .latest_action
            )
        except PaperIDTask.DoesNotExist:
            return None
        return action.student_id, action.student_name

    @staticmethod
    def get_question_version_and_mark(
        paper: Paper, question_idx: int
    ) -> tuple[int, float | None]:
        """For a particular paper and question index, return the question version and score.

        Args:
            paper: a reference to a Paper instance.
            question_idx: question index, one based.

        Returns:
            Tuple of the question version and score, where score might
            be `None`.

        Raises:
            ObjectDoesNotExist: no such marking task, either b/c the paper
                does not exist or the question does not exist for that paper.
        """
        version = PaperInfoService().get_version_from_paper_question(
            paper.paper_number, question_idx
        )
        try:
            mark = (
                MarkingTask.objects.filter(
                    paper=paper,
                    question_index=question_idx,
                    status=MarkingTask.COMPLETE,
                )
                .get()
                .latest_annotation.score
            )
        except ObjectDoesNotExist:
            mark = None
        return version, mark

    @classmethod
    def get_paper_status(
        cls, paper: Paper
    ) -> tuple[bool, bool, int, timezone.datetime]:
        """Return a list of [scanned?, identified?, n questions marked, time of last update] for a given paper.

        Args:
            paper: reference to a Paper object

        Returns:
            tuple of [bool, bool, int, datetime]
        """
        paper_id_info = cls.get_paper_id_or_none(paper)
        is_id = paper_id_info is not None
        is_scanned = ManageScanService.is_paper_completely_scanned(paper.paper_number)
        n_marked = cls._get_n_questions_marked(paper)
        last_modified = cls._get_last_updated_timestamp(paper)

        return (is_scanned, is_id, n_marked, last_modified)

    def get_identified_papers(self) -> dict[int, tuple[str | None, str]]:
        """Return a dictionary with all of the identified papers and their names and IDs, with potentially INEFFICIENT DB operations.

        TODO: only called by an unused legacy API code, see "API/views/reports.py"
        TODO: so this can be removed soon.

        Returns:
            dictionary: keys are paper numbers, values are a list of [str, str]
        """
        spreadsheet_data = {}
        papers = Paper.objects.all()
        for paper in papers:
            paper_id_info = self.get_paper_id_or_none(paper)
            if paper_id_info:
                student_id, student_name = paper_id_info
                spreadsheet_data[paper.paper_number] = (student_id, student_name)
        return spreadsheet_data

    def get_marks_from_paper(self, paper_num: int) -> dict:
        """Get the marks for a paper.

        Args:
            paper_num: The paper number.

        Returns:
            Dict keyed by paper number whose values are a dictionary holding
            the mark information for each question in the paper.
        """
        try:
            paper_obj = Paper.objects.get(paper_number=paper_num)
        except Paper.DoesNotExist:
            return {}
        marking_tasks = (
            paper_obj.markingtask_set.all()
            .select_related("latest_annotation")
            .exclude(status=MarkingTask.OUT_OF_DATE)
        )
        questions: dict[int, str | dict] = {}
        for marking_task in marking_tasks.order_by("question_index"):
            current_annotation = marking_task.latest_annotation
            if current_annotation:
                questions[marking_task.question_index] = {
                    "question": marking_task.question_index,
                    "version": marking_task.question_version,
                    "out_of": current_annotation.annotation_data["maxMark"],
                    "student_mark": current_annotation.score,
                }
            else:
                # String value so that it questions.get(i) doesn't return None
                questions[marking_task.question_index] = "Not marked"

        return {paper_num: questions}

    def get_all_marks(self) -> dict:
        """Get the marks for all papers, with potentially INEFFICIENT DB operations.

        Returns:
            Dict containing the mark information for each question in each paper. Keyed by
            paper number whose values are a dictionary holding the mark information for each
            question in the paper.
        """
        paper_nums = MarkingTask.objects.values_list(
            "paper__paper_number", flat=True
        ).distinct()
        marks = {}
        for paper_num in paper_nums:
            marks.update(self.get_marks_from_paper(paper_num))
        # Sort by paper number
        return {k: marks[k] for k in sorted(marks)}

    @staticmethod
    def get_n_of_question_marked(question: int, *, version: int = 0) -> int:
        """Get the count of how many papers have marked a specific question.

        Args:
            question: The question index.

        Keyword Args:
            version: The version of the question.

        Returns:
            The count of how many papers a mark for this question.

        Raises:
            None expected
        """
        return (
            MarkingTaskService()
            .get_tasks_from_question_with_annotation(question, version)
            .count()
        )

    @staticmethod
    def _get_csv_header(
        *,
        version_info: bool = True,
        timing_info: bool = False,
        warning_info: bool = False,
        include_name: bool = True,
    ) -> list[str]:
        """Get the header for the csv file.

        Keyword Args:
            version_info: Whether to include the version info.
            timing_info: Whether to include the timing info.
            warning_info: Whether to include the warning info.
            include_name: Whether to include the ``StudentName``.

        Returns:
            List holding the header for the csv file. Contains student info, marks,
            version info, timestamps and warnings.

        Raises:
            None expected
        """
        keys = ["StudentID", "StudentName", "PaperNumber", "Total"]
        q_labels = SpecificationService.get_question_labels()
        # if the above changed then make sure that the dict-keys also changed
        for q in q_labels:
            # TODO: we could use spaces if the label already has spaces?
            # TODO: although this might have some knock-on effects
            # pad = " " if " " in q else "_"
            pad = "_"
            keys.append(f"{q}{pad}mark")
        if version_info:
            for q in q_labels:
                pad = "_"
                keys.append(f"{q}{pad}version")
        if timing_info:
            keys.extend(["last_update"])
        if warning_info:
            keys.append("warnings")
        if not include_name:
            keys.remove("StudentName")

        return keys

    @classmethod
    def build_marks_csv_as_string(
        cls,
        version_info: bool,
        timing_info: bool,
        warning_info: bool,
        *,
        privacy_mode: bool = False,
        privacy_salt: str = "",
    ) -> str:
        """Generates a csv in string format with the marks of all students.

        Args:
            version_info: Whether to include the version info.
            timing_info: Whether to include the timing info.
            warning_info: Whether to include the warning info.

        Keyword Args:
            privacy_mode: Whether to hash the student ID.
            privacy_salt: The salt to hash the student ID with.

        Returns:
            The csv in string format.
        """
        student_marks = cls.get_all_marking_info()

        keys = cls._get_csv_header(
            version_info=version_info,
            timing_info=timing_info,
            warning_info=warning_info,
            include_name=(not privacy_mode),
        )

        # Hash the StudentID if privacy mode is on
        if privacy_mode:
            for mark in student_marks:
                student_id = mark.get("StudentID", "")
                if student_id:
                    salted_id = student_id + privacy_salt
                    hashed_id = hashlib.sha256(salted_id.encode()).hexdigest()
                    mark["StudentID"] = hashed_id

        csv_io = StringIO()
        w = csv.DictWriter(csv_io, keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(student_marks)

        csv_io.seek(0)
        return csv_io.getvalue()

    @staticmethod
    def get_all_marking_info() -> list[dict[str, Any]]:
        """Build a list of dictionaries being the rows of the marking spreadsheet.

        Returns:
            A list of dicts, with keys appropriate for the columns of Plom's
            `marks.csv` spreadsheet.

        Raises:
            RuntimeError: if there are two complete ID-tasks for the same paper,
            or if there are two complete MarkingTasks for the same paper/question.
        """
        # we build a big dictionary with all the required info
        # indexed on paper_number.
        all_papers: dict[int, dict[str, Any]] = {}
        # Each entry will be a "row" of the resulting csv
        # so we build a template-csv-row to copy into place.
        qlabels = SpecificationService.get_question_labels()
        # now build a dict of all the data index on paper_number
        csv_row_template = {
            "PaperNumber": None,
            "identified": False,
            "marked": False,
            "StudentID": "",
            "StudentName": "",
            "Total": None,
            "last_update": None,
            "warnings": "",
        }
        csv_row_template.update({f"{q}_mark": None for q in qlabels})
        csv_row_template.update({f"{q}_version": None for q in qlabels})

        # get all completed ID-tasks
        completed_id_task_info = (
            PaperIDTask.objects.filter(status=PaperIDTask.COMPLETE)
            .prefetch_related("paper", "latest_action")
            .values_list(
                "paper__paper_number",
                "latest_action__student_id",
                "latest_action__student_name",
                "last_update",
            )
        )
        # get the id-info for each paper into our dict
        for pn, sid, sname, lu in completed_id_task_info:
            if pn not in all_papers:
                all_papers[pn] = csv_row_template.copy()
                all_papers[pn]["PaperNumber"] = pn
            else:
                # We have a problem - we have two valid complete ID-tasks for
                # the same paper - this should not happen!
                raise RuntimeError(
                    "There should at most one complete ID task for each paper."
                )
            all_papers[pn]["identified"] = True
            all_papers[pn]["StudentID"] = sid
            all_papers[pn]["StudentName"] = sname
            all_papers[pn]["last_update"] = lu

        # a little utility function to get latter-time
        def latter_time(A, B):
            # get the latter time, treating None as infinite-past
            if A is None:
                return B
            if B is None:
                return A
            return max(A, B)

        # get all completed marking tasks
        completed_marking_task_info = (
            MarkingTask.objects.filter(status=MarkingTask.COMPLETE)
            .prefetch_related("paper", "latest_annotation")
            .values_list(
                "paper__paper_number",
                "question_index",
                "question_version",
                "latest_annotation__score",
                "last_update",
            )
        )
        # now get the marking info for each paper into the dict
        # note that some of these papers might not have been ID'd
        # so we might have to put the csv-row-template into place.
        for pn, qi, qv, sc, lu in completed_marking_task_info:
            if pn not in all_papers:
                all_papers[pn] = csv_row_template.copy()
                all_papers[pn]["PaperNumber"] = pn
            # qi is a 1-based index
            q = qlabels[qi - 1]
            # make sure that we have not already put this paper/question into
            # the dictionary as that would indicate that we have more than
            # one complete marking tasks for the same question/version
            if all_papers[pn][f"{q}_mark"] is not None:
                raise RuntimeError(
                    "There should be only one complete marking task for each paper/question."
                )
            all_papers[pn][f"{q}_mark"] = sc
            all_papers[pn][f"{q}_version"] = qv
            all_papers[pn]["last_update"] = latter_time(
                all_papers[pn]["last_update"], lu
            )
        # now it is also possible that we have some papers that have
        # been scanned, but not been ID'd or marked - these also need
        # to go into our marking spreadsheet
        # so get paper-number of any unfinished ID / Marking tasks
        unfinished_id_tasks = (
            PaperIDTask.objects.filter(status__in=[PaperIDTask.TO_DO, PaperIDTask.OUT])
            .prefetch_related("paper")
            .values_list("paper__paper_number", flat=True)
        )
        unfinished_marking_tasks = (
            MarkingTask.objects.filter(status__in=[MarkingTask.TO_DO, MarkingTask.OUT])
            .prefetch_related("paper")
            .values_list("paper__paper_number", flat=True)
        )
        # so we iterate over all of these and if we haven't seen
        # these paper-numbers, we add them to our paper-dictionary
        unfinished_tasks = list(
            set(list(unfinished_id_tasks) + list(unfinished_marking_tasks))
        )
        for pn in unfinished_tasks:
            if pn not in all_papers:
                all_papers[pn] = csv_row_template.copy()
                all_papers[pn]["PaperNumber"] = pn
            # note we expect to have seen most of these paper-numbers
            # since it should be pretty rare to be building this
            # spreadsheet when we still have scanned papers which have
            # been neither marked nor id'd.

        # Now that all the data is in, we can do a final scan through
        # the dictionary to put in total-mark and any warning for
        # not-id'd and not-marked.
        for pn, dat in all_papers.items():
            wrn = []
            # check if ID'd
            if not dat["identified"]:
                wrn.append("Not identified")
            # check all questions marked
            scores = [dat[f"{q}_mark"] for q in qlabels]
            if None in scores:
                wrn.append("Not marked")
            else:
                all_papers[pn]["Total"] = sum(scores)
                all_papers[pn]["marked"] = True
            if wrn:
                all_papers[pn]["warnings"] = ",".join(wrn)
            if dat["last_update"]:
                all_papers[pn]["last_update"] = dat["last_update"].strftime("%c")
        # we return a list of dicts - these will be the rows
        # of our marks.csv spreadsheet.
        return [all_papers[k] for k in sorted(all_papers.keys())]

    @staticmethod
    def get_paper_id_and_marks(paper_number: int) -> dict[Any, Any]:
        """Returns information about the given paper as a dict.

        Dict contains keys/values:
           * 'paper_number'
           * 'sid' = student ID if paper ID'd else None
           * 'name' = student name if paper ID'd else None.
           * 'total' = total score for assessment if all questions marked else None
           * 'question_max_marks' = dict of the max marks for each question keyed by question index
           * then for each question the key/value pair question_index: score for that question (else None)
        """
        paper = Paper.objects.get(paper_number=paper_number)
        question_max_marks = SpecificationService.get_questions_max_marks()
        paper_info = {
            "paper_number": paper_number,
            "sid": None,
            "name": None,
            "total": None,
            "question_max_marks": question_max_marks,
        }
        question_indices = question_max_marks.keys()
        paper_info.update({qi: None for qi in question_indices})
        # get ID info if there
        try:
            action = (
                PaperIDTask.objects.filter(paper=paper, status=PaperIDTask.COMPLETE)
                .get()
                .latest_action
            )

            paper_info.update({"sid": action.student_id, "name": action.student_name})
        except PaperIDTask.DoesNotExist:
            pass
        # now get marks if there
        scores = []
        for task in MarkingTask.objects.filter(
            paper=paper, status=MarkingTask.COMPLETE
        ).prefetch_related("latest_annotation"):
            paper_info[task.question_index] = task.latest_annotation.score
            scores.append(task.latest_annotation.score)
        # compute the total if all marked
        if len(scores) == len(question_indices):
            paper_info["total"] = sum(scores)

        return paper_info
