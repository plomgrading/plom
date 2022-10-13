from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db import transaction

import toml

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
        return toml.dumps(spec)

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
    def get_question_mark(self, question_one_index):
        """
        Get the max mark of a given question
        """
        spec_obj = self.get_the_spec()
        return spec_obj["question"][str(question_one_index)]["mark"]