from django.shortcuts import render

from Base.base_group_views import ManagerRequiredView

from Papers.services import SpecificationService, PaperInfoService


class PaperCreationView(ManagerRequiredView):
    """
    Create test-papers in the database.
    """

    def build_context(self):
        spec = SpecificationService()
        paper_info = PaperInfoService()
        context = super().build_context()
        context.update(
            {
                "is_populated": paper_info.is_paper_database_populated(),
                "n_papers": spec.get_n_to_produce(),
                "n_questions": spec.get_n_questions(),
                "n_versions": spec.get_n_versions(),
                "n_pages": spec.get_n_pages(),
            }
        )
        return context

    def get(self, request):
        context = self.build_context()
        return render(request, "Preparation/test_paper_manage.html", context)
