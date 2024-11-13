# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2024 Colin B. Macdonald
# Copyright (C) 2024 Bryan Tanady

import html

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest, HttpResponse, FileResponse, Http404
from django.shortcuts import render, reverse, redirect
from django_htmx.http import HttpResponseClientRefresh, HttpResponseClientRedirect
from rest_framework.exceptions import ValidationError

from plom import plom_valid_tag_text_pattern, plom_valid_tag_text_description
from plom.misc_utils import pprint_score
from Base.base_group_views import LeadMarkerOrManagerView
from Mark.services import (
    MarkingStatsService,
    MarkingTaskService,
    page_data,
    mark_task,
)
from Papers.services import SpecificationService
from Rubrics.services import RubricService
from Mark.models import MarkingTask, AnnotationImage
from ..services import ProgressOverviewService


class ProgressMarkingTaskFilterView(LeadMarkerOrManagerView):
    def get(self, request):
        mss = MarkingStatsService()

        context = super().build_context()

        paper = request.GET.get("paper", "*")
        question = request.GET.get("question", "*")
        if question == "*":
            question_label = "*"
        else:
            question_label = SpecificationService.get_question_label(
                question_index=question
            )
        version = request.GET.get("version", "*")
        username = request.GET.get("username", "*")
        score = request.GET.get("score", "*")
        the_tag = request.GET.get("the_tag", "*")
        status = request.GET.get("status", "*")
        if status != "*":
            status = int(status)
            status_label = MarkingTask.StatusChoices(status).label
        else:
            status_label = "*"

        (pl, pu) = ProgressOverviewService().get_first_last_used_paper_number()
        paper_list = [str(pn) for pn in range(pl, pu + 1)]

        question_index_label_pairs = [
            (str(q_idx), q_label)
            for q_idx, q_label in SpecificationService.get_question_index_label_pairs()
        ]
        version_list = [str(vn) for vn in SpecificationService.get_list_of_versions()]
        maxmark = SpecificationService.get_max_all_question_mark()
        if not maxmark:
            mark_list = []
        else:
            mark_list = [str(m) for m in range(maxmark + 1)]
        tag_list = sorted([X[1] for X in MarkingTaskService().get_all_tags()])
        # the item in status_list will be tuple (value, label), eg: (1, To Do)
        status_list = MarkingTask._meta.get_field("status").choices

        # get rid of "Out Of Date"
        if (4, "Out Of Date") in status_list:
            status_list.remove((4, "Out Of Date"))

        context.update(
            {
                "paper": paper,
                "question": question,
                "question_index_label_pairs": question_index_label_pairs,
                "question_label": html.escape(question_label),
                "version": version,
                "username": username,
                "score": score,
                "status": status,
                "the_tag": the_tag,
                "paper_list": paper_list,
                "version_list": version_list,
                "mark_list": mark_list,
                "username_list": mss.get_list_of_users_who_marked_anything(),
                "tag_list": tag_list,
                "status_list": status_list,
                "status_label": status_label,
            }
        )

        # if all filters set to * then ask user to set at least one
        # don't actually filter **all** tasks
        if all(
            X == "*"
            for X in [paper, question, version, username, score, the_tag, status]
        ):
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
            question_idx=optional_arg(question),
            version=optional_arg(version),
            username=optional_arg(username),
            score_min=optional_arg(score),
            score_max=optional_arg(score),
            the_tag=optional_arg(the_tag),
            status=optional_arg(status),
        )
        context.update({"task_info": task_info})

        return render(request, "Progress/Mark/task_filter.html", context)


class AnnotationImageWrapView(LeadMarkerOrManagerView):
    def get(
        self, request: HttpRequest, *, paper: int, question_idx: int
    ) -> HttpResponse:
        try:
            annot = MarkingTaskService().get_latest_annotation(paper, question_idx)
        except (ValueError, ObjectDoesNotExist) as e:
            raise Http404(e)
        context = {
            "paper": paper,
            "question_idx": question_idx,
            "annotation_image_id": annot.image.pk,
        }
        return render(
            request, "Progress/Mark/annotation_image_wrap_fragment.html", context
        )


class AnnotationImageView(LeadMarkerOrManagerView):
    def get(self, request: HttpRequest, *, annotation_image_id: int) -> FileResponse:
        annot_img = AnnotationImage.objects.get(pk=annotation_image_id)
        return FileResponse(annot_img.image)


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
    def get(self, request: HttpRequest) -> HttpResponse:
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
                "question_indices": SpecificationService.get_question_indices(),
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
        _, question_label_html = SpecificationService.get_question_label_str_and_html(
            task_obj.question_index
        )
        context = self.build_context()
        context.update(
            {
                "task_pk": task_pk,
                "paper_number": task_obj.paper.paper_number,
                "question_idx": task_obj.question_index,
                "question_label_html": question_label_html,
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
                    "score_str": pprint_score(task_obj.latest_annotation.score),
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

        mts = MarkingTaskService()
        # get all the tags as a dict of {pk: text}, and those for attn-markers
        all_tags = {X[0]: X[1] for X in mts.get_all_tags()}
        # list of all the markers as Users
        all_markers = User.objects.filter(groups__name="marker")
        # the corresponding attn user tag text
        attn_marker_tag_text = [f"@{X.username}" for X in all_markers]
        # tags for task at hand
        current_tags = {X[0]: X[1] for X in mts.get_tags_text_and_pk_for_task(task_pk)}
        # separate the current tags into 'normal' and 'attn' tags
        current_normal_tags = {
            X: Y for X, Y in current_tags.items() if Y not in attn_marker_tag_text
        }
        current_attn_user_tags = {
            X: Y for X, Y in current_tags.items() if Y in attn_marker_tag_text
        }
        # separate the normal tags from all the missing tags
        addable_normal_tags = {
            X: Y
            for X, Y in all_tags.items()
            if X not in current_tags and Y not in attn_marker_tag_text
        }
        # list of **users** that are not already present as a tag "@<user>"
        addable_attn_marker = [
            X
            for X in all_markers
            if f"@{X.username}" not in current_attn_user_tags.values()
        ]

        context.update(
            {
                "all_markers": all_markers,
                # the current tags, and then separated into normal and attn-marker
                "current_normal_tags": current_normal_tags,
                "current_attn_tags": current_attn_user_tags,
                # the tags / users we might add
                "addable_normal_tags": addable_normal_tags,
                "addable_attn_marker": addable_attn_marker,
                # get simple form validation pattern from here rather than hard coding into html
                "valid_tag_pattern": plom_valid_tag_text_pattern,
                "valid_tag_description": plom_valid_tag_text_description,
            }
        )

        return render(request, "Progress/Mark/task_details.html", context=context)


class MarkingTaskTagView(LeadMarkerOrManagerView):
    def patch(self, request, task_pk: int, tag_pk: int):
        MarkingTaskService().add_tag_to_task_via_pks(tag_pk, task_pk)
        return HttpResponseClientRefresh()

    def delete(self, request, task_pk: int, tag_pk: int):
        try:
            MarkingTaskService().remove_tag_from_task_via_pks(tag_pk, task_pk)
        except ValueError:
            # this will happen if (say) client removes a task out from
            # underneath us before we click here. In that case just
            # refresh the page.  See #2810
            pass
        return HttpResponseClientRefresh()

    def post(self, request, task_pk: int):
        # make sure have the correct field from the form
        if "newTagText" not in request.POST:
            return HttpResponseClientRefresh()
        try:
            tagtext = request.POST.get("newTagText").strip()
            # unnecessary? used to be done lower down so leaving here for now
            tagtext = tagtext.strip()
            MarkingTaskService().create_tag_and_attach_to_task(
                request.user, task_pk, tagtext
            )
        except ValidationError:
            # the form *should* catch validation errors.
            # we don't throw an explicit error here instead just refresh the page.
            return HttpResponseClientRefresh()

        return HttpResponseClientRefresh()


class ProgressNewestMarkingTaskDetailsView(LeadMarkerOrManagerView):
    def get(self, request, task_pk):
        # get the pn and qn from the given task
        # then find the latest task for that pn, qn.
        task_obj = MarkingTask.objects.get(pk=task_pk)
        pn = task_obj.paper.paper_number
        qi = task_obj.question_index
        new_task_pk = mark_task.get_latest_task(pn, qi).pk
        return redirect("progress_marking_task_details", task_pk=new_task_pk)


class MarkingTaskResetView(LeadMarkerOrManagerView):
    def put(self, request, task_pk: int):
        task_obj = MarkingTask.objects.get(pk=task_pk)
        pn = task_obj.paper.paper_number
        qi = task_obj.question_index
        MarkingTaskService().set_paper_marking_task_outdated(
            paper_number=pn, question_index=qi
        )
        # now grab the pk of the new task with that paper,question and redirect the user there.
        new_task_pk = mark_task.get_latest_task(pn, qi).pk
        return HttpResponseClientRedirect(
            reverse("progress_marking_task_details", args=[new_task_pk])
        )


class MarkingTaskReassignView(LeadMarkerOrManagerView):
    def post(self, request: HttpRequest, *, task_pk: int) -> HttpResponse:
        if "newUser" not in request.POST:
            return HttpResponseClientRefresh()
        new_username = request.POST.get("newUser")

        try:
            MarkingTaskService.reassign_task_to_user(
                task_pk, new_username=new_username, calling_user=request.user
            )
        except ValueError:
            # TODO - report the error
            # return HttpResponseClientRedirect("some_error_page.html")
            pass

        return HttpResponseClientRedirect(
            reverse("progress_marking_task_details", args=[task_pk])
        )
