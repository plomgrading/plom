# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

from django.contrib.auth.models import User
from django.http import FileResponse
from django.shortcuts import render
from django_htmx.http import HttpResponseClientRefresh

from Base.base_group_views import LeadMarkerOrManagerView
from Mark.services import (
    MarkingStatsService,
    MarkingTaskService,
    page_data,
    mark_task_tags,
)
from Papers.services import SpecificationService
from Progress.services import ProgressOverviewService
from Rubrics.services import RubricService

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
                "task_pk": task_obj.pk,
                "paper_number": task_obj.paper.paper_number,
                "question": task_obj.question_number,
                "version": task_obj.question_version,
                "status": task_obj.get_status_display(),
                "lead_markers": User.objects.filter(groups__name="lead_marker"),
            }
        )
        if task_obj.status == MarkingTask.COMPLETE:
            context.update(
                {
                    "annotation_pk": task_obj.latest_annotation.pk,
                    "score": task_obj.latest_annotation.score,
                    "username": task_obj.assigned_user.username,
                    "edition": task_obj.latest_annotation.edition,
                    "last_update": task_obj.latest_annotation.time_of_last_update,
                    "marking_time": task_obj.latest_annotation.marking_time,
                    "rubrics": RubricService().get_rubrics_from_annotation(
                        task_obj.latest_annotation
                    ),
                }
            )
        elif task_obj.status == MarkingTask.OUT:
            context.update({"username": task_obj.assigned_user.username})
        else:
            pass

        # getting the current tags and addable tags is complicated because
        # adr wants to separate them into 2 categories - normal tags and attn-user tags
        # these are index by the tag_pk and the user_pk respectively
        # hence there is a little bit of work to check if a given user is already "attn"
        # consequently make a list of all the markers and all the attn-tags they would get
        all_tags = mark_task_tags.get_all_marking_task_tags()
        all_markers = User.objects.filter(groups__name="marker")
        all_attn_marker_tag_text = [f"@{X.username}" for X in all_markers]
        # all the current tags for this task, and those that are attn_marker and otherwise
        task_tags = mark_task_tags.get_tags_for_task(task_obj)
        # list of tags
        tags_attn_marker = [X for X in task_tags if X.text in all_attn_marker_tag_text]
        # list of tags
        tags_not_attn_marker = [
            X for X in task_tags if X.text not in all_attn_marker_tag_text
        ]
        # addable tags not_attn_marker
        task_tags_text = [X.text for X in task_tags]  # text of all current tags
        # list of tags that are not of the form "@<user>"
        addable_tags_not_attn = [
            X
            for X in all_tags
            if X not in task_tags
            and X.text not in task_tags_text
            and X.text not in all_attn_marker_tag_text
        ]
        # list of **users** that are not already present as a tag "@<user>"
        addable_attn_marker = [
            X for X in all_markers if f"@{X.username}" not in task_tags_text
        ]

        context.update(
            {
                # the current tags, and then separated into normal and attn-marker
                "tags": task_tags,
                "tags_attn_marker": tags_attn_marker,
                "tags_not_attn_marker": tags_not_attn_marker,
                # the tags / users we might add
                "addable_attn_markers": addable_attn_marker,
                "addable_tags_not_attn": addable_tags_not_attn,
            }
        )

        return render(request, "Progress/Mark/task_details.html", context=context)


class MarkingTaskTagView(LeadMarkerOrManagerView):
    def patch(self, request, task_pk: int, tag_pk: int):
        mark_task_tags.add_tag_to_task(tag_pk, task_pk)
        return HttpResponseClientRefresh()

    def delete(self, request, task_pk: int, tag_pk: int):
        mark_task_tags.remove_tag_from_task(tag_pk, task_pk)
        return HttpResponseClientRefresh()

    def post(self, request, task_pk: int):
        # make sure have the correct field from the form
        if "newTagText" not in request.POST:
            return HttpResponseClientRefresh()
        # sanitize the text, check if such a tag already exists
        # (create it otherwise) then add to the task
        mts = MarkingTaskService()
        tag_text = mts.sanitize_tag_text(request.POST.get("newTagText"))

        tag_obj = mts.get_tag_from_text(tag_text)
        if tag_obj is None:  # no such tag exists, so create one
            tag_obj = mts.create_tag(request.user, tag_text)

        mark_task_tags.add_tag_to_task(tag_obj.pk, task_pk)
        return HttpResponseClientRefresh()
