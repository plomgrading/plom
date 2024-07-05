# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan

from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from Papers.services import SpecificationService
from QuestionTags.services import QuestionTagService
from .models import TmpAbstractQuestion, PedagogyTag, QuestionTagLink
from .forms import AddTagForm, RemoveTagForm


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
            "questiontaglink_set__tag"
        ).all()
        context["add_tag_form"] = AddTagForm()
        context["remove_tag_form"] = RemoveTagForm()
        return context

    def post(self, request, *args, **kwargs):
        if "add_tag" in request.POST:
            form = AddTagForm(request.POST)
            if form.is_valid():
                question_index = form.cleaned_data["question_index"]
                tag_id = form.cleaned_data["tag_id"].id
                tag = get_object_or_404(PedagogyTag, id=tag_id)
                QuestionTagService.add_question_tag(
                    question_index, [tag.tag_name], request.user
                )
        elif "remove_tag" in request.POST:
            form = RemoveTagForm(request.POST)
            if form.is_valid():
                question_tag_id = form.cleaned_data["question_tag_id"]
                try:
                    question_tag = get_object_or_404(
                        QuestionTagLink, id=question_tag_id
                    )
                    question_tag.delete()
                except Exception as e:
                    print("Error deleting QuestionTag:", e)  # Debug print
        return redirect(reverse("qtags_landing"))


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
