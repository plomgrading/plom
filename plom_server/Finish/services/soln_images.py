# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2025 Colin B. Macdonald

from django.core.files import File

from ..models import SolutionImage


class SolnImageService:
    @staticmethod
    def get_soln_image(qidx: int, version: int) -> File:
        """Return the solution image file for the given q/v.

        If the image is not present then an ObjectDoesNotExist
        exception thrown and it is up to the caller to deal with that.
        """
        return SolutionImage.objects.get(question_index=qidx, version=version).image
