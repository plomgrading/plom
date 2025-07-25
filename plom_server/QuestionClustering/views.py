# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady

# Django
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseNotFound,
    Http404,
    QueryDict,
)
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist

# application
from plom_server.Papers.services import SpecificationService, PaperInfoService
from plom_server.Rectangles.services import get_reference_qr_coords_for_page
from plom_server.QuestionClustering.services import (
    QuestionClusteringJobService,
    QuestionClusteringService,
)
from plom_server.QuestionClustering.models import QVCluster, QVClusterLink
from plom_server.QuestionClustering.forms import ClusteringJobForm
from plom_server.QuestionClustering.exceptions.job_exception import (
    DuplicateClusteringJobError,
)
from plom_server.QuestionClustering.exceptions.clustering_exception import (
    NoSelectedClusterError,
)
from plom_server.Base.base_group_views import ManagerRequiredView
from plom_server.Base.models import HueyTaskTracker

# misc
from urllib.parse import urlencode


class Debug(ManagerRequiredView):
    def get(self, request):

        HueyTaskTracker.set_every_task_obsolete()
        QVClusterLink.objects.all().delete()
        QVCluster.objects.all().delete()

        return render(request, "QuestionClustering/clustering_jobs.html")


# ====== Clustering Home Page (choose q, v, page) =======
class QuestionClusteringHomeView(ManagerRequiredView):
    """Render clustering home page for choosing question-version pair for clustering."""

    def get(self, request: HttpRequest) -> HttpResponse:
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
        Display the page with previews of selected regions for clustering
        and begin clustering button.

    POST:
        Validate the clustering job form.
        On success: start clustering job then redirect to job
            page (POST/REDIRECT/GET design practice).
        On Failure: rerender current page with error messages.
    """

    def get(self, request: HttpRequest) -> HttpResponse:
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

            rects = {"left": left, "top": top, "right": right, "bottom": bottom}
            try:
                qcjs.start_cluster_qv_job(
                    question_idx=question_idx,
                    version=version,
                    page_num=page_num,
                    rects=rects,
                    clustering_model=choice,
                )

                messages.success(
                    request,
                    f"Started {choice} clustering for {SpecificationService.get_question_label(question_idx)}, V{version}",
                )
                return redirect("question_clustering_jobs_home")

            except DuplicateClusteringJobError as err:
                messages.error(request, f"Clustering job failed: {err}")
                return redirect("question_clustering_jobs_home")

        else:
            for field, errs in form.errors.items():
                for err in errs:
                    # associate each error with its field (or None for non-field)
                    messages.error(request, f"{field}: {err}")

            return render(request, "QuestionClustering/show_rectangles.html")


# ============== List of clustering jobs page (table of jobs) =====================
class QuestionClusteringJobsHome(ManagerRequiredView):
    """Render the page with all clustering jobs"""

    def get(self, request: HttpRequest) -> HttpResponse:
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
        qcjs = QuestionClusteringJobService()
        try:
            qcjs.delete_clustering_job(task_id)
            return HttpResponse(status=204)

        except ObjectDoesNotExist as err:
            return HttpResponseNotFound(f"Task {task_id} not found.")


# ========= Cluster detail page (# members, priorities, tags, etc) =============
class ClusterGroupsView(ManagerRequiredView):
    """Render a page for a summary of all clusters in a (q, v) context."""

    def get(
        self, request: HttpRequest, question_idx: int, version: int, page_num: int
    ) -> HttpResponse:

        qcs = QuestionClusteringService()
        # A list of (cluster_id, member_count) sorted by cluster_id
        # NOTE: use a sorted list so the default order is by cluster_id
        cluster_groups = qcs.get_clusters_and_member_count(
            question_idx=question_idx, version=version
        )

        # cluster_id to paper mapping used for preview
        cluster_to_paper_map = qcs.get_paper_nums_in_clusters(
            question_idx=question_idx, version=version
        )

        # corners used for clustering (for preview)
        rects = qcs.get_corners_used_for_clustering(
            question_idx=question_idx, version=version
        )

        # cluster_id to priority mapping
        cluster_to_priority = qcs.get_cluster_priority_map(
            question_idx=question_idx, version=version
        )

        # cluster_id to merged count
        merged_component_count = qcs.get_merged_component_count(
            question_idx=question_idx, version=version
        )

        # cluster_id to tags
        cluster_to_tags = qcs.cluster_ids_to_tags(
            question_idx=question_idx, version=version
        )

        context = {
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
    """Handle merge of multiple clusters in a (q, v) context."""

    def post(self, request: HttpRequest):
        clusterIds = request.POST.getlist("selected_clusters")
        clusterIds = list(map(int, clusterIds))

        question_idx = int(request.POST["question_idx"])
        version = int(request.POST["version"])
        next_url = request.POST.get("next")

        qcs = QuestionClusteringService()
        try:
            merged_cluster = qcs.merge_clusters(question_idx, version, clusterIds)

            messages.success(
                request,
                f"Merged {len(clusterIds)} clusters into cluster with id: {merged_cluster}",
            )
        except (ValueError, NoSelectedClusterError) as e:
            messages.error(request, f"Merge failed: {e}")
        return redirect(next_url)


class ClusterBulkDeleteView(ManagerRequiredView):
    """Handle delete of one or multiple clusters in a (q, v) context."""

    def post(self, request: HttpRequest) -> HttpResponse:
        clusterIds = request.POST.getlist("selected_clusters")
        clusterIds = list(map(int, clusterIds))

        question_idx = int(request.POST["question_idx"])
        version = int(request.POST["version"])
        next_url = request.POST.get("next")

        qcs = QuestionClusteringService()

        qcs.delete_clusters(question_idx, version, clusterIds)

        messages.success(request, f"Deleted {len(clusterIds)} clusters")
        return redirect(next_url)


class ClusterBulkResetView(ManagerRequiredView):
    def post(self, request: HttpRequest) -> HttpResponse:
        clusterIds = request.POST.getlist("selected_clusters")
        clusterIds = list(map(int, clusterIds))

        question_idx = int(request.POST["question_idx"])
        version = int(request.POST["version"])
        next_url = request.POST.get("next")

        qcs = QuestionClusteringService()

        qcs.reset_clusters(question_idx, version, clusterIds)

        messages.success(request, f"reset {len(clusterIds)} clusters")
        return redirect(next_url)


class UpdateClusterPriorityView(ManagerRequiredView):
    def post(self, request: HttpRequest) -> HttpResponse:
        next_url = request.POST.get("next") or request.META.get("HTTP_REFERER", "/")
        new_order = request.POST.getlist("cluster_order")
        question_idx = int(request.POST["question_idx"])
        version = int(request.POST["version"])

        qcs = QuestionClusteringService()
        new_order_int = list(map(int, new_order))
        qcs.update_priority_based_on_scene(new_order_int, question_idx, version)

        messages.success(request, "Updated priority to match scene")
        return redirect(next_url)


class ClusterBulkTaggingView(ManagerRequiredView):
    def post(self, request: HttpRequest) -> HttpResponse:
        next_url = request.POST.get("next") or request.META.get("HTTP_REFERER", "/")
        question_idx = int(request.POST["question_idx"])
        version = int(request.POST["version"])
        uid = request.user.id

        qcs = QuestionClusteringService()
        qcs.bulk_tagging(question_idx=question_idx, version=version, userid=uid)

        messages.success(request, "Bulk tagged")
        return redirect(next_url)


class RemoveTagFromClusterView(ManagerRequiredView):
    def delete(self, request: HttpRequest):

        qd = QueryDict(request.body.decode())
        question_idx = int(qd.get("question_idx"))
        version = int(qd.get("version"))
        clusterId = int(qd.get("clusterId"))
        tag_pk = int(qd.get("tag_pk"))

        qcs = QuestionClusteringService()
        qcs.remove_tag_from_a_cluster(
            question_idx=question_idx,
            version=version,
            clusterId=clusterId,
            tag_pk=tag_pk,
        )
        tags = qcs.cluster_ids_to_tags(question_idx=question_idx, version=version)[
            clusterId
        ]
        context = {
            "clusterId": clusterId,
            "tags": tags,
            "question_idx": question_idx,
            "version": version,
        }

        return render(
            request,
            "QuestionClustering/fragments/clustering_tag_cell.html",
            context=context,
        )


# =========== Papers inside a cluster ==============
class ClusteredPapersView(ManagerRequiredView):
    def get(
        self,
        request: HttpRequest,
        question_idx: int,
        version: int,
        page_num: int,
        clusterId: int,
    ) -> HttpResponse:
        qcs = QuestionClusteringService()
        papers = qcs.get_paper_nums_in_clusters(
            question_idx=question_idx, version=version
        )[clusterId]
        corners = qcs.get_corners_used_for_clustering(
            question_idx=question_idx, version=version
        )

        context = {
            "question_label": SpecificationService.get_question_label(question_idx),
            "question_idx": question_idx,
            "version": version,
            "page_num": page_num,
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
        question_idx: int,
        version: int,
        page_num: int,
        clusterId: int,
    ):

        qcs = QuestionClusteringService()
        papers_to_delete = request.POST.getlist("delete_ids")
        qcs.bulk_delete_cluster_members(
            question_idx=question_idx,
            version=version,
            clusterId=clusterId,
            paper_nums=list(map(int, papers_to_delete)),
        )

        corners = qcs.get_corners_used_for_clustering(
            question_idx=question_idx, version=version
        )
        papers = qcs.get_paper_nums_in_clusters(
            question_idx=question_idx, version=version
        )[clusterId]

        context = {
            "question_label": SpecificationService.get_question_label(question_idx),
            "question_idx": question_idx,
            "version": version,
            "page_num": page_num,
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
