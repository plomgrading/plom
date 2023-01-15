from django.urls import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django_htmx.http import HttpResponseClientRefresh

from Base.base_group_views import ManagerRequiredView
from Papers.services import (
    PaperCreatorService,
    PaperInfoService,
    SpecificationService,
)
from Papers.models import CreatePaperTask
from Preparation.services import PQVMappingService


class CreateTestPapers(ManagerRequiredView):
    """
    Create test-papers in the database, using the test specification, classlist,
    and question-version map.
    """

    def post(self, request):
        pcs = PaperCreatorService()
        qvs = PQVMappingService()

        qvmap = qvs.get_pqv_map_dict()
        status, err = pcs.add_all_papers_in_qv_map(qvmap)
        if not status:
            print(err)

        progress_url = reverse("papers_progress")
        return HttpResponse(
            f'<p class="card-text" hx-get="{progress_url}" hx-trigger="every 0.5s">Creating test-papers...</p>'
        )

    def delete(self, request):
        """
        For testing purposes: delete all papers from the database.
        """
        pcs = PaperCreatorService()
        pcs.remove_all_papers_from_db()
        CreatePaperTask.objects.all().delete()
        return HttpResponseClientRefresh()


class TestPaperProgress(ManagerRequiredView):
    """
    Get the database creation progress.
    """

    def get(self, request):
        pinfo = PaperInfoService()
        spec = SpecificationService()

        n_to_produce = spec.get_n_to_produce()
        papers_in_database = pinfo.how_many_papers_in_database()

        if papers_in_database == n_to_produce:
            return HttpResponseClientRefresh()
        else:
            percent_complete = papers_in_database / n_to_produce * 100
            progress_url = reverse("papers_progress")
            return HttpResponse(
                f"""
                <p class=\"card-text\" hx-get=\"{progress_url}\" hx-trigger=\"every 0.5s\">
                    {papers_in_database} papers complete out of {n_to_produce}
                    ({int(percent_complete)}%)
                </p>"""
            )
