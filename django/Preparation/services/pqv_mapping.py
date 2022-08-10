from django.core.files import File
from django.db import transaction

from Preparation.models import StagingStudent, StagingPQVMapping

from pathlib import Path
from tempfile import NamedTemporaryFile


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
