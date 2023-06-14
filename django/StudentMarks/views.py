# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

import json

from django.shortcuts import render
from django.http import JsonResponse

from Base.base_group_views import ManagerRequiredView
from StudentMarks.services import StudentMarksService


class StudentMarkView(ManagerRequiredView):
    """View for the Student Marks page."""

    sms = StudentMarksService()

    def get(self, request):
        context = self.build_context()

        student_marks = self.sms.get_all_marks()

        return JsonResponse(student_marks)


class StudentMarkPaperView(ManagerRequiredView):
    """View for the Student Marks page as a JSON blob."""

    template = "StudentMarks/paper_marks.html"
    sms = StudentMarksService()

    def get(self, request, paper_num):
        marks_dict = self.sms.get_marks_from_paper(paper_num)
        return JsonResponse(marks_dict)