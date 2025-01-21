# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2024-2025 Andrew Rechnitzer

from django.urls import path

from .views import (
    MarkingInformationView,
    MarkingInformationPaperView,
    ReassemblePapersView,
    StudentReportView,
    StartOneReassembly,
    StartAllReassembly,
    CancelQueuedReassembly,
    SolnHomeView,
    SolnSpecView,
    SolnSourcesView,
    TemplateSolnSpecView,
    BuildSolutionsView,
    StartAllBuildSoln,
    DownloadRangeOfReassembled,
    StartOneBuildSoln,
    CancelQueuedBuildSoln,
)


urlpatterns = [
    path("marking_info", MarkingInformationView.as_view(), name="marking_info"),
    path(
        "marking_info/<int:paper_num>/paper/",
        MarkingInformationPaperView.as_view(),
        name="paper_num",
    ),
    path(
        "marking_info/marks_download/",
        MarkingInformationView.marks_download,
        name="marks_download",
    ),
    path(
        "marking_info/ta_info_download/",
        MarkingInformationView.ta_info_download,
        name="ta_info_download",
    ),
    path("reassemble/", ReassemblePapersView.as_view(), name="reassemble_pdfs"),
    path(
        "reassemble/<int:paper_number>",
        StartOneReassembly.as_view(),
        name="reassemble_one_paper",
    ),
    path("reassemble/all", StartAllReassembly.as_view(), name="reassemble_all_pdfs"),
    path(
        "reassemble/range",
        DownloadRangeOfReassembled.as_view(),
        name="reassembled_range",
    ),
    path(
        "reassemble/queued",
        CancelQueuedReassembly.as_view(),
        name="reassemble_cancel_queued",
    ),
    path(
        "student_report/<int:paper_number>",
        StudentReportView.as_view(),
        name="get_student_report",
    ),
    path("solutions/home", SolnHomeView.as_view(), name="soln_home"),
    path("solutions/spec", SolnSpecView.as_view(), name="soln_spec"),
    path(
        "solutions/spec/template",
        TemplateSolnSpecView.as_view(),
        name="template_soln_spec",
    ),
    path(
        "solutions/sources/<int:version>",
        SolnSourcesView.as_view(),
        name="soln_source_upload",
    ),
    path("solutions/sources", SolnSourcesView.as_view(), name="soln_sources"),
    path("build_soln/", BuildSolutionsView.as_view(), name="build_soln"),
    path(
        "build_soln/<int:paper_number>",
        StartOneBuildSoln.as_view(),
        name="build_one_soln",
    ),
    path("build_soln/all", StartAllBuildSoln.as_view(), name="build_all_soln"),
    path(
        "build_soln/queued",
        CancelQueuedBuildSoln.as_view(),
        name="build_soln_cancel_queued",
    ),
]
