import pathlib
from django.views import View
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView
from braces.views import LoginRequiredMixin, GroupRequiredMixin

from Base.base_group_views import ManagerRequiredView

from SpecCreator.services import StagingSpecificationService, ReferencePDFService
from .. import models


class TestSpecPageView(ManagerRequiredView):
    def build_context(self, page_name):
        context = super().build_context()
        spec = StagingSpecificationService()

        context.update({
            "long_name": spec.get_long_name(),
            "short_name": spec.get_short_name(),
            "slugged_short_name": spec.get_short_name_slug(),
            "curr_page": page_name,
            "questions": [i for i in range(spec.get_n_questions())],
            "completed": {}
        })

        return context


class TestSpecPDFView(TestSpecPageView):
    def build_context(self, page_name):
        context = super().build_context(page_name)
        spec = StagingSpecificationService()
        ref = ReferencePDFService()
        if ref.is_there_a_reference_pdf():
            thumbnails = ref.create_page_thumbnail_list()
            context.update({
                "thumbnails": thumbnails,
                "num_pages": spec.get_n_pages(),
            })

        return context
