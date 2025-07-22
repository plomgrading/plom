# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady

from pathlib import Path
from tempfile import NamedTemporaryFile

from django.http import (
    HttpRequest,
    HttpResponse,
    FileResponse,
    Http404,
)

from django.core.files.base import ContentFile
from django.shortcuts import render
from django.contrib import messages

from plom_server.Papers.services import SpecificationService, PaperInfoService
from plom_server.Preparation.services import SourceService
from plom_server.Base.base_group_views import ManagerRequiredView
from plom_server.Rectangles.services import get_reference_qr_coords_for_page
from plom_server.QuestionClustering.services import QuestionClusteringService
from plom_server.Base.models import HueyTaskTracker
from plom_server.QuestionClustering.models import QVCluster, QVClusterLink
from plom_server.QuestionClustering.forms import ClusteringJobForm
from django.shortcuts import redirect
from django.urls import reverse
from urllib.parse import urlencode


class Debug(ManagerRequiredView):
    def get(self, request):

        HueyTaskTracker.set_every_task_obsolete()
        QVClusterLink.objects.all().delete()
        QVCluster.objects.all().delete()

        return render(request, "QuestionClustering/clustering_jobs.html")


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


class SelectRectangleForClusteringView(ManagerRequiredView):
    """Render rectangle selection used for clustering

    GET:
        Display rectangle extractor page for selecting region for clustering

    POST:
        Submit the selected region and redirect to preview page using
        POST/REDIRECT/GET design practice
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


class PreviewSelectedRectsView(ManagerRequiredView):
    """Render page to show previews of selected regions

    GET:
        Display the page with previews of selected regions for clustering
        and begin clustering button

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

        # get 4 scanned papers for previews
        paper_numbers = PaperInfoService.get_paper_numbers_containing_page(
            page_num, version=version, scanned=True, limit=4
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

            qcs = QuestionClusteringService()

            rects = {"left": left, "top": top, "right": right, "bottom": bottom}
            qcs.start_cluster_qv_job(
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

        else:
            for field, errs in form.errors.items():
                for err in errs:
                    # associate each error with its field (or None for non-field)
                    messages.error(request, f"{field}: {err}")

            return render(request, "QuestionClustering/show_rectangles.html")


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


class GetQuestionClusteringJobs(ManagerRequiredView):
    def get(self, request: HttpRequest) -> HttpResponse:

        qcs = QuestionClusteringService()
        tasks = qcs.get_question_clustering_tasks()
        return render(
            request, "QuestionClustering/clustering_jobs_table.html", {"tasks": tasks}
        )


class DeleteClusterMember(ManagerRequiredView):
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
        for pn in papers_to_delete:
            qcs.delete_cluster_member(
                question_idx=question_idx,
                version=version,
                clusterId=clusterId,
                paper_num=int(pn),
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


class ClusterGroupsView(ManagerRequiredView):
    def get(
        self, request: HttpRequest, question_idx: int, version: int, page_num: int
    ) -> HttpResponse:

        qcs = QuestionClusteringService()
        cluster_groups = qcs.get_user_facing_clusters(
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

        # cluster_id to types
        merged_component_count = qcs.get_merged_component_count(
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
            "merged_count": merged_component_count,
            "top": rects["top"],
            "left": rects["left"],
            "right": rects["right"],
            "bottom": rects["bottom"],
        }
        return render(
            request, "QuestionClustering/cluster_groups.html", context=context
        )


class UpdateClusterPriorityView(ManagerRequiredView):
    def post(self, request: HttpRequest) -> HttpResponse:
        next_url = request.POST.get("next") or request.META.get("HTTP_REFERER", "/")
        new_order = request.POST.getlist("cluster_order")
        question_idx = int(request.POST["question_idx"])
        version = int(request.POST["version"])

        qcs = QuestionClusteringService()
        new_order_int = list(map(int, new_order))
        print(f"test: {new_order_int}")
        qcs.update_priority_based_on_scene(new_order_int, question_idx, version)

        messages.success(request, "Updated priority to match scene")
        return redirect(next_url)


class ClusterMergeView(ManagerRequiredView):
    def post(self, request: HttpRequest):
        clusterIds = request.POST.getlist("selected_clusters")
        clusterIds = list(map(int, clusterIds))

        question_idx = int(request.POST["question_idx"])
        version = int(request.POST["version"])
        next_url = request.POST.get("next")

        qcs = QuestionClusteringService()
        qcs.merge_clusters(question_idx, version, clusterIds)

        messages.success(
            request,
            f"Merged {len(clusterIds)} clusters into cluster with id: {min(clusterIds)}",
        )
        return redirect(next_url)


class ClusterBulkDeleteView(ManagerRequiredView):
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
