# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan
# Copyright (C) 2024 Andrew Rechnitzer
# Copyright (C) 2024 Colin B. Macdonald
# Copyright (C) 2024 Aden Chan

import csv
import io

from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.db.utils import IntegrityError

from Base.base_group_views import ManagerRequiredView
from Papers.services import SpecificationService
from .services import QuestionTagService
from .models import TmpAbstractQuestion, PedagogyTag
from .forms import AddTagForm, RemoveTagForm
from plom.tagging import plom_valid_tag_text_description


class QTagsLandingView(ListView, ManagerRequiredView):
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
                try:
                    QuestionTagService.add_question_tag_link(
                        question_index, [tag.tag_name], request.user
                    )
                except (IntegrityError, ValueError) as err:
                    return JsonResponse({"error": f"{err}"})
        elif "remove_tag" in request.POST:
            form = RemoveTagForm(request.POST)
            if form.is_valid():
                question_tag_id = form.cleaned_data["question_tag_id"]
                try:
                    QuestionTagService.delete_question_tag_link(question_tag_id)
                except ValueError as err:
                    return JsonResponse({"error": f"{err}"})
        return redirect(reverse("qtags_landing"))


class AddQuestionTagLinkView(CreateView, ManagerRequiredView):
    """View for adding a question tag link."""

    template_name = "Questiontags/qtags_landing.html"

    def post(self, request, *args, **kwargs):
        """Handle POST requests to add a question tag link.

        Returns:
            A JSON response object.
        """
        question_index = request.POST.get("questionIndex")
        tag_names = request.POST.getlist("tagName")
        try:
            QuestionTagService.add_question_tag_link(
                question_index, tag_names, request.user
            )
        except (IntegrityError, ValueError) as err:
            return JsonResponse({"error": f"{err}"})
        return JsonResponse({"success": True})


class CreateTagView(CreateView, ManagerRequiredView):
    """View for creating a new tag."""

    template_name = "Questiontags/qtags_landing.html"

    def post(self, request, *args, **kwargs):
        """Handle POST requests to create a new tag.

        Returns:
            A JSON response object.
        """
        # make sure we strip leading/trailing whitespace
        tag_name = request.POST.get("tagName").strip()
        text = request.POST.get("text").strip()
        confidential_info = request.POST.get("confidential_info").strip()
        try:
            QuestionTagService.create_tag(
                tag_name, text, user=request.user, confidential_info=confidential_info
            )
        except (IntegrityError, ValueError) as err:
            return JsonResponse({"error": f"{err}"})
        return JsonResponse({"success": True})


class DeleteTagView(DeleteView, ManagerRequiredView):
    """View for deleting a tag."""

    model = PedagogyTag

    def post(self, request, *args, **kwargs):
        """Handle POST requests to delete a tag.

        Returns:
            An HTTP response object.
        """
        tag_id = request.POST.get("tag_id")
        try:
            QuestionTagService.delete_tag(tag_id)
        except ValueError as err:
            return JsonResponse({"error": f"{err}"})
        return redirect(reverse("qtags_landing"))


class EditTagView(UpdateView, ManagerRequiredView):
    """View for editing a tag."""

    template_name = "Questiontags/qtags_landing.html"

    def post(self, request, *args, **kwargs):
        """Handle POST requests to edit a tag.

        Returns:
            A JSON response object.
        """
        print(request.POST)
        tag_id = request.POST.get("tag_id")
        # strip out leading/trailing whitespace from name,text,confidential_info
        tag_name = request.POST.get("tagName").strip()
        text = request.POST.get("text").strip()
        confidential_info = request.POST.get("confidential_info").strip()
        try:
            help_threshold = float(request.POST.get("help_threshold"))
        except ValueError:
            return JsonResponse({"error": "Help threshold must be a number"})
        help_resources = request.POST.get("help_resources").strip()
        try:
            QuestionTagService.edit_tag(
                tag_id,
                tag_name,
                text,
                confidential_info=confidential_info,
                help_threshold=help_threshold,
                help_text=help_resources,
            )
        except (ValueError, IntegrityError) as err:
            return JsonResponse({"error": f"{err}"})
        return JsonResponse({"success": True})


class DownloadQuestionTagsView(ManagerRequiredView):
    """View to download question tags as CSV or JSON file."""

    def get(self, request, *args, **kwargs):
        """Handle GET requests to download question tags as CSV or JSON."""
        format = request.GET.get("format", "json")
        csv_type = request.GET.get("csv_type", "questions")

        if format == "csv":
            if csv_type == "tags":
                return self.download_tags_csv()
            else:
                return self.download_questions_csv()
        else:
            return self.download_json()

    def download_questions_csv(self):
        """Generate and return a CSV response for questions."""
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="question_tags.csv"'

        writer = csv.writer(response)
        writer.writerow(["Question Index", "Question Label", "Tags"])

        questions = TmpAbstractQuestion.objects.all()
        for question in questions:
            question_label = SpecificationService.get_question_label(
                question.question_index
            )
            tags = ", ".join(
                [qt.tag.tag_name for qt in question.questiontaglink_set.all()]
            )
            writer.writerow([question.question_index, question_label, tags])

        return response

    def download_tags_csv(self):
        """Generate and return a CSV response for tags."""
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="tags.csv"'

        writer = csv.writer(response)
        writer.writerow(
            [
                "Name",
                "Description",
                "Confidential_Info",
                "Help_Threshold",
                "Help_Resources",
            ]
        )

        tags = PedagogyTag.objects.all()
        for tag in tags:
            writer.writerow(
                [
                    tag.tag_name,
                    tag.text,
                    tag.confidential_info,
                    tag.help_threshold,
                    tag.help_resources or "",
                ]
            )

        return response


class ImportTagsView(ManagerRequiredView):
    """View to handle importing tags from a CSV file."""

    def post(self, request, *args, **kwargs):
        """Handle POST requests to import tags from a CSV file.

        Returns:
            A JSON response object.
        """
        csv_file = request.FILES.get("csv_file")
        if not csv_file or not csv_file.name.endswith(".csv"):
            return JsonResponse({"error": "File is not CSV type"})

        if csv_file.multiple_chunks():
            return JsonResponse({"error": "Uploaded file is too big"})

        required_cols = [
            "Name",
            "Description",
            "Confidential_Info",
            "Help_Threshold",
            "Help_Resources",
        ]

        csv_file.open()
        text_file = io.TextIOWrapper(csv_file.file, encoding='utf-8')
        red = csv.DictReader(text_file)
        cols_present = red.fieldnames
        if any(req not in cols_present for req in required_cols):
            return JsonResponse(
                {"error": "CSV file does not have required column headings"}
            )

        for row in red:
            try:
                PedagogyTag.objects.get_or_create(
                    tag_name=row["Name"],
                    defaults={
                        "text": row["Description"],
                        "confidential_info": row["Confidential_Info"],
                        "help_threshold": row["Help_Threshold"],
                        "help_resources": row["Help_Resources"],
                    },
                )
            except Exception as e:
                return JsonResponse({"error": str(e)})

        return JsonResponse({"success": True})
