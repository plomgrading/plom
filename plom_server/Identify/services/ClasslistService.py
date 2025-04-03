# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2024 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov

from __future__ import annotations

from plom_server.Preparation.services import StagingStudentService


def get_students() -> list[dict[str, str | int]]:
    """Get a list of students, empty if there are none."""
    return StagingStudentService().get_students()


def get_students_in_api_format() -> list[dict[str, str | int]]:
    """Get a list of students, empty if there are none, in a format for our API."""
    students = get_students()
    for s in students:
        s["id"] = s.pop("student_id")
        s["name"] = s.pop("student_name")
    return students


def get_classdict():
    students = get_students()
    for s in students:
        s["id"] = s.pop("student_id")
        s["studentName"] = s.pop("student_name")
        if s["paper_number"] is None:
            s["paper_number"] = -1
    return students


def get_classlist_sids_for_ID_matching() -> list[str]:
    """Returns a list containing all student IDs on the classlist."""
    students = []
    classlist = get_students()
    for entry in classlist:
        # MyPy thinks the input is "str | int": not sure why but cast to str just in case
        students.append(str(entry.pop("student_id")))
    return students
