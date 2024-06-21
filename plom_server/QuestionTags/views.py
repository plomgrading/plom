# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan

from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from QuestionTags.services import QuestionTagService
from .models import QuestionTag, Tag


class QTagsLandingView(ListView):
    model = QuestionTag
    template_name = "Questiontags/qtags_landing.html"
    context_object_name = "question_tags"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["question_labels"] = QuestionTagService.get_question_labels()
        context["question_count"] = len(context["question_labels"])
        context["tags"] = Tag.objects.all()
        return context


class AddQuestionTagView(CreateView):
    template_name = "Questiontags/qtags_landing.html"

    def post(self, request, *args, **kwargs):
        question_index = request.POST.get("questionIndex")
        tag_names = request.POST.getlist("tagName")
        description = request.POST.get("description")
        QuestionTagService.add_question_tag(question_index, tag_names, description)
        return redirect(reverse("qtags_landing"))


class CreateTagView(CreateView):
    template_name = "Questiontags/qtags_landing.html"

    def post(self, request, *args, **kwargs):
        tag_name = request.POST.get("tagName")
        description = request.POST.get("tagDescription")
        QuestionTagService.create_tag(tag_name, description)
        return redirect(reverse("qtags_landing"))


class DeleteTagView(DeleteView):
    model = Tag

    def post(self, request, *args, **kwargs):
        tag_id = request.POST.get("tag_id")
        QuestionTagService.delete_tag(tag_id)
        return redirect(reverse("qtags_landing"))


class EditTagView(UpdateView):
    template_name = "Questiontags/qtags_landing.html"

    def post(self, request, *args, **kwargs):
        tag_id = request.POST.get("tag_id")
        tag_name = request.POST.get("tagName")
        tag_description = request.POST.get("tagDescription")
        QuestionTagService.edit_tag(tag_id, tag_name, tag_description)
        return redirect(reverse("qtags_landing"))
