# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan

from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from Papers.services import SpecificationService
from QuestionTags.services import QuestionTagService
from .models import TmpAbstractQuestion, PedagogyTag
from .forms import AddTagForm, RemoveTagForm
from django.http import JsonResponse, HttpResponse
from plom.tagging import plom_valid_tag_text_description
import json
import csv
from django.views import View
from Papers.models.paper_structure import QuestionPage

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
        meta = request.POST.get("meta")
        error_message = QuestionTagService.create_tag(
            tag_name, text, request.user, meta
        )
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
        meta = request.POST.get("meta")
        error_message = QuestionTagService.edit_tag(tag_id, tag_name, text, meta)
        if error_message:
            return JsonResponse({"error": error_message})
        return JsonResponse({"success": True})


class DownloadQuestionTagsView(View):
    """View to download question tags as CSV or JSON file."""

    def get(self, request, *args, **kwargs):
        """Handle GET requests to download question tags as CSV or JSON."""
        
        format = request.GET.get('format', 'json')
        
        if format == 'csv':
            return self.download_csv()
        else:
            return self.download_json()

    def download_csv(self):
        """Generate and return a CSV response."""

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="question_tags.csv"'

        writer = csv.writer(response)
        writer.writerow(['Paper Number', 'Question Index', 'Question Label', 'Tags', 'Page Numbers'])

        questions = TmpAbstractQuestion.objects.all()
        
        for question in questions:
            question_label = SpecificationService.get_question_label(question.question_index)
            tags = ', '.join([qt.tag.tag_name for qt in question.questiontaglink_set.all()])
            question_pages = QuestionPage.objects.filter(question_index=question.question_index)
            for qp in question_pages:
                paper_number = qp.paper.paper_number
                pages = ', '.join([str(page.page_number) for page in QuestionPage.objects.filter(paper=qp.paper, question_index=question.question_index)])
                writer.writerow([paper_number, question.question_index, question_label, tags, pages])

        return response

    def download_json(self):
        """Generate and return a JSON response."""

        data = []
        questions = TmpAbstractQuestion.objects.all()

        for question in questions:
            question_label = SpecificationService.get_question_label(question.question_index)
            tags = [qt.tag.tag_name for qt in question.questiontaglink_set.all()]
            question_pages = QuestionPage.objects.filter(question_index=question.question_index)
            for qp in question_pages:
                question_data = {
                    'paper_number': qp.paper.paper_number,
                    'question_index': question.question_index,
                    'question_label': question_label,
                    'tags': tags,
                    'page_numbers': [page.page_number for page in QuestionPage.objects.filter(paper=qp.paper, question_index=question.question_index)]
                }
                data.append(question_data)

        response = HttpResponse(json.dumps(data, indent=4), content_type="application/json")
        response['Content-Disposition'] = 'attachment; filename="question_tags.json"'
        return response