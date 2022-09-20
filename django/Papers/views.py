from django.urls import reverse
from django.http import HttpResponseRedirect

from Base.base_group_views import ManagerRequiredView
from Papers.services import PaperCreatorService
from Preparation.services import PQVMappingService


class CreateTestPapers(ManagerRequiredView):
    """
    Create test-papers in the database, using the test specification, classlist,
    and question-version map.
    """

    def post(self, request):
        pcs = PaperCreatorService()
        qvs = PQVMappingService()

        # for debugging purposes!
        pcs.remove_all_papers_from_db()

        qvmap = qvs.get_pqv_map_dict()
        status, err = pcs.add_all_papers_in_qv_map(qvmap)
        if not status:
            print(err)

        return HttpResponseRedirect(reverse("prep_test_papers"))
