import pathlib
from django.views import View
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView
from braces.views import LoginRequiredMixin, GroupRequiredMixin

from Base.base_group_views import ManagerRequiredView

from ..services import TestSpecService, TestSpecProgressService, ReferencePDFService
from .. import models


class TestSpecPageView(ManagerRequiredView):
    def build_context(self, page_name):
        context = super().build_context()
        spec = TestSpecService()
        progress = TestSpecProgressService(spec)

        context.update({
            "long_name": spec.get_long_name(),
            "short_name": spec.get_short_name(),
            "slugged_short_name": spec.get_short_name_slug(),
            "curr_page": page_name,
            "questions": [i for i in range(spec.get_n_questions())],
            "completed": progress.get_progress_dict()
        })

        return context


class TestSpecPDFView(TestSpecPageView):
    def build_context(self, page_name):
        context = super().build_context(page_name)
        spec = TestSpecService()
        n_pages = spec.get_n_pages()
        if n_pages > 0:
            spec = TestSpecService()
            ref = ReferencePDFService(spec)
            thumbnails = ref.create_page_thumbnail_list()
            context.update({
                "thumbnails": thumbnails,
                "pages": spec.get_page_list(),
                "num_pages": spec.get_n_pages(),
            })

        return context
