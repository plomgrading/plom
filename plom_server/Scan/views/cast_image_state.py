# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2024-2025 Colin B. Macdonald
# Copyright (C) 2025 Aidan Murphy

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest, HttpResponse, Http404
from django.shortcuts import render
from django.urls import reverse
from django_htmx.http import HttpResponseClientRedirect, HttpResponseClientRefresh

from plom_server.Base.base_group_views import ScannerRequiredView
from plom_server.Papers.services import SpecificationService, PaperInfoService

from ..services import (
    ScanCastService,
    ScanService,
    check_bundle_object_is_neither_locked_nor_pushed,
)

from plom.plom_exceptions import PlomBundleLockedException

from datetime import datetime


class DiscardImageView(ScannerRequiredView):
    """Discard a particular StagingImage type."""

    def post(self, request: HttpRequest, *, bundle_id: int, index: int) -> HttpResponse:
        try:
            ScanCastService.discard_image_type_from_bundle_id_and_order(
                request.user, bundle_id, index
            )
        except ValueError as e:
            raise Http404(e)
        except PlomBundleLockedException:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_lock", args=[bundle_id])
            )
        return render(
            request,
            "Scan/fragments/bundle_page_panel.html",
            {"bundle_id": bundle_id, "index": index},
        )


class DiscardAllUnknownsHTMXView(ScannerRequiredView):
    def post(
        self,
        request: HttpRequest,
        *,
        bundle_id: int,
    ) -> HttpResponse:
        """View that discards all unknowns from the given bundle."""
        try:
            ScanCastService().discard_all_unknowns_from_bundle_id(
                request.user, bundle_id
            )
        except ValueError as e:
            raise Http404(e)
        except PlomBundleLockedException:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_lock", args=[bundle_id])
            )
        return HttpResponseClientRefresh()


class UnknowifyImageView(ScannerRequiredView):
    """Unknowify a particular StagingImage type."""

    def post(self, request: HttpRequest, *, bundle_id: int, index: int) -> HttpResponse:
        try:
            ScanCastService().unknowify_image_type_from_bundle_id_and_order(
                request.user, bundle_id, index
            )
        except ValueError as e:
            raise Http404(e)
        except PlomBundleLockedException:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_lock", args=[bundle_id])
            )

        return render(
            request,
            "Scan/fragments/bundle_page_panel.html",
            {"bundle_id": bundle_id, "index": index},
        )


class UnknowifyAllDiscardsHTMXView(ScannerRequiredView):
    def post(
        self,
        request: HttpRequest,
        *,
        bundle_id: int,
    ) -> HttpResponse:
        """View that casts all discards in the given bundle as unknowns."""
        try:
            ScanCastService().unknowify_all_discards_from_bundle_id(
                request.user, bundle_id
            )
        except ValueError as e:
            raise Http404(e)
        except PlomBundleLockedException:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_lock", args=[bundle_id])
            )
        return HttpResponseClientRefresh()


class KnowifyImageView(ScannerRequiredView):
    """Knowify a particular StagingImage type."""

    def get(self, request: HttpRequest, *, bundle_id: int, index: int) -> HttpResponse:
        context = super().build_context()
        scanner = ScanService()
        paper_info = PaperInfoService()
        bundle = scanner.get_bundle_from_pk(bundle_id)

        try:
            check_bundle_object_is_neither_locked_nor_pushed(bundle)
        except PlomBundleLockedException:
            # TODO: this would confuse me as a user:
            # bounce user back to scanner home page if not allowed to change things
            return HttpResponseClientRedirect(
                reverse("scan_bundle_lock", args=[bundle_id])
            )

        n_pages = scanner.get_n_images(bundle)

        if index < 0 or index > n_pages:
            raise Http404("Bundle page does not exist.")

        context.update(
            {
                "is_pushed": bundle.pushed,
                "bundle_id": bundle_id,
                "index": index,
                "total_pages": n_pages,
                "timestamp": datetime.now().timestamp(),
            }
        )

        page_labels = [
            f"page {n + 1}" for n in range(SpecificationService.get_n_pages())
        ]
        all_paper_numbers = paper_info.which_papers_in_database()
        missing_papers_pages = scanner.get_bundle_missing_paper_page_numbers(bundle)
        context.update(
            {
                "page_labels": page_labels,
                "all_paper_numbers": all_paper_numbers,
                "missing_papers_pages": missing_papers_pages,
            }
        )

        return render(request, "Scan/fragments/knowify_image.html", context)

    def post(self, request: HttpRequest, *, bundle_id: int, index: int) -> HttpResponse:
        # TODO - improve this form processing

        knowify_page_data = request.POST

        if knowify_page_data.get("bundleOrArbitrary", "off") == "on":
            try:
                paper_number, page_number = knowify_page_data.get(
                    "missingPaperPage", ","
                ).split(",")
            except ValueError:
                return HttpResponse(
                    """<div class="alert alert-danger">Choose paper/page</div>"""
                )
        else:
            paper_number = knowify_page_data.get("arbitraryPaper", None)
            page_number = knowify_page_data.get("pageSelect", None)

        try:
            paper_number = int(paper_number)
        except ValueError:
            return HttpResponse(
                """<div class="alert alert-danger">Invalid paper number</div>"""
            )

        try:
            page_number = int(page_number)
        except ValueError:
            return HttpResponse(
                """<div class="alert alert-danger">Select a page</div>"""
            )

        try:
            ScanCastService().knowify_image_from_bundle_id(
                request.user, bundle_id, index, paper_number, page_number
            )
        except ValueError as err:
            return HttpResponse(f"""<div class="alert alert-danger">{err}</div>""")
        except PlomBundleLockedException:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_lock", args=[bundle_id])
            )

        return render(
            request,
            "Scan/fragments/bundle_page_panel.html",
            {"bundle_id": bundle_id, "index": index},
        )


class ExtraliseImageView(ScannerRequiredView):
    """Extralise a particular StagingImage type."""

    def post(self, request: HttpRequest, *, bundle_id: int, index: int) -> HttpResponse:
        # TODO - improve this form processing

        extra_page_data = request.POST

        paper_number = extra_page_data.get("paper_number", None)

        try:
            paper_number = int(paper_number)
        except (ValueError, TypeError):
            return HttpResponse(
                """<span class="alert alert-danger">Invalid paper number</span>""",
                status=409,
            )

        choice = extra_page_data.get("question_all_dnm", "")
        if choice == "choose_all":
            # set all the questions
            to_questions = SpecificationService.get_question_indices()
        elif choice == "choose_dnm":
            # TODO: or explicitly empty list or ...?
            to_questions = []
        elif choice == "choose_q":
            # caution: `get` would return just the last entry
            to_questions = [int(q) for q in extra_page_data.getlist("questions")]
            if not to_questions:
                return HttpResponse(
                    """<span class="alert alert-danger">At least one question</span>"""
                )
        else:
            return HttpResponse(
                """<span class="alert alert-danger">
                    Unexpected radio choice: this is a bug; please file an issue!
                </span>"""
            )

        try:
            ScanCastService().assign_extra_page_from_bundle_pk_and_order(
                request.user, bundle_id, index, paper_number, to_questions
            )
        except PlomBundleLockedException:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_lock", args=[bundle_id])
            )
        except ValueError as e:
            return HttpResponse(
                f"""<div class="alert alert-danger"><p>{e}</p><p>Try reloading this page.</p></div>"""
            )

        return render(
            request,
            "Scan/fragments/bundle_page_panel.html",
            {"bundle_id": bundle_id, "index": index},
        )

    # TODO: Post and Put are the wrong way around? Put should update the existing extra page, Post should create a new one?
    def put(self, request: HttpRequest, *, bundle_id: int, index: int) -> HttpResponse:
        """Cast an existing bundle page to an extra page (unassigned)."""
        try:
            ScanCastService.extralise_image_from_bundle_id(
                request.user, bundle_id, index
            )
        except PlomBundleLockedException:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_lock", args=[bundle_id])
            )
        except ObjectDoesNotExist as err:
            return Http404(err)
        except ValueError as err:
            print(f"Issue #3878: got ValueError we're unsure how to handle: {err}")
            # TODO: redirect ala scan_bundle_lock?
            raise

        return render(
            request,
            "Scan/fragments/bundle_page_panel.html",
            {"bundle_id": bundle_id, "index": index},
        )

    def delete(
        self, request: HttpRequest, *, bundle_id: int, index: int
    ) -> HttpResponse:
        try:
            ScanCastService().clear_extra_page_info_from_bundle_pk_and_order(
                request.user, bundle_id, index
            )
        except PlomBundleLockedException:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_lock", args=[bundle_id])
            )

        return render(
            request,
            "Scan/fragments/bundle_page_panel.html",
            {"bundle_id": bundle_id, "index": index},
        )
