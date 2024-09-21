# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023-2024 Colin B. Macdonald

from django.contrib.sites.shortcuts import get_current_site
from django.shortcuts import render

from Base.base_group_views import (
    MarkerLeadMarkerOrManagerView,
    LeadMarkerOrManagerView,
)

from Authentication.services import AuthenticationServices
from Papers.services import SpecificationService
from Mark.services import MarkingStatsService
from ..services import ProgressOverviewService


class ProgressMarkHome(MarkerLeadMarkerOrManagerView):
    def get(self, request):
        context = super().build_context()
        context.update(
            {
                "versions": SpecificationService.get_list_of_versions(),
                "questions": SpecificationService.get_question_indices(),
            }
        )
        return render(request, "Progress/Mark/mark_home.html", context)


class ProgressMarkStartMarking(MarkerLeadMarkerOrManagerView):
    def get(self, request):
        context = super().build_context()
        server_link = AuthenticationServices.get_base_link(
            default_host=get_current_site(request).domain
        )
        context.update({"server_link": server_link})
        return render(request, "Progress/Mark/mark_papers.html", context)


class ProgressMarkStatsView(MarkerLeadMarkerOrManagerView):
    def get(self, request, question, version):
        context = super().build_context()
        mss = MarkingStatsService()
        context.update(
            {
                "question": question,
                "version": version,
                "stats": mss.get_basic_marking_stats(question, version=version),
                "status_counts": ProgressOverviewService().get_mark_task_status_counts_by_qv(
                    question, version
                ),
            }
        )

        return render(request, "Progress/Mark/mark_stats_card.html", context)


class ProgressMarkDetailsView(LeadMarkerOrManagerView):
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
        remaining_tasks = stats["all_task_count"] - stats["number_of_completed_tasks"]

        context.update(
            {
                "question": question,
                "version": version,
                "stats": stats,
                "hist_keys": list(hist_keys),
                "hist_values": list(hist_values),
                "user_hists": user_hists_and_stats,
                "remaining_tasks": remaining_tasks,
                "status_counts": ProgressOverviewService().get_mark_task_status_counts_by_qv(
                    question, version
                ),
            }
        )

        return render(request, "Progress/Mark/mark_details.html", context)


class ProgressMarkVersionCompareView(LeadMarkerOrManagerView):
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

        context.update(
            {
                "question": question,
                "version": version,
                "stats": stats,
                "hist_keys": list(hist_keys),
                "hist_values": list(hist_values),
                "version_hists": version_hists_and_stats,
                "status_counts": ProgressOverviewService().get_mark_task_status_counts_by_qv(
                    question, version=None
                ),
            }
        )

        return render(request, "Progress/Mark/mark_compare_versions.html", context)
