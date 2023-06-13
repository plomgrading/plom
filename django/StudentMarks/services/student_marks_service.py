# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

import json

from plom.finish import with_finish_messenger


class StudentMarksService:
    """Service for the Student Marks page."""

    @with_finish_messenger
    def get_student_marks_as_json(self, msgr):
        """Get the student marks as JSON."""
        gradesDict = msgr.RgetSpreadsheet()
        return json.dumps(gradesDict)