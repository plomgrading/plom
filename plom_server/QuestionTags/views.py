# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan

from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from Papers.services import SpecificationService
from QuestionTags.services import QuestionTagService
from .models import TmpAbstractQuestion, PedagogyTag
from .forms import AddTagForm, RemoveTagForm
from django.http import JsonResponse
from plom.tagging import plom_valid_tag_text_description


class QTagsLandingView(ListView):
    """View for displaying and managing question tags."""

    model = TmpAbstractQuestion
    template_name = "Questiontags/qtags_landing.html"
    context_object_name = "question_tags"

    def get_context_data(self, **kwargs):
        """Get the context data for the view.

        Returns:
            The context data for the view.
        """
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
        context["tagging_rulez"] = plom_valid_tag_text_description
        return context

    def post(self, request, *args, **kwargs):
        """Handle POST requests to add or remove tags.

        Returns:
            An HTTP response object.
        """
        if "add_tag" in request.POST:
            form = AddTagForm(request.POST)
            if form.is_valid():
                question_index = form.cleaned_data["question_index"]
                tag_id = form.cleaned_data["tag_id"].id
                tag = get_object_or_404(PedagogyTag, id=tag_id)
                QuestionTagService.add_question_tag_link(
                    question_index, [tag.tag_name], request.user
                )
        elif "remove_tag" in request.POST:
            form = RemoveTagForm(request.POST)
            if form.is_valid():
                question_tag_id = form.cleaned_data["question_tag_id"]
                QuestionTagService.delete_question_tag_link(question_tag_id)
        return redirect(reverse("qtags_landing"))


class AddQuestionTagLinkView(CreateView):
    """View for adding a question tag link."""

    template_name = "Questiontags/qtags_landing.html"

    def post(self, request, *args, **kwargs):
        """Handle POST requests to add a question tag link.

        Returns:
            A JSON response object.
        """
        question_index = request.POST.get("questionIndex")
        tag_names = request.POST.getlist("tagName")
        error_message = QuestionTagService.add_question_tag_link(
            question_index, tag_names, request.user
        )
        if error_message:
            return JsonResponse({"error": error_message})
        return JsonResponse({"success": True})


class CreateTagView(CreateView):
    """View for creating a new tag."""

    template_name = "Questiontags/qtags_landing.html"

    def post(self, request, *args, **kwargs):
        """Handle POST requests to create a new tag.

        Returns:
            A JSON response object.
        """
        tag_name = request.POST.get("tagName")
        text = request.POST.get("text")
        error_message = QuestionTagService.create_tag(tag_name, text, request.user)
        if error_message:
            return JsonResponse({"error": error_message})
        return JsonResponse({"success": True})


class DeleteTagView(DeleteView):
    """View for deleting a tag."""

    model = PedagogyTag

    def post(self, request, *args, **kwargs):
        """Handle POST requests to delete a tag.

        Returns:
            An HTTP response object.
        """
        tag_id = request.POST.get("tag_id")
        QuestionTagService.delete_tag(tag_id)
        return redirect(reverse("qtags_landing"))


class EditTagView(UpdateView):
    """View for editing a tag."""

    template_name = "Questiontags/qtags_landing.html"

    def post(self, request, *args, **kwargs):
        """Handle POST requests to edit a tag.

        Returns:
            A JSON response object.
        """
        tag_id = request.POST.get("tag_id")
        tag_name = request.POST.get("tagName")
        text = request.POST.get("text")
        error_message = QuestionTagService.edit_tag(tag_id, tag_name, text)
        if error_message:
            return JsonResponse({"error": error_message})
        return JsonResponse({"success": True})
