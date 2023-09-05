# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
from django.shortcuts import render
from django.http import FileResponse

from Base.base_group_views import ManagerRequiredView
from Mark.services import MarkingStatsService, MarkingTaskService, PageDataService


class ProgressTaskAnnotationView(ManagerRequiredView):
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


class AnnotationImageWrapView(ManagerRequiredView):
    def get(self, request, paper, question):
        context = {"paper": paper, "question": question}
        return render(
            request, "Progress/Mark/annotation_image_wrap_fragment.html", context
        )


class AnnotationImageView(ManagerRequiredView):
    def get(self, request, paper, question):
        annot = MarkingTaskService().get_latest_annotation(paper, question)
        return FileResponse(annot.image.image)


class OriginalImageWrapView(ManagerRequiredView):
    def get(self, request, paper, question):
        img_list = PageDataService().get_question_pages_list(paper, question)
        # update this to include an angle which is (-1)*orientation - for css transforms
        for X in img_list:
            X.update({"angle": -X["orientation"]})

        context = {"paper": paper, "question": question, "img_list": img_list}
        return render(
            request, "Progress/Mark/original_image_wrap_fragment.html", context
        )
