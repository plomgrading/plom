# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald

from django.shortcuts import render

from Base.base_group_views import (
    ManagerRequiredView,
    MarkerOrHigherView,
    LeadMarkerOrHigherView,
)

from Papers.services import SpecificationService
from Mark.services import MarkingStatsService


class ProgressMarkHome(MarkerOrHigherView):
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


class ProgressMarkStatsView(MarkerOrHigherView):
    def get(self, request, question, version):
        context = super().build_context()
        mss = MarkingStatsService()
        context.update(
            {
                "question": question,
                "version": version,
                "stats": mss.get_basic_marking_stats(question, version=version),
            }
        )

        return render(request, "Progress/Mark/mark_stats_card.html", context)


class ProgressMarkDetailsView(LeadMarkerOrHigherView):
    def get(self, request, question, version):
        context = super().build_context()
        mss = MarkingStatsService()
        stats = mss.get_basic_marking_stats(question, version=version)
        histogram = mss.get_mark_histogram(question, version=version)
        hist_keys, hist_values = zip(*histogram.items())
        # user_list = mss.get_list_of_users_who_marked(question, version=version)
        user_hists_and_stats = mss.get_mark_histogram_and_stats_by_users(
            question, version=version
        )
        # for the charts we need a list of histogram values for each user, hence the following
        # we also want to show it against scaled histogram of all users
        for upk in user_hists_and_stats:
            user_hists_and_stats[upk]["hist_values"] = [
                v for k, v in user_hists_and_stats[upk]["histogram"].items()
            ]
            scale = (
                user_hists_and_stats[upk]["number"] / stats["number_of_completed_tasks"]
            )
            user_hists_and_stats[upk]["hist_everyone_values"] = [
                v * scale for v in hist_values
            ]
        # to show incomplete pie-chart need this value
        pie_angle = 360 * stats["number_of_completed_tasks"] / stats["all_task_count"]

        context.update(
            {
                "question": question,
                "version": version,
                "stats": stats,
                "hist_keys": list(hist_keys),
                "hist_values": list(hist_values),
                "user_hists": user_hists_and_stats,
                "pie_angle": pie_angle,
            }
        )

        return render(request, "Progress/Mark/mark_details.html", context)


class ProgressMarkVersionCompareView(LeadMarkerOrHigherView):
    def get(self, request, question):
        version = 1
        context = super().build_context()
        mss = MarkingStatsService()
        stats = mss.get_basic_marking_stats(question, version=None)
        histogram = mss.get_mark_histogram(question, version=None)
        hist_keys, hist_values = zip(*histogram.items())
        version_hists_and_stats = mss.get_mark_histogram_and_stats_by_versions(question)
        # for the charts we need a list of histogram values for each version, hence the following
        # we also want to show it against scaled histogram of all versions
        for ver in version_hists_and_stats:
            version_hists_and_stats[ver]["hist_values"] = [
                val for k, val in version_hists_and_stats[ver]["histogram"].items()
            ]
            scale = (
                version_hists_and_stats[ver]["number"]
                / stats["number_of_completed_tasks"]
            )
            version_hists_and_stats[ver]["hist_all_version_values"] = [
                v * scale for v in hist_values
            ]
        # to show incomplete pie-chart need this value
        pie_angle = 360 * stats["number_of_completed_tasks"] / stats["all_task_count"]

        context.update(
            {
                "question": question,
                "version": version,
                "stats": stats,
                "hist_keys": list(hist_keys),
                "hist_values": list(hist_values),
                "version_hists": version_hists_and_stats,
                "pie_angle": pie_angle,
            }
        )

        return render(request, "Progress/Mark/mark_compare_versions.html", context)
