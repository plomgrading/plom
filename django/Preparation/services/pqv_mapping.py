from django.core.files import File
from django.db import transaction

from Preparation.models import StagingStudent, StagingPQVMapping

from .temp_functions import get_demo_spec


class PQVMappingService:
    @transaction.atomic()
    def is_there_a_pqv_map(self):
        return StagingPQVMapping.objects.exists()

    @transaction.atomic()
    def list_of_paper_numbers(self):
        paper_numbers = [
            x
            for x in StagingPQVMapping.objects.values_list("paper_number", flat=True)
            .order_by("paper_number")
            .distinct()
        ]
        return paper_numbers

    def make_version_map(self, numberToProduce):
        from plom import make_random_version_map
        demo_spec = get_demo_spec()
        # note that this spec does not include numberToProduce so we add it manually.
        demo_spec['numberToProduce'] = numberToProduce
        pqvmap = make_random_version_map(demo_spec)
        print(pqvmap)
