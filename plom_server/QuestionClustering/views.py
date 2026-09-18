# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady
# Copyright (C) 2025-2026 Colin B. Macdonald
# Copyright (C) 2026 Deep Shah

import json
from typing import Any
from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseNotFound,
    JsonResponse,
)
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.urls import reverse

from plom_server.Base.base_group_views import ManagerRequiredView
from plom_server.Base.models import HueyTaskTracker
from plom_server.Papers.models import ReferenceImage
from plom_server.Papers.services import SpecificationService, PaperInfoService
from plom_server.Rectangles.services import get_reference_qr_coords_for_page
from plom_server.Preparation.services import QuestionRegionsService
from .services.mcq_box_detection import detect_mcq_boxes_for_reference_image
from .services import QuestionClusteringJobService, QuestionClusteringService
from .models import (
    ClusteringModelType,
    QuestionClusteringChore,
    QVCluster,
    QVClusterLink,
)
from .forms import ClusteringJobForm
from .exceptions.clustering_exception import EmptySelectedError


def _build_mcq_metadata(
    cleaned_data: dict[str, Any], clustering_model: ClusteringModelType
) -> dict[str, Any]:
    """Build MCQ option-box metadata from the clustering form, if present."""
    is_mcq_model = clustering_model == ClusteringModelType.MCQ
    if not is_mcq_model or cleaned_data.get("question_type") != "MCQ":
        return {}

    raw_mcq_boxes = cleaned_data.get("mcq_boxes")
    if not raw_mcq_boxes:
        raise ValueError("No MCQ option boxes were submitted.")

    try:
        submitted_metadata = json.loads(raw_mcq_boxes)
    except json.JSONDecodeError as err:
        raise ValueError("MCQ option boxes were not valid JSON.") from err

    if not isinstance(submitted_metadata, dict):
        raise ValueError("MCQ option boxes were not submitted in the expected format.")

    boxes = submitted_metadata.get("boxes", [])
    if not isinstance(boxes, list) or not boxes:
        raise ValueError("No MCQ option boxes were submitted.")

    normalised_boxes = []
    for idx, box in enumerate(boxes):
        if not isinstance(box, dict):
            raise ValueError(
                "MCQ option boxes were not submitted in the expected format."
            )

        try:
            normalised_boxes.append(
                {
                    "label": str(box["label"]),
                    "left": round(float(box["left"]), 6),
                    "top": round(float(box["top"]), 6),
                    "right": round(float(box["right"]), 6),
                    "bottom": round(float(box["bottom"]), 6),
                }
            )
        except (KeyError, TypeError, ValueError) as err:
            raise ValueError(
                f"MCQ option box {idx + 1} is missing valid coordinates."
            ) from err

    return {
        "question_type": "MCQ",
        "num_options": int(
            submitted_metadata.get("num_options")
            or cleaned_data.get("mcq_num_options")
            or len(normalised_boxes)
        ),
        "boxes": normalised_boxes,
    }


def _get_padded_mcq_box(
    box: dict[str, Any], padding_ratio: float = 0.15
) -> dict[str, float | str]:
    left = float(box["left"])
    top = float(box["top"])
    right = float(box["right"])
    bottom = float(box["bottom"])
    width = right - left
    height = bottom - top
    pad_x = width * padding_ratio
    pad_y = height * padding_ratio
    return {
        "left": max(0.0, left - pad_x),
        "top": max(0.0, top - pad_y),
        "right": min(1.0, right + pad_x),
        "bottom": min(1.0, bottom + pad_y),
    }


def _build_mcq_crop_preview_boxes(raw_mcq_boxes: str) -> list[dict[str, Any]]:
    """Build padded option-box crop coordinates for the pre-clustering preview."""
    try:
        submitted_metadata = json.loads(raw_mcq_boxes)
    except json.JSONDecodeError as err:
        raise ValueError("MCQ option boxes were not valid JSON.") from err

    if not isinstance(submitted_metadata, dict):
        raise ValueError("MCQ option boxes were not submitted in the expected format.")

    boxes = submitted_metadata.get("boxes", [])
    if not isinstance(boxes, list):
        raise ValueError("MCQ option boxes were not submitted in the expected format.")

    preview_boxes = []
    for box in boxes:
        if not isinstance(box, dict):
            continue
        padded_box = _get_padded_mcq_box(box)
        padded_box["label"] = str(box.get("label", "?"))
        preview_boxes.append(padded_box)
    return preview_boxes


def _get_mcq_cluster_label_map(job: QuestionClusteringChore) -> dict[int, str]:
    """Build display labels for checkbox-aware MCQ clusters, if available."""
    if job.clustering_model != ClusteringModelType.MCQ or not isinstance(
        job.mcq_metadata, dict
    ):
        return {}

    boxes = job.mcq_metadata.get("boxes", [])
    if not isinstance(boxes, list) or not boxes:
        return {}

    labels = [
        str(box["label"]) for box in boxes if isinstance(box, dict) and "label" in box
    ]
    if not labels:
        return {}

    label_map = {idx: label for idx, label in enumerate(labels)}
    label_map[len(labels)] = "blank"
    label_map[len(labels) + 1] = "multiple"
    label_map[len(labels) + 2] = "ambiguous"
    return label_map


class Debug(ManagerRequiredView):
    """Temp debug."""

    def get(self, request):
        """Temp debug."""
        HueyTaskTracker.set_every_task_obsolete()
        QVClusterLink.objects.all().delete()
        QVCluster.objects.all().delete()

        return render(request, "QuestionClustering/clustering_jobs.html")


# ====== Clustering Home Page (choose q, v, page) =======
class QuestionClusteringHomeView(ManagerRequiredView):
    """Render clustering home page for choosing question-version pair for clustering."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """Render clustering home page for choosing question-version pair for clustering."""
        context = self.build_context()
        if not SpecificationService.is_there_a_spec():
            return render(request, "Finish/finish_no_spec.html", context=context)

        context.update(
            {
                "version_list": SpecificationService.get_list_of_versions(),
                "q_idx_label_pairs": SpecificationService.get_question_index_label_pairs(),
                "q_idx_to_pages": SpecificationService.get_question_pages(),
            }
        )
        return render(request, "QuestionClustering/home.html", context)


# ========== Rectangle selector for clustering ===============
class SelectRectangleForClusteringView(ManagerRequiredView):
    """Render rectangle selection used for clustering.

    GET:
        Display rectangle extractor page for selecting region for clustering.

    POST:
        Submit the selected region and redirect to preview page.
    """

    def get(
        self, request: HttpRequest, version: int, qidx: int, page: int
    ) -> HttpResponse:
        """Display rectangle extractor page for selecting region for clustering."""
        context = self.build_context()
        try:
            qr_info = get_reference_qr_coords_for_page(page, version=version)
        except ValueError as err:
            raise Http404(err) from err
        x_coords = [X[0] for X in qr_info.values()]
        y_coords = [X[1] for X in qr_info.values()]
        rect_top_left = [min(x_coords), min(y_coords)]
        rect_bottom_right = [max(x_coords), max(y_coords)]

        # regions = QuestionRegionsService.get_question_regions()
        # for x in regions:
        #     print(x)

        # TODO: this seems messy, need new service for this?
        region_info_per_page = QuestionRegionsService.get_region_info_per_page()
        # print(region_info_per_page)
        print("* " * 42)
        region_info_per_page = [x for x in region_info_per_page if x["page"] == page]
        if len(region_info_per_page) > 0:
            Z = region_info_per_page[0]["question_regions"]
            Z = [x for x in Z if x["qidx"] == qidx]
            region_info_per_page[0]["question_regions"] = Z
            region_info_per_page[0]["ref_image_html_id"] = "reference_image"
            region_info_per_page[0]["canvas_html_id"] = "canvas"
        for x in region_info_per_page:
            print(x)

        context.update(
            {
                "version": version,
                "page_num": page,
                "qr_info": qr_info,
                "top_left": rect_top_left,
                "bottom_right": rect_bottom_right,
                "q_label": SpecificationService.get_question_label(qidx),
                "region_info_per_page": region_info_per_page,
            }
        )
        return render(request, "QuestionClustering/select.html", context)

    def post(
        self, request: HttpRequest, version: int, qidx: int, page: int
    ) -> HttpResponse:
        """Submit the selected region and redirect to preview page."""
        left = round(float(request.POST.get("plom_left")), 6)
        top = round(float(request.POST.get("plom_top")), 6)
        right = round(float(request.POST.get("plom_right")), 6)
        bottom = round(float(request.POST.get("plom_bottom")), 6)

        params: dict[str, int | float | str] = {
            "version": version,
            "question_index": qidx,
            "page_num": page,
            "left": left,
            "top": top,
            "right": right,
            "bottom": bottom,
        }
        if request.POST.get("question_type") == "MCQ":
            params.update(
                {
                    "question_type": "MCQ",
                    "mcq_num_options": request.POST.get("mcq_num_options", "4"),
                    "mcq_boxes": request.POST.get("mcq_boxes", "[]"),
                }
            )
        url = reverse("preview_clustering_region")
        return redirect(f"{url}?{urlencode(params)}")


class DetectMCQBoxesView(ManagerRequiredView):
    """Detect MCQ checkbox positions inside a selected reference-page region."""

    def get(
        self, request: HttpRequest, version: int, page: int
    ) -> HttpResponse | JsonResponse:
        """Return detected MCQ option boxes as JSON."""
        try:
            selected_rect = {
                "left": float(request.GET["left"]),
                "top": float(request.GET["top"]),
                "right": float(request.GET["right"]),
                "bottom": float(request.GET["bottom"]),
            }
            num_options = int(request.GET.get("num_options", "4"))
        except (KeyError, TypeError, ValueError) as err:
            return HttpResponseBadRequest(f"Invalid MCQ detection request: {err}")

        if num_options < 1:
            return HttpResponseBadRequest("num_options must be positive.")

        try:
            reference_image = ReferenceImage.objects.get(
                version=version, page_number=page
            )
            boxes = detect_mcq_boxes_for_reference_image(
                reference_image, selected_rect, num_options
            )
        except ReferenceImage.DoesNotExist as err:
            raise Http404(
                f"There is no reference image for v{version} pg{page}."
            ) from err
        except ValueError as err:
            return JsonResponse({"error": str(err)}, status=400)

        return JsonResponse(
            {
                "boxes": boxes,
                "requested_num_options": num_options,
            }
        )


# ======== Page to preview selected regions ===============
class PreviewSelectedRectsView(ManagerRequiredView):
    """Render page to show previews of selected regions.

    GET:
        Display the page with previews of selected regions for clustering.

    POST:
        Validate the clustering job form.
        On success: start clustering job then redirect to job
            page (POST/REDIRECT/GET design practice).
        On Failure: rerender current page with error messages.
    """

    def get(self, request: HttpRequest) -> HttpResponse:
        """Display the page with previews of selected regions for clustering."""
        context = self.build_context()

        params = request.GET
        page_num = int(params["page_num"])
        version = int(params["version"])

        # get some scanned papers for previews
        num_previews = 4
        paper_numbers = PaperInfoService.get_paper_numbers_containing_page(
            page_num, version=version, scanned=True, limit=num_previews
        )

        initial: dict[str, int | float | str] = {
            "question": int(params["question_index"]),
            "version": version,
            "page_num": page_num,
            "left": float(params["left"]),
            "top": float(params["top"]),
            "right": float(params["right"]),
            "bottom": float(params["bottom"]),
        }
        if params.get("question_type") == "MCQ":
            raw_mcq_boxes = params.get("mcq_boxes", "[]")
            initial.update(
                {
                    "choice": str(ClusteringModelType.MCQ),
                    "question_type": "MCQ",
                    "mcq_num_options": params.get("mcq_num_options", "4"),
                    "mcq_boxes": raw_mcq_boxes,
                }
            )
            try:
                context["mcq_crop_boxes"] = _build_mcq_crop_preview_boxes(raw_mcq_boxes)
            except ValueError as err:
                context["mcq_crop_preview_error"] = str(err)
        form = ClusteringJobForm(initial=initial)

        context.update(initial)
        context.update({"clustering_job_form": form, "papers": paper_numbers})

        return render(request, "QuestionClustering/show_rectangles.html", context)

    def post(self, request: HttpRequest) -> HttpResponse:
        """Validate the clustering job form.

        On success: start clustering job then redirect to job
            page (POST/REDIRECT/GET design practice).
        On Failure: rerender current page with error messages.
        """
        form = ClusteringJobForm(request.POST)
        if form.is_valid():
            choice = form.cleaned_data["choice"]
            question_idx = form.cleaned_data["question"]
            version = form.cleaned_data["version"]
            page_num = form.cleaned_data["page_num"]
            left = form.cleaned_data["left"]
            top = form.cleaned_data["top"]
            right = form.cleaned_data["right"]
            bottom = form.cleaned_data["bottom"]

            try:
                mcq_metadata = _build_mcq_metadata(form.cleaned_data, choice)
            except ValueError as err:
                messages.error(request, str(err))
                return redirect("question_clustering_home")

            qcjs = QuestionClusteringJobService()

            rect = {"left": left, "top": top, "right": right, "bottom": bottom}
            qcjs.start_cluster_qv_job(
                question_idx=question_idx,
                version=version,
                page_num=page_num,
                rect=rect,
                clustering_model=choice,
                mcq_metadata=mcq_metadata,
            )

            messages.success(
                request,
                f"Started {choice} clustering for {SpecificationService.get_question_label(question_idx)}, v{version}",
            )
            return redirect("question_clustering_jobs_home")

        else:
            for field, errors in form.errors.items():
                for error in errors:
                    # associate each error with its field (or None for non-field)
                    messages.error(request, f"{field}: {error}")

            return render(request, "QuestionClustering/show_rectangles.html")


# ============== List of clustering jobs page (table of jobs) =====================
class QuestionClusteringJobsHome(ManagerRequiredView):
    """Render the page with all clustering jobs."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """Render the page with all clustering jobs."""
        context = self.build_context()
        if not SpecificationService.is_there_a_spec():
            return render(request, "Finish/finish_no_spec.html", context=context)

        qcs = QuestionClusteringService()
        tasks = qcs.get_question_clustering_tasks()

        context.update(
            {
                "version_list": SpecificationService.get_list_of_versions(),
                "q_idx_label_pairs": SpecificationService.get_question_index_label_pairs(),
                "q_idx_to_pages": SpecificationService.get_question_pages(),
                "tasks": tasks,
            }
        )
        return render(request, "QuestionClustering/clustering_jobs.html", context)


class QuestionClusteringJobTable(ManagerRequiredView):
    """Render a fragment html for the table of jobs."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """Render a fragment html for the table of jobs."""
        qcs = QuestionClusteringService()
        tasks = qcs.get_question_clustering_tasks()
        return render(
            request,
            "QuestionClustering/fragments/clustering_jobs_table.html",
            {"tasks": tasks},
        )


class ClusteringErrorJobInfoView(ManagerRequiredView):
    """Render the error info modal dialog for failed job."""

    def get(self, request: HttpRequest, task_id: int) -> HttpResponse:
        """Render the error info modal dialog for failed job."""
        qcjs = QuestionClusteringJobService()
        try:
            task = qcjs.get_clustering_job(task_id)
            context = {"message": task["message"]}

        except ObjectDoesNotExist as err:
            context = {"message": err}

        return render(
            request,
            "QuestionClustering/fragments/error_detail_modal.html",
            context=context,
        )


class RemoveJobView(ManagerRequiredView):
    """Delete a clustering job."""

    def delete(self, request: HttpRequest, task_id: int) -> HttpResponse:
        """Delete a clustering job."""
        qcjs = QuestionClusteringJobService()
        try:
            qcjs.delete_clustering_job(task_id)
            return HttpResponse(status=204)

        except ObjectDoesNotExist:
            return HttpResponseNotFound(f"Task {task_id} not found.")


# ========= Cluster detail page (# members, priorities, tags, etc) =============
def _get_cluster_groups_context(
    task_id: int,
    *,
    include_table_context: bool,
):
    """Build shared context for cluster table and unclustered review pages."""
    qcs = QuestionClusteringService()
    job = qcs.get_clustering_chore(task_id)
    cluster_groups = qcs.get_clusters_and_member_count(task_id)
    cluster_to_paper_map = qcs.get_paper_nums_in_clusters(task_id)
    cluster_to_name = qcs.get_cluster_name_map(task_id)
    rects = qcs.get_corners_used_for_clustering(task_id)
    unclustered_papers = qcs.get_unclustered_paper_nums(task_id)

    context = {
        "task_id": task_id,
        "question_label": SpecificationService.get_question_label(job.question_idx),
        "question_idx": job.question_idx,
        "version": job.version,
        "page_num": job.page_num,
        "cluster_groups": cluster_groups,
        "cluster_to_paper_map": cluster_to_paper_map,
        "cluster_to_name": cluster_to_name,
        "unclustered_papers": unclustered_papers,
        "top": rects["top"],
        "left": rects["left"],
        "right": rects["right"],
        "bottom": rects["bottom"],
    }

    if include_table_context:
        context.update(
            {
                "cluster_to_priority": qcs.get_cluster_priority_map(task_id),
                "cluster_to_tags": qcs.cluster_ids_to_tags(task_id),
                "merged_count": qcs.get_merged_component_count(task_id),
                "cluster_id_to_label": _get_mcq_cluster_label_map(job),
            }
        )

    return context


class ClusterGroupsView(ManagerRequiredView):
    """Render a page for a summary of all clusters in a clustering job."""

    def get(self, request: HttpRequest, task_id: int) -> HttpResponse:
        """Render a page for a summary of all clusters in a clustering job."""
        if request.GET.get("unclustered"):
            return redirect("unclustered_papers", task_id)

        try:
            context = _get_cluster_groups_context(
                task_id,
                include_table_context=True,
            )
        except ObjectDoesNotExist as err:
            messages.error(request, err)
            return redirect("question_clustering_jobs_home")
        return render(
            request, "QuestionClustering/cluster_groups.html", context=context
        )


class UnclusteredPapersView(ManagerRequiredView):
    """Render unclustered paper review for a clustering job."""

    def get(self, request: HttpRequest, task_id: int) -> HttpResponse:
        """Render unclustered paper review for a clustering job."""
        try:
            context = _get_cluster_groups_context(
                task_id,
                include_table_context=False,
            )
        except ObjectDoesNotExist as err:
            messages.error(request, err)
            return redirect("question_clustering_jobs_home")

        return render(
            request, "QuestionClustering/unclustered_papers.html", context=context
        )


class ClusterMergeView(ManagerRequiredView):
    """Handle merge of multiple clusters in a clustering job."""

    def post(self, request: HttpRequest):
        """Handle merge of multiple clusters in a (q, v) context."""
        clusterIds = request.POST.getlist("selected_clusters")
        clusterIds = list(map(int, clusterIds))

        task_id = int(request.POST["task_id"])
        next_url = request.POST.get("next")

        qcs = QuestionClusteringService()
        try:
            merged_cluster = qcs.merge_clusters(task_id, clusterIds)

            messages.success(
                request,
                f"Merged {len(clusterIds)} clusters into cluster with id: {merged_cluster}",
            )
        except (ValueError, EmptySelectedError) as e:
            messages.error(request, f"Merge failed: {e}")
        return redirect(next_url)


class ClusterBulkDeleteView(ManagerRequiredView):
    """Handle deletion of one or multiple clusters in a clustering job."""

    def post(self, request: HttpRequest) -> HttpResponse:
        """Handle deletion of one or multiple clusters in a (q, v) context."""
        clusterIds = request.POST.getlist("selected_clusters")
        clusterIds = list(map(int, clusterIds))

        task_id = int(request.POST["task_id"])
        next_url = request.POST.get("next")

        qcs = QuestionClusteringService()

        qcs.delete_clusters(task_id, clusterIds)

        messages.success(request, f"Deleted {len(clusterIds)} clusters")
        return redirect(next_url)


class AssignUnclusteredPapersView(ManagerRequiredView):
    """Assign unclustered papers to an existing user-facing cluster."""

    def post(self, request: HttpRequest) -> HttpResponse:
        """Assign selected paper numbers to a target cluster.

        This endpoint is used by ordinary form posts from the clustered and
        unclustered paper pages.  Those callers get a redirect and Django
        message.  The unclustered review page also calls this endpoint with
        htmx for drag/drop assignment and suggested-assignment application;
        htmx callers get JSON with updated counts.
        The caller updates several existing page elements after a successful
        assignment, including count badges, card removal, and cluster previews.

        Cluster suggestions are read-only and handled by
        ``SuggestUnclusteredPapersView``.
        """
        task_id = int(request.POST["task_id"])
        clusterId = int(request.POST["target_cluster_id"])
        next_url = request.POST.get("next") or reverse("cluster_groups", args=[task_id])

        paper_nums = list(map(int, request.POST.getlist("paper_nums")))
        qcs = QuestionClusteringService()
        is_htmx = request.htmx

        try:
            member_count = qcs.assign_papers_to_cluster(
                task_id=task_id,
                clusterId=clusterId,
                paper_nums=paper_nums,
            )
        except EmptySelectedError as err:
            if is_htmx:
                return JsonResponse({"ok": False, "message": str(err)}, status=400)
            messages.error(request, f"Assign failed: {err}")
        except ObjectDoesNotExist as err:
            if is_htmx:
                return JsonResponse({"ok": False, "message": str(err)}, status=404)
            messages.error(request, f"Assign failed: {err}")
        else:
            if is_htmx:
                unclustered_count = len(qcs.get_unclustered_paper_nums(task_id))
                return JsonResponse(
                    {
                        "ok": True,
                        "clusterId": clusterId,
                        "member_count": member_count,
                        "unclustered_count": unclustered_count,
                        "paper_nums": paper_nums,
                    }
                )
            messages.success(
                request, f"Assigned {len(paper_nums)} papers to cluster {clusterId}"
            )

        return redirect(next_url)


class CreateClusterFromUnclusteredPapersView(ManagerRequiredView):
    """Create a new user-facing cluster from selected unclustered papers."""

    def post(self, request: HttpRequest) -> HttpResponse:
        """Create a new cluster from selected paper numbers.

        The current template uses this as a normal form action and expects a
        redirect with a Django message.  The JSON response is kept for callers
        that create clusters without a full page reload.
        """
        task_id = int(request.POST["task_id"])
        next_url = request.POST.get("next") or reverse("cluster_groups", args=[task_id])

        paper_nums = list(map(int, request.POST.getlist("paper_nums")))
        qcs = QuestionClusteringService()
        is_htmx = request.htmx

        try:
            clusterId, member_count = qcs.create_cluster_from_papers(
                task_id=task_id,
                paper_nums=paper_nums,
            )
        except EmptySelectedError as err:
            if is_htmx:
                return JsonResponse({"ok": False, "message": str(err)}, status=400)
            messages.error(request, f"Create cluster failed: {err}")
        else:
            if is_htmx:
                unclustered_count = len(qcs.get_unclustered_paper_nums(task_id))
                return JsonResponse(
                    {
                        "ok": True,
                        "clusterId": clusterId,
                        "member_count": member_count,
                        "unclustered_count": unclustered_count,
                        "paper_nums": paper_nums,
                        "view_members_url": reverse(
                            "clustered_papers",
                            args=[task_id, clusterId],
                        ),
                        "tag_html": render_to_string(
                            "QuestionClustering/fragments/clustering_tag_cell.html",
                            {
                                "clusterId": clusterId,
                                "tags": set(),
                                "task_id": task_id,
                            },
                            request=request,
                        ),
                    }
                )
            messages.success(
                request, f"Created cluster {clusterId} from {len(paper_nums)} papers"
            )

        return redirect(next_url)


class SuggestUnclusteredPapersView(ManagerRequiredView):
    """Suggest target clusters for currently unclustered papers."""

    def post(self, request: HttpRequest) -> HttpResponse:
        """Return suggested cluster assignments without applying them.

        The unclustered review page calls this with htmx and receives a
        server-rendered suggestions panel.  Applying a suggestion is a separate
        htmx POST to ``AssignUnclusteredPapersView``.
        """
        task_id = int(request.POST["task_id"])

        qcs = QuestionClusteringService()
        try:
            suggestions = qcs.suggest_clusters_for_unclustered_papers(task_id)
        except ValueError as err:
            if request.htmx:
                context = _get_cluster_groups_context(
                    task_id,
                    include_table_context=False,
                )
                context.update(
                    {
                        "suggestions": [],
                        "suggestion_status": str(err),
                        "suggestion_status_tone": "danger",
                    }
                )
                return render(
                    request,
                    "QuestionClustering/fragments/unclustered_suggestions_panel.html",
                    context=context,
                )
            return JsonResponse({"ok": False, "message": str(err)}, status=400)

        if request.htmx:
            context = _get_cluster_groups_context(
                task_id,
                include_table_context=False,
            )
            context["suggestions"] = suggestions
            if not suggestions:
                context.update(
                    {
                        "suggestion_status": "No suggestions available.",
                        "suggestion_status_tone": "info",
                    }
                )
            return render(
                request,
                "QuestionClustering/fragments/unclustered_suggestions_panel.html",
                context=context,
            )

        return JsonResponse({"ok": True, "suggestions": suggestions})


class ClusterResetView(ManagerRequiredView):
    """Handle full reset of clusters in a clustering job."""

    def post(self, request: HttpRequest) -> HttpResponse:
        """Handle reset of all clusters in a (q, v) context."""
        task_id = int(request.POST["task_id"])
        next_url = request.POST.get("next")

        qcs = QuestionClusteringService()
        try:
            affected_cluster_ids = qcs.reset_clusters(task_id)
        except (EmptySelectedError, ObjectDoesNotExist) as err:
            messages.error(request, f"Reset failed: {err}")
        else:
            messages.success(
                request,
                "Restored the original clustering for all clusters; "
                f"updated {len(affected_cluster_ids)} original clusters.",
            )
        return redirect(next_url)


class UpdateClusterPriorityView(ManagerRequiredView):
    """Update cluster priorities."""

    def post(self, request: HttpRequest) -> HttpResponse:
        """Update cluster priorities."""
        next_url = request.POST.get("next") or request.META.get("HTTP_REFERER", "/")
        new_order = request.POST.getlist("cluster_order")
        task_id = int(request.POST["task_id"])

        qcs = QuestionClusteringService()
        new_order_int = list(map(int, new_order))
        qcs.update_priority_based_on_cluster_order(new_order_int, task_id)

        messages.success(
            request, "Updated priorities based on cluster order in the table"
        )
        return redirect(next_url)


class UpdateClusterNameView(ManagerRequiredView):
    """Update the human-readable name of a cluster."""

    def post(self, request: HttpRequest) -> HttpResponse:
        """Update the human-readable name of a cluster."""
        next_url = request.POST.get("next") or request.META.get("HTTP_REFERER", "/")
        task_id = int(request.POST["task_id"])
        clusterId = int(request.POST["clusterId"])
        cluster_name = request.POST.get("cluster_name", "")

        qcs = QuestionClusteringService()
        try:
            qcs.update_cluster_name(
                task_id=task_id,
                clusterId=clusterId,
                cluster_name=cluster_name,
            )
        except (ObjectDoesNotExist, ValueError) as err:
            messages.error(request, f"Could not update cluster name: {err}")
        else:
            messages.success(request, f"Updated name for cluster {clusterId}")
        return redirect(next_url)


class ClusterBulkTaggingView(ManagerRequiredView):
    """Tag one or multiple clusters."""

    def post(self, request: HttpRequest) -> HttpResponse:
        """Tag one or multiple clusters."""
        next_url = request.POST.get("next") or request.META.get("HTTP_REFERER", "/")
        task_id = int(request.POST["task_id"])
        uid = request.user.id

        qcs = QuestionClusteringService()
        qcs.bulk_tagging(task_id, userid=uid)

        messages.success(request, "Bulk tagged")
        return redirect(next_url)


class RemoveTagFromClusterView(ManagerRequiredView):
    """Remove tag from a particular cluster."""

    def delete(self, request: HttpRequest) -> HttpResponse:
        """Remove tag from a particular cluster."""
        task_id = int(request.GET.get("task_id"))
        clusterId = int(request.GET.get("clusterId"))
        tag_pk = int(request.GET.get("tag_pk"))

        qcs = QuestionClusteringService()
        job = qcs.get_clustering_chore(task_id)
        qcs.remove_tag_from_a_cluster(
            task_id=task_id,
            clusterId=clusterId,
            tag_pk=tag_pk,
        )
        tags = qcs.cluster_ids_to_tags(task_id)[clusterId]
        context = {
            "task_id": task_id,
            "clusterId": clusterId,
            "tags": tags,
            "question_idx": job.question_idx,
            "version": job.version,
        }

        return render(
            request,
            "QuestionClustering/fragments/clustering_tag_cell.html",
            context=context,
        )


# =========== Papers inside a cluster ==============
def _clustered_papers_context(
    qcs: QuestionClusteringService,
    task_id: int,
    clusterId: int,
) -> dict:
    """Build context for the clustered papers page."""
    job = qcs.get_clustering_chore(task_id)
    papers = qcs.get_paper_nums_in_clusters(task_id)[clusterId]
    corners = qcs.get_corners_used_for_clustering(task_id)
    cluster_groups = qcs.get_clusters_and_member_count(task_id)
    target_cluster_groups = [
        (cid, count) for cid, count in cluster_groups if cid != clusterId
    ]
    cluster_to_name = qcs.get_cluster_name_map(task_id)

    return {
        "task_id": task_id,
        "question_label": SpecificationService.get_question_label(job.question_idx),
        "question_idx": job.question_idx,
        "version": job.version,
        "page_num": job.page_num,
        "clusterId": clusterId,
        "papers": papers,
        "top": corners["top"],
        "left": corners["left"],
        "bottom": corners["bottom"],
        "right": corners["right"],
        "cluster_groups": cluster_groups,
        "target_cluster_groups": target_cluster_groups,
        "cluster_to_name": cluster_to_name,
    }


class ClusteredPapersView(ManagerRequiredView):
    """Render a page of papers in a particular cluster."""

    def get(
        self,
        request: HttpRequest,
        task_id: int,
        clusterId: int,
    ) -> HttpResponse:
        """Render a page of papers in a particular cluster."""
        qcs = QuestionClusteringService()
        context = _clustered_papers_context(
            qcs=qcs,
            task_id=task_id,
            clusterId=clusterId,
        )
        return render(
            request, "QuestionClustering/clustered_papers.html", context=context
        )


class DeleteClusterMember(ManagerRequiredView):
    """Handle removal of a paper from a cluster."""

    def post(
        self,
        request: HttpRequest,
    ) -> HttpResponse:
        """Handle removal of a paper from a cluster."""
        task_id = int(request.POST.get("task_id"))
        clusterId = int(request.POST.get("clusterId"))

        qcs = QuestionClusteringService()
        papers_to_delete = request.POST.getlist("delete_ids") or request.POST.getlist(
            "paper_nums"
        )
        qcs.bulk_delete_cluster_members(
            task_id=task_id,
            clusterId=clusterId,
            paper_nums=list(map(int, papers_to_delete)),
        )

        context = _clustered_papers_context(
            qcs=qcs,
            task_id=task_id,
            clusterId=clusterId,
        )
        messages.success(
            request, f"Removed {len(papers_to_delete)} papers from cluster {clusterId}"
        )
        return render(
            request, "QuestionClustering/clustered_papers.html", context=context
        )
