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

class Debug(ManagerRequiredView):
    def get(self, request):


        HueyTaskTracker.set_every_task_obsolete()
        QVClusterLink.objects.all().delete()
        QVCluster.objects.all().delete()

        return render(request, "QuestionClustering/clustering_jobs.html")

class DeleteClusterMember(ManagerRequiredView):
    def post(self, request: HttpRequest,
        question_idx: int,
        version: int,
        page_num: int,
        clusterId: int):

        qcs = QuestionClusteringService()
        papers_to_delete = request.POST.getlist('delete_ids')
        for pn in papers_to_delete:
            qcs.delete_cluster_member(question_idx=question_idx, version=version, clusterId=clusterId, paper_num=int(pn))

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
        messages.success(request, f"Removed {len(papers_to_delete)} papers from cluster {clusterId}")
        return render(request, "QuestionClustering/clustered_papers.html", context=context)


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
        cluster_groups = qcs.get_cluster_groups_and_count(
            question_idx=question_idx, version=version
        )

        context = {
            "question_label": SpecificationService.get_question_label(question_idx),
            "question_idx": question_idx,
            "version": version,
            "page_num": page_num,
            "cluster_groups": cluster_groups,
        }
        return render(
            request, "QuestionClustering/cluster_groups.html", context=context
        )


class QuestionClusteringHomeView(ManagerRequiredView):
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
        context = self.build_context()
        left = round(float(request.POST.get("plom_left")), 6)
        top = round(float(request.POST.get("plom_top")), 6)
        right = round(float(request.POST.get("plom_right")), 6)
        bottom = round(float(request.POST.get("plom_bottom")), 6)

        # get all scanned papers with that page,version
        # paper_numbers may be duplicated if there are multiple questions on a page
        paper_numbers = PaperInfoService.get_paper_numbers_containing_page(
            page, version=version, scanned=True, limit=4
        )

        context.update(
            {
                "version": version,
                "question_index": qidx,
                "page_num": page,
                "left": left,
                "top": top,
                "right": right,
                "bottom": bottom,
                "papers": paper_numbers,
            }
        )
        return render(request, "QuestionClustering/show_rectangles.html", context)


class GetQuestionClusteringJobs(ManagerRequiredView):
    def get(self, request: HttpRequest) -> HttpResponse:

        qcs = QuestionClusteringService()
        tasks = qcs.get_question_clustering_tasks()
        return render(
            request, "QuestionClustering/clustering_jobs_table.html", {"tasks": tasks}
        )


class QuestionClusteringJobsHome(ManagerRequiredView):
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

    def post(self, request: HttpRequest) -> HttpResponse:

        question_idx = int(request.POST.get("question"))
        version = int(request.POST.get("version"))
        page_num = int(request.POST.get("page_num"))

        left = round(float(request.POST.get("plom_left")), 6)
        top = round(float(request.POST.get("plom_top")), 6)
        right = round(float(request.POST.get("plom_right")), 6)
        bottom = round(float(request.POST.get("plom_bottom")), 6)

        rects = {"left": left, "top": top, "right": right, "bottom": bottom}

        qcs = QuestionClusteringService()
        tasks = qcs.get_question_clustering_tasks()

        context = {"tasks": tasks}

        qcs.start_cluster_qv_job(
            question_idx=question_idx, version=version, page_num=page_num, rects=rects
        )

        messages.success(
            request,
            f"Started clustering for {SpecificationService.get_question_label(question_idx)}, V{version}",
        )
        return render(
            request, "QuestionClustering/clustering_jobs.html", context=context
        )
