from django.http import HttpResponseRedirect
from django.urls import reverse

from Base.base_group_views import ManagerRequiredView
from Papers.services import PaperInfoService

from SpecCreator.services import StagingSpecificationService, ReferencePDFService


class TestSpecPageView(ManagerRequiredView):
    def dispatch(self, request):
        """
        Redirect to the assessment preparation page if the Papers database
        is already populated
        """
        paper_info = PaperInfoService()
        if paper_info.is_paper_database_populated():
            return HttpResponseRedirect(reverse("prep_landing"))
        return super().dispatch()

    def build_context(self, page_name):
        context = super().build_context()
        spec = StagingSpecificationService()

        context.update(
            {
                "long_name": spec.get_long_name(),
                "short_name": spec.get_short_name(),
                "slugged_short_name": spec.get_short_name_slug(),
                "curr_page": page_name,
                "questions": [i for i in range(spec.get_n_questions())],
                "completed": spec.get_progress_dict(),
            }
        )

        print(spec.get_progress_dict())

        return context


class TestSpecPDFView(TestSpecPageView):
    def build_context(self, page_name):
        context = super().build_context(page_name)
        spec = StagingSpecificationService()
        ref = ReferencePDFService()
        if ref.is_there_a_reference_pdf():
            thumbnails = ref.create_page_thumbnail_list()
            context.update(
                {
                    "thumbnails": thumbnails,
                    "num_pages": spec.get_n_pages(),
                }
            )

        return context
