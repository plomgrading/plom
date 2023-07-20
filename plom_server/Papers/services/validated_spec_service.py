# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022 Colin B. Macdonald
# Copyright (C) 2022 Brennen Chiu

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db import transaction

import tomlkit

from Papers.models import Specification
from Papers.services import PaperInfoService

# TODO - build similar for solution specs
# NOTE - this does not **validate** test specs, it assumes the spec is valid

import logging

log = logging.getLogger("ValidatedSpecService")


class SpecificationService:
    @transaction.atomic
    def is_there_a_spec(self):
        """Has a test-specification been uploaded to the database."""
        return Specification.objects.count() == 1

    @transaction.atomic
    def get_the_spec(self):
        """Return the test-specification from the database."""
        try:
            return Specification.objects.get().spec_dict
        except Specification.DoesNotExist:
            raise ObjectDoesNotExist(
                "The database does not contain a test specification."
            )

    @transaction.atomic
    def get_the_spec_as_toml(self):
        """Return the test-specification from the database.
        If present, remove the private seed and public code.
        """
        spec = self.get_the_spec()
        spec.pop("publicCode", None)
        spec.pop("privateSeed", None)
        return tomlkit.dumps(spec)

    @transaction.atomic
    def store_validated_spec(self, validated_spec):
        """Takes the validated test specification and stores it in the db

        validated_spec (dict): A dictionary containing a validated test
            specification.
        """
        spec_obj = Specification(spec_dict=validated_spec)
        spec_obj.save()

    @transaction.atomic
    def remove_spec(self):
        """Removes the test specification from the db. This can only be done
        if no tests have been created.
        """
        if not self.is_there_a_spec():
            raise ObjectDoesNotExist(
                "The database does not contain a test specification."
            )

        pis = PaperInfoService()
        if pis.is_paper_database_populated():
            raise MultipleObjectsReturned(
                "Database is already populated with test-papers."
            )

        Specification.objects.filter().delete()

    @transaction.atomic
    def get_n_questions(self):
        """
        Get the number of questions in the test.
        """
        spec_obj = self.get_the_spec()
        return spec_obj["numberOfQuestions"]

    @transaction.atomic
    def get_n_versions(self):
        """
        Get the number of test versions.
        """
        spec_obj = self.get_the_spec()
        return spec_obj["numberOfVersions"]

    @transaction.atomic
    def get_n_pages(self):
        """
        Get the number of pages in the test.
        """
        spec_obj = self.get_the_spec()
        return spec_obj["numberOfPages"]

    @transaction.atomic
    def get_n_to_produce(self):
        """
        Get the number of papers to produce.
        """
        spec_obj = self.get_the_spec()
        return spec_obj["numberToProduce"]

    @transaction.atomic
    def modify_n_to_produce(self, n):
        """
        Modify the number of papers to produce - assumes it's a valid value.
        """
        spec_obj = Specification.objects.get()
        spec_obj.spec_dict["numberToProduce"] = n
        spec_obj.save()

    @transaction.atomic
    def get_question_mark(self, question_one_index):
        """
        Get the max mark of a given question

        Args:
            question_one_index (str/int): question number, indexed from 1.

        Raises:
            KeyError: question out of range
        """
        spec_obj = self.get_the_spec()
        return spec_obj["question"][str(question_one_index)]["mark"]

    @transaction.atomic
    def n_pages_for_question(self, question_one_index):
        spec_obj = self.get_the_spec()
        pages = spec_obj["question"][str(question_one_index)]["pages"]
        return len(pages)
