# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2023 Colin B. Macdonald
# Copyright (C) 2022 Brennen Chiu

import logging
from typing import Dict

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db import transaction

from plom import SpecVerifier

from ..models import Specification
from ..services import PaperInfoService

# TODO - build similar for solution specs
# NOTE - this does not **validate** test specs, it assumes the spec is valid


log = logging.getLogger("ValidatedSpecService")


class SpecificationService:
    @transaction.atomic
    def is_there_a_spec(self):
        """Has a test-specification been uploaded to the database."""
        return Specification.objects.count() == 1

    @transaction.atomic
    def get_the_spec(self) -> Dict:
        """Return the test-specification from the database.

        Returns:
            The exam specification as a dictionary.

        Exceptions:
            ObjectDoesNotExist: no exam specification yet.
        """
        try:
            return Specification.objects.get().spec_dict
        except Specification.DoesNotExist:
            raise ObjectDoesNotExist(
                "The database does not contain a test specification."
            )

    @transaction.atomic
    def get_the_spec_as_toml(self):
        """Return the test-specification from the database.

        If present, remove the private seed.  But the public code
        is included (if present).
        """
        sv = SpecVerifier(self.get_the_spec())
        spec = sv.get_public_spec_dict()
        spec.pop("privateSeed", None)
        sv = SpecVerifier(spec)
        return sv.as_toml_string()

    @transaction.atomic
    def get_the_spec_as_toml_with_codes(self):
        """Return the test-specification from the database.

        .. warning::
            Note this includes both the public code and the private
            seed.  If you are calling this, consider carefully whether
            you need the private seed.  At the time of writing, no one
            is calling this.
        """
        sv = SpecVerifier(self.get_the_spec())
        return sv.as_toml_string()

    @transaction.atomic
    def store_validated_spec(self, validated_spec: Dict) -> None:
        """Takes the validated test specification and stores it in the db.

        Args:
            validated_spec (dict): A dictionary containing a validated test
                specification.
        """
        spec_obj = Specification(spec_dict=validated_spec)
        spec_obj.save()

    @transaction.atomic
    def remove_spec(self) -> None:
        """Removes the test specification from the db, if possible.

        This can only be done if no tests have been created.

        Raises:
            ObjectDoesNotExist: no exam specification yet.
            MultipleObjectsReturned: cannot remove spec because
                there are already papers.
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
    def get_longname(self) -> str:
        """Get the long name of the exam.

        Exceptions:
            ObjectDoesNotExist: no exam specification yet.
        """
        spec_obj = self.get_the_spec()
        return spec_obj["longName"]

    @transaction.atomic
    def get_shortname(self) -> str:
        """Get the short name of the exam.

        Exceptions:
            ObjectDoesNotExist: no exam specification yet.
        """
        spec_obj = self.get_the_spec()
        return spec_obj["name"]

    @transaction.atomic
    def get_n_questions(self) -> int:
        """Get the number of questions in the test.

        Exceptions:
            ObjectDoesNotExist: no exam specification yet.
        """
        spec_obj = self.get_the_spec()
        return spec_obj["numberOfQuestions"]

    @transaction.atomic
    def get_n_versions(self) -> int:
        """Get the number of test versions.

        Exceptions:
            ObjectDoesNotExist: no exam specification yet.
        """
        spec_obj = self.get_the_spec()
        return spec_obj["numberOfVersions"]

    @transaction.atomic
    def get_n_pages(self) -> int:
        """Get the number of pages in the test.

        Exceptions:
            ObjectDoesNotExist: no exam specification yet.
        """
        spec_obj = self.get_the_spec()
        return spec_obj["numberOfPages"]

    @transaction.atomic
    def get_question_mark(self, question_one_index) -> int:
        """Get the max mark of a given question.

        Args:
            question_one_index (str/int): question number, indexed from 1.

        Returns:
            The maximum mark.

        Raises:
            ObjectDoesNotExist: no exam specification yet.
            KeyError: question out of range
        """
        spec_obj = self.get_the_spec()
        return spec_obj["question"][str(question_one_index)]["mark"]

    @transaction.atomic
    def n_pages_for_question(self, question_one_index) -> int:
        spec_obj = self.get_the_spec()
        pages = spec_obj["question"][str(question_one_index)]["pages"]
        return len(pages)

    @transaction.atomic
    def get_question_label(self, question_one_index) -> str:
        """Get the question label from its one-index.

        Args:
            question_one_index (str | int): question number indexed from 1.

        Returns:
            The question label.

        Raises:
            ObjectDoesNotExist: no exam specification yet.
        """
        spec_obj = self.get_the_spec()
        return spec_obj["question"][str(question_one_index)]["label"]
