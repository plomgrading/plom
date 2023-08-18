# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023 Andrew Rechnitzer
from django.shortcuts import render

from Base.base_group_views import ManagerRequiredView

from Papers.services import SpecificationService
from Mark.services import MarkingStatsService


class ProgressMarkHome(ManagerRequiredView):
    def get(self, request):
        context = super().build_context()

        version_numbers = [
            v + 1
            for v in range(
                SpecificationService.get_n_versions(),
            )
        ]
        question_numbers = [
            q + 1 for q in range(SpecificationService.get_n_questions())
        ]

        context.update({"versions": version_numbers, "questions": question_numbers})

        return render(request, "Progress/Mark/mark_home.html", context)


class ProgressMarkStatsView(ManagerRequiredView):
    def get(self, request, question, version):
        context = super().build_context()
        mss = MarkingStatsService()
        context.update(
            {
                "question": question,
                "version": version,
                "stats": mss.get_basic_marking_stats(
                    question=question, version=version
                ),
            }
        )

        return render(request, "Progress/Mark/mark_stats_card.html", context)
