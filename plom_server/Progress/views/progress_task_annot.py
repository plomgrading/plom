# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
from django.shortcuts import render
from django.http import FileResponse

from Base.base_group_views import LeadMarkerOrManagerView
from Mark.services import MarkingStatsService, MarkingTaskService, page_data
from Papers.services import SpecificationService
from Progress.services import ProgressOverviewService


class ProgressTaskAnnotationFilterView(LeadMarkerOrManagerView):
    def get(self, request):
        mss = MarkingStatsService()

        question = request.GET.get("question", "*")
        version = request.GET.get("version", "*")
        username = request.GET.get("username", "*")

        question_list = [
            str(q + 1) for q in range(SpecificationService.get_n_questions())
        ]
        version_list = [
            str(v + 1) for v in range(SpecificationService.get_n_versions())
        ]

        def optional_arg(val):
            if val == "*":
                return None
            else:
                return val

        task_info = mss.filter_marking_task_annotation_info(
            question=optional_arg(question),
            version=optional_arg(version),
            username=optional_arg(username),
        )

        context = super().build_context()
        context.update(
            {
                "question": question,
                "version": version,
                "username": username,
                "question_list": question_list,
                "version_list": version_list,
                "username_list": mss.get_list_of_users_who_marked_anything(),
                "task_info": task_info,
            }
        )

        return render(request, "Progress/Mark/task_annotations_filter.html", context)


class ProgressTaskAnnotationView(LeadMarkerOrManagerView):
    def get(self, request, question, version):
        context = super().build_context()
        context.update(
            {
                "question": question,
                "version": version,
                "task_info": MarkingStatsService().get_marking_task_annotation_info(
                    question, version
                ),
            }
        )

        return render(request, "Progress/Mark/task_annotations.html", context)


class AnnotationImageWrapView(LeadMarkerOrManagerView):
    def get(self, request, paper, question):
        annot = MarkingTaskService().get_latest_annotation(paper, question)
        context = {"paper": paper, "question": question, "annotation_pk": annot.pk}
        return render(
            request, "Progress/Mark/annotation_image_wrap_fragment.html", context
        )


class AnnotationImageView(LeadMarkerOrManagerView):
    def get(self, request, paper, question):
        annot = MarkingTaskService().get_latest_annotation(paper, question)
        return FileResponse(annot.image.image)


class OriginalImageWrapView(LeadMarkerOrManagerView):
    def get(self, request, paper, question):
        img_list = page_data.get_question_pages_list(paper, question)
        # update this to include an angle which is (-1)*orientation - for css transforms
        for X in img_list:
            X.update({"angle": -X["orientation"]})

        context = {"paper": paper, "question": question, "img_list": img_list}
        return render(
            request, "Progress/Mark/original_image_wrap_fragment.html", context
        )


class AllTaskOverviewView(LeadMarkerOrManagerView):
    def get(self, request):
        question_indices = [
            q + 1 for q in range(SpecificationService.get_n_questions())
        ]

        context = self.build_context()
        pos = ProgressOverviewService()  # acronym excellence
        id_task_overview, marking_task_overview = pos.get_task_overview()
        papers_with_a_task = list(id_task_overview.keys())
        n_papers = len(papers_with_a_task)

        task_counts = pos.get_completed_task_counts()
        # convert completed counts to percentages for progress bars
        if n_papers > 0:
            percent_complete = {
                "id": round(100 * task_counts["id"] / n_papers),
                "mk": {
                    q: round(100 * n / n_papers) for q, n in task_counts["mk"].items()
                },
            }
        else:
            percent_complete = {
                "id": 0,
                "mk": {q: 0 for q, n in task_counts["mk"].items()},
            }

        # Just experimenting with passing unpacked lists
        tmp = (
            (qi, label)
            for qi, label in SpecificationService.get_question_labels_map().items()
        )

        context.update(
            {
                "question_indices": question_indices,
                "question_labels": SpecificationService.get_question_labels_map(),
                "tmp_question_labels": tmp,
                "papers_with_a_task": papers_with_a_task,
                "id_task_overview": id_task_overview,
                "marking_task_overview": marking_task_overview,
                "n_papers": n_papers,
                "completed_task_counts": task_counts,
                "percent_complete": percent_complete,
            }
        )
        return render(request, "Progress/task_overview_home.html", context=context)
