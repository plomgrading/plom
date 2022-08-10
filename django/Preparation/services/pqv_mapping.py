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

    @transaction.atomic()
    def remove_pqv_map(self):
        StagingPQVMapping.objects.all().delete()

    @transaction.atomic()
    def use_pqv_map(self, valid_pqvmap):
        # assumes that there is no current pqvmap.
        # assumes that passed pqvmap is valid
        for paper_number, qvmap in valid_pqvmap.items():
            for question, version in qvmap.items():
                StagingPQVMapping.objects.create(
                    paper_number=paper_number, question=question, version=version
                )

    @transaction.atomic()
    def build_pqv_map_dict(self):
        pqvmapping = {}
        for pqv_obj in StagingPQVMapping.objects.all():
            if pqv_obj.paper_number in pqvmapping:
                pqvmapping[pqv_obj.paper_number][pqv_obj.question] = [pqv_obj.version]
            else:
                pqvmapping[pqv_obj.paper_number] = {pqv_obj.question: pqv_obj.version}
        return pqvmapping

    def make_version_map(self, numberToProduce):
        from plom import make_random_version_map

        demo_spec = get_demo_spec()
        # this spec does not include numberToProduce so we add in by hand
        demo_spec["numberToProduce"] = numberToProduce
        make_random_version_map(demo_spec)

        return make_random_version_map(demo_spec)

    def generate_and_set_pqvmap(self, numberToProduce):
        # delete old map, build a new one, and then use it.
        self.remove_pqv_map()
        pqvmap = self.make_version_map(numberToProduce)
        self.use_pqv_map(pqvmap)
