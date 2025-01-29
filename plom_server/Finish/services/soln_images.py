# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2025 Colin B. Macdonald

from django.core.files import File
from django.db import transaction

from ..models import SolutionImage


class SolnImageService:
    @transaction.atomic
    def get_soln_image(self, question: int, version: int) -> File:
        """Return the soln image file for the given q/v.

        If the image is not present then an ObjectDoesNotExist
        exception thrown and it is up to the caller to deal with that.
        """
        return SolutionImage.objects.get(
            solution_number=question, version=version
        ).image
