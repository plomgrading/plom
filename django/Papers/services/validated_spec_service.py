from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db import transaction

import toml

from Papers.models import TestSpecification
from Papers.services import PaperInfoService

# TODO - build similar for solution specs
# NOTE - this does not **validate** test specs, it assumes the spec is valid

import logging

log = logging.getLogger("ValidatedSpecService")


class TestSpecificationService:
    @transaction.atomic
    def is_there_a_spec(self):
        """Has a test-specification been uploaded to the database."""
        return TestSpecification.objects.count() == 1

    @transaction.atomic
    def get_the_spec(self):
        """Return the test-specification from the database."""
        try:
            return TestSpecification.objects.get().spec_dict
        except TestSpecification.DoesNotExist:
            raise ObjectDoesNotExist(
                "The database does not contain a test specification."
            )

    @transaction.atomic
    def get_the_spec_as_toml(self):
        """Return the test-specification from the database."""
        return toml.dumps(TestSpecification.objects.get().spec_dict)

    @transaction.atomic
    def store_validated_spec(self, validated_spec):
        """Takes the validated test specification and stores it in the db

        validated_spec (dict): A dictionary containing a validated test
            specification.
        """
        spec_obj = TestSpecification(spec_dict=validated_spec)
        spec_obj.save()

    @transaction.atomic
    def remove_spec(self):
        """Removes the test specification from the db. This can only be done
        if no tests have been created.
        """
        if not self.is_there_a_test_spec():
            raise ObjectDoesNotExist(
                "The database does not contain a test specification."
            )

        pis = PaperInfoService()
        if pis.is_paper_database_populated():
            raise MultipleObjectsReturned(
                "Database is already populated with test-papers."
            )

        TestSpecification.objects.filter().delete()
