# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

import os

from django.shortcuts import render

from Base.base_group_views import ManagerRequiredView
from StudentMarks.services import StudentMarksService


class StudentMarkView(ManagerRequiredView):
    """View for the Student Marks page."""

    sms = StudentMarksService()

    def get(self, request):
        print("STARTING")
        context = self.build_context()
        server = os.environ.get("PLOM_SERVER")
        if not server:
            print("PLOM_SERVER not set")
            server = "0.0.0.0"
        password = os.environ.get("PLOM_MANAGER_PASSWORD")
        if not password:
            print("PLOM_MANAGER_PASSWORD not set")
            password = "demomanager1"
        
        print(self.sms.get_student_marks_as_json(msgr = (server, password)))

        return render(request, "student_marks", context=context)
