# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan

from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from Papers.services import SpecificationService
from QuestionTags.services import QuestionTagService
from .models import TmpAbstractQuestion, PedagogyTag


class QTagsLandingView(ListView):
    model = TmpAbstractQuestion
    template_name = "Questiontags/qtags_landing.html"
    context_object_name = "question_tags"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["question_label_triple"] = (
            SpecificationService.get_question_html_label_triples()
        )
        context["tags"] = PedagogyTag.objects.all()
        context["question_tags"] = TmpAbstractQuestion.objects.prefetch_related(
            "tags"
        ).all()
        return context


class AddQuestionTagView(CreateView):
    template_name = "Questiontags/qtags_landing.html"

    def post(self, request, *args, **kwargs):
        question_index = request.POST.get("questionIndex")
        tag_names = request.POST.getlist("tagName")
        QuestionTagService.add_question_tag(question_index, tag_names, request.user)
        return redirect(reverse("qtags_landing"))


class CreateTagView(CreateView):
    template_name = "Questiontags/qtags_landing.html"

    def post(self, request, *args, **kwargs):
        tag_name = request.POST.get("tagName")
        text = request.POST.get("text")
        QuestionTagService.create_tag(tag_name, text, request.user)
        return redirect(reverse("qtags_landing"))


class DeleteTagView(DeleteView):
    model = PedagogyTag

    def post(self, request, *args, **kwargs):
        tag_id = request.POST.get("tag_id")
        QuestionTagService.delete_tag(tag_id)
        return redirect(reverse("qtags_landing"))


class EditTagView(UpdateView):
    template_name = "Questiontags/qtags_landing.html"

    def post(self, request, *args, **kwargs):
        tag_id = request.POST.get("tag_id")
        tag_name = request.POST.get("tagName")
        text = request.POST.get("text")
        QuestionTagService.edit_tag(tag_id, tag_name, text)
        return redirect(reverse("qtags_landing"))
