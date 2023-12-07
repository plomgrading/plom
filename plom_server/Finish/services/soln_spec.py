# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

from typing import Dict

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from Papers.models import SolnSpecification, SolnSpecQuestion
from Papers.serializers import SolnSpecSerializer


class SolnSpecService:
    def is_there_a_solution_spec(self):
        """Has a soln-specification been uploaded to the database."""
        return SolnSpecification.objects.count() == 1

    def get_number_of_pages(self):
        return SolnSpecification.objects.get().numberOfPages

    def get_number_of_questions(self):
        # this should be equal to the number of questions in the test spec.
        return SolnSpecQuestion.objects.count()

    def get_pages_for_solution_n(self, solution_number: int):
        return SolnSpecQuestion.objects.get(solution_number=solution_number).pages

    def load_spec_from_dict(self, spec_dict: Dict):
        # convert the list of solns to a dict of soln with soln-numbers as keys
        spec_dict["solution"] = {
            str(i + 1): q for i, q in enumerate(spec_dict["solution"])
        }

        serializer = SolnSpecSerializer(data=spec_dict)
        print("v" * 20)
        serializer.is_valid()
        print("^" * 20)

        return serializer.create(serializer.validated_data)

    @transaction.atomic
    def remove_solution_spec(self):
        if not self.is_there_a_solution_spec():
            raise ObjectDoesNotExist(
                "The database does not contain a solution specification."
            )

        # vvvvvvvvvvvvvvvvvvvv
        # TODO - add logic here for when it is okay to remove the solution spec
        # ^^^^^^^^^^^^^^^^^^^^

        SolnSpecQuestion.objects.all().delete()
        SolnSpecification.objects.all().delete()
