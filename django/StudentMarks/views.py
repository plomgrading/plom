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

        # TODO: Get the student marks from the database.
        # temporary random data
        dict = {
            "sports": 10,
            "countries": ["Pakistan", "USA", "India", "China", "Germany", "France", "Spain"],
            "types_of_wood": ["Teak", "Deodar", "Sal", "Sheesham"],
            "colors": ["Red", "Green", "Blue", "Yellow"],
        }
        print("good")
        json_data = json.dumps(dict)
        parsed_data = json.loads(json_data)
        print(parsed_data["sports"])
        context["content"] = json_data


        return render(request, "StudentMarks/student_marks.html", context=context)


class StudentMarkPaperView(ManagerRequiredView):
    """View for the Student Marks page as a JSON blob."""

    template = "StudentMarks/paper_marks.html"
    sms = StudentMarksService()

    def get(self, request, paper_num):
        marks_dict = self.sms.get_marks_from_paper(paper_num)
        return JsonResponse(marks_dict)