# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2024-2025 Bryan Tanady

import csv
from io import StringIO

from django.core.exceptions import ValidationError
from django.contrib import messages
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse

from plom_server.Base.base_group_views import ManagerRequiredView
from plom_server.Papers.services import SpecificationService
from .forms import TaskOrderForm, UploadFileForm
from .services import TaskOrderService


class TaskOrderPageView(ManagerRequiredView):
    """A page for setting the task marking priorities."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """Get the main page for task ordering."""
        template_name = "TaskOrder/task_order_landing.html"

        context = self.build_context()
        order_form = TaskOrderForm()
        upload_form = UploadFileForm()

        order_form.fields["order_tasks_by"].initial = request.session.get(
            "order_tasks_by",
        )
        paper_to_priority_dict = TaskOrderService.get_paper_number_to_priority_list()

        context.update(
            {
                "order_form": order_form,
                "upload_form": upload_form,
                "qlabels": SpecificationService.get_question_html_label_triples(),
                "paper_to_priority_dict": paper_to_priority_dict,
            }
        )

        return render(request, template_name, context=context)

    @staticmethod
    def upload_task_priorities(request: HttpRequest) -> HttpResponse:
        """Upload the task priorities as a CSV file and update the database."""
        if request.method == "POST":
            order_by = request.POST.get("order_tasks_by")
            request.session["order_tasks_by"] = order_by

            custom_order = {}
            try:
                if order_by == "custom":

                    form = UploadFileForm(request.POST, request.FILES)
                    if not request.FILES:
                        raise ValidationError("No file uploaded")

                    elif not form.is_valid():
                        raise ValidationError("Invalid form: " + form.errors.as_text())

                    else:
                        file = form.cleaned_data["file"]
                        custom_order = TaskOrderService.handle_file_upload(file)
                TaskOrderService.update_priority_ordering(
                    order_by, custom_order=custom_order
                )
            except ValidationError as e:
                messages.error(request, str(e.message))

            except ValueError as e:
                messages.error(request, str(e))

            else:
                messages.success(request, "Task order updated successfully")

        return redirect("task_order_landing")

    @staticmethod
    def download_priorities(request: HttpRequest) -> HttpResponse:
        """Download the task priorities."""
        shortname = SpecificationService.get_short_name_slug()
        keys = TaskOrderService.get_csv_header()
        priorities = TaskOrderService.get_task_priorities_download()

        f = StringIO()
        w = csv.DictWriter(f, keys)
        w.writeheader()
        w.writerows(priorities)
        f.seek(0)

        filename = f"task-order--{shortname}.csv"

        response = HttpResponse(f, content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename={filename}".format(
            filename=filename
        )

        return response
