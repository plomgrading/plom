# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald

from django.shortcuts import render
from django.http import Http404
from django_htmx.http import HttpResponseClientRefresh

from Base.base_group_views import ScannerRequiredView
from Papers.services import ImageBundleService
from ..services import ScanService
from ..forms import FlagImageForm, ReplaceImageForm


class ReadQRcodesView(ScannerRequiredView):
    """Read QR codes of all pages in a bundle."""

    def post(self, request, timestamp):
        try:
            timestamp = float(timestamp)
        except ValueError:
            return Http404()

        scanner = ScanService()
        bundle = scanner.get_bundle(timestamp, request.user)
        scanner.read_qr_codes(bundle.pk)

        return HttpResponseClientRefresh()


class UpdateQRProgressView(ScannerRequiredView):
    """Get the progress of a background QR code reading task."""

    def build_context(self, timestamp, user, index):
        context = super().build_context()
        scanner = ScanService()
        form = FlagImageForm()
        replace_image_form = ReplaceImageForm()
        bundle = scanner.get_bundle(timestamp, user)
        task_status = scanner.get_qr_code_reading_status(bundle, index)

        context.update(
            {
                "timestamp": timestamp,
                "index": index,
                "task_status": task_status,
                "form": form,
                "replace_image_form": replace_image_form,
            }
        )

        image = scanner.get_image(timestamp, user, index)
        img_service = ImageBundleService()
        if img_service.image_exists(image.image_hash):
            context.update({"image_exists": True})

        if task_status:
            context.update({"in_progress": True})
            qr_data = scanner.get_qr_code_results(bundle, index)
            if qr_data:
                code = list(qr_data.values())[0]  # get the first sub-dict
                qr_results = {
                    "paper_id": code["paper_id"],
                    "page_num": code["page_num"],
                    "version_num": code["version_num"],
                }
                context.update({"qr_results": qr_results})
            if task_status == "error" and image.error:
                stagged_bundle = image.bundle
                flagged_bundle = img_service.get_or_create_bundle(
                    stagged_bundle.slug, stagged_bundle.pdf_hash
                )
                flag_image = scanner.get_error_image(flagged_bundle, index)
                # most_common_qr = scanner.get_common_qr_code(qr_data)

                context.update(
                    {
                        "error": scanner.get_qr_code_error_message(bundle, index),
                        "error_paper_id": flag_image.paper_number,
                        "error_page_num": flag_image.page_number,
                        "error_version_num": flag_image.version_number,
                        "image_error": image.error,
                    }
                )
                if flag_image.flagged:
                    context.update({"flagged": True})
            if task_status == "error" and image.colliding:
                colliding_image = scanner.get_collision_image(bundle, index)
                # most_common_qr = scanner.get_common_qr_code(qr_data)
                context.update(
                    {
                        "error": scanner.get_qr_code_error_message(bundle, index),
                        "error_paper_id": colliding_image.paper_number,
                        "error_page_num": colliding_image.page_number,
                        "error_version_num": colliding_image.version_number,
                        "collision": image.colliding,
                    }
                )
            if task_status == "error" and image.unknown:
                context.update(
                    {
                        "error": scanner.get_qr_code_error_message(bundle, index),
                        "unknown": image.unknown,
                    }
                )

        return context

    def get(self, request, timestamp, index):
        try:
            timestamp = float(timestamp)
        except ValueError:
            raise Http404()

        context = self.build_context(timestamp, request.user, index)
        return render(request, "Scan/fragments/qr_code_panel.html", context)


class QRParsingProgressAlert(ScannerRequiredView):
    """Display and update an alert while QR code reading is in progress."""

    def post(self, request, timestamp):
        try:
            timestamp = float(timestamp)
        except ValueError:
            raise Http404()

        context = self.build_context()
        scanner = ScanService()
        bundle = scanner.get_bundle(timestamp, request.user)

        if scanner.is_bundle_reading_finished(bundle) and not bundle.has_qr_codes:
            scanner.qr_reading_cleanup(bundle)
            n_complete = len(scanner.get_all_complete_images(bundle))
            context.update({"n_complete": n_complete, "timestamp": timestamp})
            return render(request, "Scan/fragments/qr_complete_modal.html", context)

        context.update(
            {
                "reading_ongoing": scanner.is_bundle_reading_ongoing(bundle),
                "total_pages": scanner.get_n_images(bundle),
                "total_complete": scanner.get_n_complete_reading_tasks(bundle),
                "timestamp": timestamp,
                "finished": scanner.is_bundle_reading_finished(bundle),
            }
        )

        return render(request, "Scan/fragments/qr_code_alert.html", context)


class BundleTableView(UpdateQRProgressView):
    def get(self, request, timestamp, index):
        try:
            timestamp = float(timestamp)
        except ValueError:
            raise Http404()
        context = self.build_context(timestamp, request.user, index)

        scanner = ScanService()
        bundle = scanner.get_bundle(timestamp, request.user)
        num_images = scanner.get_n_images(bundle)
        all_images = scanner.get_all_images(bundle)
        qr_code_list = scanner.bundle_contains_list(all_images, num_images)

        paper_id = []
        page_num = []
        version_num = []
        for qr_code in qr_code_list:
            if qr_code != "unknown page":
                paper_id.append(str(qr_code[:5]).lstrip("0"))
                page_num.append(str(qr_code[5:8]).lstrip("0"))
                version_num.append(str(qr_code[8:11]).lstrip("0"))

        context.update(
            {
                "qr_reading": scanner.is_bundle_reading_ongoing(bundle),
                "paper_list": zip(paper_id, page_num, version_num),
            }
        )

        return render(request, "Scan/fragments/bundle_table.html", context)
