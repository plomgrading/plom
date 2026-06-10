# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady
# Copyright (C) 2025-2026 Colin B. Macdonald
# Copyright (C) 2026 Deep Shah

from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest, HttpResponse, HttpResponseNotFound, Http404
from django.shortcuts import render, redirect
from django.urls import reverse

from plom_server.Base.base_group_views import ManagerRequiredView
from plom_server.Base.models import HueyTaskTracker
from plom_server.Papers.services import SpecificationService, PaperInfoService
from plom_server.Rectangles.services import get_reference_qr_coords_for_page
from .services import QuestionClusteringJobService, QuestionClusteringService
from .models import QVCluster, QVClusterLink
from .forms import ClusteringJobForm
from .exceptions.clustering_exception import EmptySelectedError


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
        context.update(
            {
                "version": version,
                "page_num": page,
                "qr_info": qr_info,
                "top_left": rect_top_left,
                "bottom_right": rect_bottom_right,
                "q_label": SpecificationService.get_question_label(qidx),
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

        params = {
            "version": version,
            "question_index": qidx,
            "page_num": page,
            "left": left,
            "top": top,
            "right": right,
            "bottom": bottom,
        }
        url = reverse("preview_clustering_region")
        return redirect(f"{url}?{urlencode(params)}")


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

        initial = {
            "question": int(params["question_index"]),
            "version": version,
            "page_num": page_num,
            "left": float(params["left"]),
            "top": float(params["top"]),
            "right": float(params["right"]),
            "bottom": float(params["bottom"]),
        }
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

            qcjs = QuestionClusteringJobService()

            rect = {"left": left, "top": top, "right": right, "bottom": bottom}
            qcjs.start_cluster_qv_job(
                question_idx=question_idx,
                version=version,
                page_num=page_num,
                rect=rect,
                clustering_model=choice,
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
class ClusterGroupsView(ManagerRequiredView):
    """Render a page for a summary of all clusters in a clustering job."""

    def get(self, request: HttpRequest, task_id: int) -> HttpResponse:
        """Render a page for a summary of all clusters in a clustering job."""
        qcs = QuestionClusteringService()
        job = qcs.get_clustering_chore(task_id)
        question_idx = job.question_idx
        version = job.version
        page_num = job.page_num
        # A list of (cluster_id, member_count) sorted by cluster_id
        # NOTE: use a sorted list so the default order is by cluster_id
        cluster_groups = qcs.get_clusters_and_member_count(task_id)

        # cluster_id to paper mapping used for preview
        cluster_to_paper_map = qcs.get_paper_nums_in_clusters(task_id)

        # corners used for clustering (for preview)
        rects = qcs.get_corners_used_for_clustering(task_id)

        # cluster_id to priority mapping
        cluster_to_priority = qcs.get_cluster_priority_map(task_id)

        # cluster_id to merged count
        merged_component_count = qcs.get_merged_component_count(task_id)

        # cluster_id to tags
        cluster_to_tags = qcs.cluster_ids_to_tags(task_id)

        context = {
            "task_id": task_id,
            "question_label": SpecificationService.get_question_label(question_idx),
            "question_idx": question_idx,
            "version": version,
            "page_num": page_num,
            "cluster_groups": cluster_groups,
            "cluster_to_paper_map": cluster_to_paper_map,
            "cluster_to_priority": cluster_to_priority,
            "cluster_to_tags": cluster_to_tags,
            "merged_count": merged_component_count,
            "top": rects["top"],
            "left": rects["left"],
            "right": rects["right"],
            "bottom": rects["bottom"],
        }
        return render(
            request, "QuestionClustering/cluster_groups.html", context=context
        )


class ClusterMergeView(ManagerRequiredView):
    """Handle merge of multiple clusters in a clustering job."""

    def post(self, request: HttpRequest):
        """Handle merge of multiple clusters in a clustering job."""
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
        """Handle deletion of one or multiple clusters in a clustering job."""
        clusterIds = request.POST.getlist("selected_clusters")
        clusterIds = list(map(int, clusterIds))

        task_id = int(request.POST["task_id"])
        next_url = request.POST.get("next")

        qcs = QuestionClusteringService()

        qcs.delete_clusters(task_id, clusterIds)

        messages.success(request, f"Deleted {len(clusterIds)} clusters")
        return redirect(next_url)


class ClusterBulkResetView(ManagerRequiredView):
    """Handle reset of one or multiple clusters in a clustering job."""

    def post(self, request: HttpRequest) -> HttpResponse:
        """Handle reset of one or multiple clusters in a clustering job."""
        clusterIds = request.POST.getlist("selected_clusters")
        clusterIds = list(map(int, clusterIds))

        task_id = int(request.POST["task_id"])
        next_url = request.POST.get("next")

        qcs = QuestionClusteringService()

        qcs.reset_clusters(task_id, clusterIds)

        messages.success(request, f"reset {len(clusterIds)} clusters")
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
        job = qcs.get_clustering_chore(task_id)
        papers = qcs.get_paper_nums_in_clusters(task_id)[clusterId]
        corners = qcs.get_corners_used_for_clustering(task_id)

        context = {
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
        }
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
        job = qcs.get_clustering_chore(task_id)
        papers_to_delete = request.POST.getlist("delete_ids")
        qcs.bulk_delete_cluster_members(
            task_id=task_id,
            clusterId=clusterId,
            paper_nums=list(map(int, papers_to_delete)),
        )

        corners = qcs.get_corners_used_for_clustering(task_id)
        papers = qcs.get_paper_nums_in_clusters(task_id)[clusterId]

        context = {
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
        }
        messages.success(
            request, f"Removed {len(papers_to_delete)} papers from cluster {clusterId}"
        )
        return render(
            request, "QuestionClustering/clustered_papers.html", context=context
        )
