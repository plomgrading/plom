# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Andrew Rechnitzer
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2024-2025 Colin B. Macdonald

import csv
import logging
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.core.files import File
from django.db import transaction, IntegrityError

from plom.create import PlomClasslistValidator
from .preparation_dependency_service import assert_can_modify_classlist
from ..models import StagingStudent
from ..services import PrenameSettingService


log = logging.getLogger("ClasslistService")


class StagingStudentService:
    @transaction.atomic
    def how_many_students(self) -> int:
        return StagingStudent.objects.all().count()

    @transaction.atomic
    def are_there_students(self) -> bool:
        return StagingStudent.objects.exists()

    @transaction.atomic()
    def get_students(self) -> list[dict[str, str | int]]:
        """Get a list of students, empty if there are none."""
        return list(
            StagingStudent.objects.all().values(
                "student_id", "student_name", "paper_number"
            )
        )

    @transaction.atomic()
    def get_first_last_prenamed_paper(self) -> tuple[int, int] | tuple[None, None]:
        """Return the lowest and highest paper_number allocated to a prenamed paper.

        This appropriately returns (None, None) if there are no prenamed papers.
        """
        query = StagingStudent.objects.filter(paper_number__isnull=False).order_by(
            "paper_number"
        )
        if query.exists():
            return (query.first().paper_number, query.last().paper_number)
        else:
            return (None, None)

    @transaction.atomic()
    def get_prenamed_papers(self) -> dict[int, tuple[str, str]]:
        """Return dict of prenamed papers {paper_number: (student_id, student_name)}."""
        return {
            s_obj.paper_number: (s_obj.student_id, s_obj.student_name)
            for s_obj in StagingStudent.objects.filter(paper_number__isnull=False)
        }

    def get_students_as_csv_string(self, *, prename: bool = False) -> str:
        """Write the data from the classlist table into a string in CSV format.

        The header and name-columns are quoted.
        """
        txt = '"id","name","paper_number"\n'
        for row in self.get_students():
            if prename and row["paper_number"]:
                txt += f"{row['student_id']},\"{row['student_name']}\",{row['paper_number']}\n"
            else:
                # don't print the -1 for non-prename.
                txt += f"{row['student_id']},\"{row['student_name']}\",\n"
        return txt

    @transaction.atomic()
    def _add_student(
        self,
        student_id: str,
        student_name: str,
        *,
        paper_number: int | str | None = None,
    ) -> None:
        """Add a single student to the staging classlist.

        Note - does not check dependencies.

        Args:
            student_id: a string.
            student_name: a string.

        Keyword Args:
            paper_number: either None or a non-negative integer.  Sentinel values
                of ``-1``, ``None`` and ``""`` are accepted as None.

        Returns:
            None.

        Raises:
            IntegrityError: if student-id is not unique, or other database
                checks failed, for example invalid paper number.
            ValueError: invalid paper_number such as inappropriate sentinel value
        """
        s_obj = StagingStudent(student_id=student_id, student_name=student_name)
        # note that zero is not a sentinel so "if paper_number" is NOT appropriate
        if PlomClasslistValidator.is_paper_number_sentinel(paper_number):
            paper_number = None
        if paper_number is not None:
            try:
                # 1.1 would become 1; validator before us should've complained
                paper_number = int(paper_number)
            except ValueError as e:
                raise ValueError(
                    f"paper_number cannot be converted to int: str{e}"
                ) from None
        s_obj.paper_number = paper_number
        s_obj.save()

    @transaction.atomic()
    def remove_all_students(self):
        """Remove all the students from the staging classlist.

        Raises:
            PlomDependencyConflict: if dependencies not met.
        """
        assert_can_modify_classlist()
        StagingStudent.objects.all().delete()

    @transaction.atomic()
    def validate_and_use_classlist_csv(
        self, in_memory_csv_file: File, ignore_warnings: bool = False
    ) -> tuple[bool, list[dict[str, Any]]]:
        """Validate and store the classlist from the in-memory file, if possible.

        Args:
            in_memory_csv_file: some kind of Django file thing.

        Keyword Args:
            ignore_warnings: try to proceed with opening the file even if
                the validator expressed warnings.

        Returns:
            2-tuple, the first entry is a bool indicating success.  In case of
            success the 2nd entry is an empty list (or might contain
            ignored warnings).  In case of errors the second list contains dicts
            which elaborate on errors or warnings.

        Raises:
            PlomDependencyConflict: If dependencies not met.
        """
        assert_can_modify_classlist()

        # now save the in-memory file to a tempfile and validate
        # Note: we must be careful to unlink this file ourselves
        tmp_csv = Path(NamedTemporaryFile(delete=False).name)

        with open(tmp_csv, "wb") as fh:
            for chunk in in_memory_csv_file:
                fh.write(chunk)

        vlad = PlomClasslistValidator()
        success, werr = vlad.validate_csv(tmp_csv)
        # success = False means warnings+errors - listed in werr
        # success = True means no errors, but could be warnings in werr.

        if (not success) or (werr and not ignore_warnings):
            # errors, or non-ignorable warnings.
            tmp_csv.unlink()
            return (success, werr)

        # either no warnings, or warnings but ignore them - so read the csv
        with open(tmp_csv) as fh:
            csv_reader = csv.DictReader(fh, skipinitialspace=True)
            try:
                # We accept "id", "ID", "Id", but code is messy #3822 #1140
                headers = csv_reader.fieldnames
                assert headers, "Expectedly empty csv header"
                (id_key,) = [x for x in headers if x.casefold() == "id"]
                (name_key,) = [x for x in headers if x.casefold() == "name"]
                # paper_number is a bit harder b/c it might not be present
                papernum_key = "paper_number"
                _tmp = [x for x in headers if x.casefold() == papernum_key]
                if len(_tmp) == 1:
                    papernum_key = _tmp[0]
                for row in csv_reader:
                    self._add_student(
                        row[id_key],
                        row[name_key],
                        paper_number=row.get(papernum_key, None),
                    )
            except (IntegrityError, ValueError, KeyError, AssertionError) as e:
                # in theory, we "asked permission" using vlad the validator
                # so the input must be perfect and this can never fail---haha!
                success = False
                errmsg = "Unexpected error, "
                errmsg += f"likely a bug in Plom's classlist validator: {str(e)}"
                # see :method:`PlomClasslistValidator.validate_csv` for this format
                werr.append(
                    {"warn_or_err": "error", "werr_line": None, "werr_text": errmsg}
                )

        tmp_csv.unlink()
        return (success, werr)

    @transaction.atomic()
    def get_minimum_number_to_produce(self) -> int:
        """Gets a suggestion for the minimum number of papers a server should produce.

        The return value depends on the current server state.
        """
        # how_many_students doesn't behave well if an empty classlist is uploaded
        if not self.are_there_students():
            num_students = 0
        else:
            num_students = self.how_many_students()
        _, last_prename = self.get_first_last_prenamed_paper()
        prenaming_enabled = PrenameSettingService().get_prenaming_setting()

        return self._minimum_number_to_produce(
            num_students, last_prename, prenaming_enabled
        )

    def _minimum_number_to_produce(
        self,
        num_students: int,
        highest_prenamed_paper: int | None,
        prenaming_enabled: bool,
    ) -> int:
        """Suggests a minimum number of papers to produce in various situations.

        Args:
            num_students: the maximum number of students expected to
                attempt the assessment.
            highest_prenamed_paper: the highest paper number allocated
                to a prenamed paper. Can be None, indicating no prenamed
                papers.
            prenaming_enabled: whether prenaming is currently enabled on
                the server.
        """
        extra_20 = num_students + 20
        # simple fiddle to get ceiling of 1.1*N using python floor-div //
        extra_10percent = -((-num_students * 11) // 10)
        prenamed_extra_10 = (highest_prenamed_paper or 0) + 10
        if prenaming_enabled:
            return max(extra_20, extra_10percent, prenamed_extra_10)
        return max(extra_20, extra_10percent)

    def get_prename_for_paper(self, paper_number) -> str | None:
        """Return student ID for prenamed paper or None if paper is not prenamed."""
        try:
            student_obj = StagingStudent.objects.get(paper_number=paper_number)
            return student_obj.student_id
        except ObjectDoesNotExist:
            return None
