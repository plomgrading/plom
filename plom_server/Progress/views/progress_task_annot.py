# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
from django.shortcuts import render
from django.http import FileResponse

from Base.base_group_views import LeadMarkerOrManagerView
from Mark.services import MarkingStatsService, MarkingTaskService, page_data
from Papers.services import SpecificationService
from Progress.services import ProgressOverviewService

from Mark.models import MarkingTask


class ProgressMarkingTaskFilterView(LeadMarkerOrManagerView):
    def get(self, request):
        mss = MarkingStatsService()

        context = super().build_context()

        paper = request.GET.get("paper", "*")
        question = request.GET.get("question", "*")
        version = request.GET.get("version", "*")
        username = request.GET.get("username", "*")
        score = request.GET.get("score", "*")

        (pl, pu) = ProgressOverviewService().get_first_last_used_paper_number()
        paper_list = [str(pn) for pn in range(pl, pu + 1)]

        question_list = [
            str(q + 1) for q in range(SpecificationService.get_n_questions())
        ]
        version_list = [
            str(v + 1) for v in range(SpecificationService.get_n_versions())
        ]
        mark_list = [
            str(m) for m in range(SpecificationService.get_max_all_question_mark() + 1)
        ]

        context.update(
            {
                "paper": paper,
                "question": question,
                "version": version,
                "username": username,
                "score": score,
                "paper_list": paper_list,
                "question_list": question_list,
                "version_list": version_list,
                "mark_list": mark_list,
                "username_list": mss.get_list_of_users_who_marked_anything(),
            }
        )

        # if all filters set to * then ask user to set at least one
        # don't actually filter **all** tasks
        if all(X == "*" for X in [paper, question, version, username, score]):
            context.update({"warning": True})
            return render(request, "Progress/Mark/task_filter.html", context)

        # at least one filter is set, so continue
        def optional_arg(val):
            if val == "*":
                return None
            else:
                return val

        # We pass ranges for scores and papers to this filter
        # TODO - get ranges from the filter form - needs some nice multi-range-selector widget or something.
        task_info = mss.filter_marking_task_annotation_info(
            paper_min=optional_arg(paper),
            paper_max=optional_arg(paper),
            question=optional_arg(question),
            version=optional_arg(version),
            username=optional_arg(username),
            score_min=optional_arg(score),
            score_max=optional_arg(score),
        )
        context.update({"task_info": task_info})

        return render(request, "Progress/Mark/task_filter.html", context)


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
            X.update({"aspect": X["img_height"] / X["img_width"]})

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

        # get the counts for each id and marking task by their status
        # we pass the number of papers so that we also get counts of **missing** tasks
        id_task_status_counts = pos.get_id_task_status_counts(n_papers=n_papers)
        marking_task_status_counts = pos.get_mark_task_status_counts(n_papers=n_papers)

        context.update(
            {
                "question_indices": question_indices,
                "question_labels": SpecificationService.get_question_index_label_pairs(),
                "papers_with_a_task": papers_with_a_task,
                "id_task_overview": id_task_overview,
                "marking_task_overview": marking_task_overview,
                "n_papers": n_papers,
                "id_task_status_counts": id_task_status_counts,
                "marking_task_status_counts": marking_task_status_counts,
            }
        )
        return render(request, "Progress/all_task_overview.html", context=context)


class ProgressMarkingTaskDetailsView(LeadMarkerOrManagerView):
    def get(self, request, task_pk):
        # todo = move most of this DB work to a service.
        task_obj = MarkingTask.objects.get(pk=task_pk)
        context = self.build_context()
        context.update(
            {
                "paper_number": task_obj.paper.paper_number,
                "question": task_obj.question_number,
                "version": task_obj.question_version,
                "status": task_obj.get_status_display(),
            }
        )
        if task_obj.status == MarkingTask.COMPLETE:
            context.update(
                {
                    "annotation_pk": task_obj.latest_annotation.pk,
                    "score": task_obj.latest_annotation.score,
                    "username": task_obj.assigned_user.username,
                    "edition": task_obj.latest_annotation.edition,
                }
            )
        elif task_obj.status == MarkingTask.OUT:
            context.update({"username": task_obj.assigned_user.username})
        else:
            pass

        return render(request, "Progress/Mark/task_details.html", context=context)
