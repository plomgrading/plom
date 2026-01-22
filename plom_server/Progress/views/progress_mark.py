# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023-2025 Andrew Rechnitzer
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2025 Bryan Tanady
# Copyright (C) 2025 Deep Shah

from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from plom_server.Base.base_group_views import (
    MarkerOrManagerView,
    LeadMarkerOrManagerView,
)

from collections import Counter

from plom_server.Authentication.services import AuthService
from plom_server.Papers.services import SpecificationService
from plom_server.Mark.services import MarkingStatsService
from ..services import ProgressOverviewService


class ProgressMarkHome(MarkerOrManagerView):
    """The Marking Progress page showing progress and stats for all question/version pairs in a grid of small cards."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """Render the page with all the marking stats cards for all questions and versions."""
        context = self.build_context()

        # TODO: could extract this from the "task_counts", save a little bit of DB
        missing_task_count = ProgressOverviewService.n_missing_marking_tasks()

        task_counts = ProgressOverviewService.get_mark_task_status_counts(
            breakdown_by_version=True
        )

        question_labels_html = SpecificationService.get_question_html_label_triples()
        versions = SpecificationService.get_list_of_versions()
        all_max_marks = SpecificationService.get_questions_max_marks()
        data_for_histograms = {}
        for qidx, __, __ in question_labels_html:
            _data: dict[int, list] = {}
            data_for_histograms[qidx] = _data
            for ver in versions:
                max_mark = all_max_marks[qidx]
                _data[ver] = _should_be_in_a_service(qidx, ver, max_mark)

        who_marked = MarkingStatsService.get_lists_of_users_who_marked()
        context.update(
            {
                "versions": versions,
                "question_labels_html": question_labels_html,
                "missing_task_count": missing_task_count,
                "task_counts": task_counts,
                "data_for_histograms": data_for_histograms,
                "who_marked_how_many": who_marked,
            }
        )
        return render(request, "Progress/Mark/mark_overview.html", context)


class ProgressMarkStartMarking(MarkerOrManagerView):
    """Display a page telling users how to get the client and get started."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """Respond to Get method requests to the Mark Papers page."""
        context = self.build_context()
        server_link = AuthService.get_base_link(
            default_host=get_current_site(request).domain
        )
        context.update({"server_link": server_link})
        return render(request, "Progress/Mark/mark_papers.html", context)


# TODO: move this to MarkingStatsService?
def _should_be_in_a_service(
    question_idx: int, version: int, max_mark: int
) -> list[dict[str, int | float]]:
    scores = MarkingStatsService.get_scores_for_question_version(question_idx, version)
    score_counts = Counter(scores)

    histogram_data = []

    max_count = max(score_counts.values()) if score_counts else 1

    svg_height = 100
    svg_bar_max_height = 80

    bar_width_percentage = 100 / (max_mark + 1)

    for mark in range(max_mark + 1):
        count = score_counts.get(mark, 0)
        bar_height = (count / max_count) * svg_bar_max_height if count > 0 else 0

        histogram_data.append(
            {
                "score": mark,
                "count": count,
                "height": bar_height,
                "x": mark * bar_width_percentage + 1,
                "y": svg_height - bar_height - 20,
                "width": bar_width_percentage - 1,
                "text_x": (mark * bar_width_percentage) + (bar_width_percentage / 2),
            }
        )
    return histogram_data


class ProgressMarkStatsView(MarkerOrManagerView):
    """Currently unused but can be used to render just one of the marking stats cards.

    Currently the cards all all rendered from a single view-context, namely
    :class:`ProgressMarkHome`.  Previously this view was used to render each
    card in separate HTMX on-loads.  It could be resurrected for per-card
    refresh if desired, or just deleted, especially if it starts to bitrot.
    """

    def get(
        self, request: HttpRequest, *, question_idx: int, version: int
    ) -> HttpResponse:
        """Render a single marking stats card for one question version pair."""
        context = self.build_context()

        status_counts = ProgressOverviewService.get_mark_task_status_counts_restricted(
            question_idx, version
        )

        all_max_marks = SpecificationService.get_questions_max_marks()
        max_mark = all_max_marks.get(question_idx, 0)
        histogram_data = _should_be_in_a_service(question_idx, version, max_mark)
        qlabel, qlabel_html = SpecificationService.get_question_label_str_and_html(
            question_idx
        )
        context.update(
            {
                "question_idx": question_idx,
                "question_label_html": qlabel_html,
                "version": version,
                "task_status_counts": status_counts,
                "histogram_data": histogram_data,
            }
        )
        return render(request, "Progress/Mark/mark_stats_card.html", context)


class ProgressMarkDetailsView(LeadMarkerOrManagerView):
    def get(
        self, request: HttpRequest, *, question_idx: int, version: int
    ) -> HttpResponse:
        context = self.build_context()
        mss = MarkingStatsService()
        stats = mss.get_basic_marking_stats(question_idx, version=version)
        histogram = mss.get_mark_histogram(question_idx, version=version)
        hist_keys, hist_values = zip(*histogram.items())
        # user_list = mss.get_list_of_users_who_marked(question, version=version)

        user_hists_and_stats = mss.get_mark_histogram_and_stats_by_users(
            question_idx, version=version
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
        question_label, question_label_html = (
            SpecificationService.get_question_label_str_and_html(question_idx)
        )

        status_counts = ProgressOverviewService.get_mark_task_status_counts_restricted(
            question_idx, version
        )

        context.update(
            {
                "question_idx": question_idx,
                "question_label": question_label,
                "question_label_html": question_label_html,
                "version": version,
                "stats": stats,
                "hist_keys": list(hist_keys),
                "hist_values": list(hist_values),
                "user_hists": user_hists_and_stats,
                "remaining_tasks": remaining_tasks,
                "task_status_counts": status_counts,
            }
        )

        return render(request, "Progress/Mark/mark_details.html", context)


class ProgressMarkVersionCompareView(LeadMarkerOrManagerView):
    def get(self, request: HttpRequest, *, question_idx: int) -> HttpResponse:
        version = 1
        context = self.build_context()
        mss = MarkingStatsService()
        stats = mss.get_basic_marking_stats(question_idx, version=None)
        histogram = mss.get_mark_histogram(question_idx, version=None)
        hist_keys, hist_values = zip(*histogram.items())
        version_hists_and_stats = mss.get_mark_histogram_and_stats_by_versions(
            question_idx
        )
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

        status_counts = ProgressOverviewService.get_mark_task_status_counts_restricted(
            question_idx
        )

        question_label, question_label_html = (
            SpecificationService.get_question_label_str_and_html(question_idx)
        )
        context.update(
            {
                "question_idx": question_idx,
                "question_label": question_label,
                "question_label_html": question_label_html,
                "version": version,
                "stats": stats,
                "hist_keys": list(hist_keys),
                "hist_values": list(hist_values),
                "version_hists": version_hists_and_stats,
                "task_status_counts": status_counts,
            }
        )

        return render(request, "Progress/Mark/mark_compare_versions.html", context)
