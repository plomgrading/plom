# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2025 Aidan Murphy

import random
from copy import deepcopy

from rest_framework import serializers

from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from plom.spec_verifier import SpecVerifier

from .models import SpecQuestion, Specification, SolnSpecification, SolnSpecQuestion


class SpecQuestionSerializer(serializers.ModelSerializer):
    """Handle serializing questions in the test specification."""

    pages = serializers.ListField(child=serializers.IntegerField(min_value=1))
    mark = serializers.IntegerField(min_value=0)
    label = serializers.CharField(required=False)

    class Meta:
        model = SpecQuestion
        exclude = ["question_index"]


def new_private_seed() -> str:
    """Generate a random seed for a specification."""
    return str(random.randrange(0, 10**16)).zfill(16)


class SpecSerializer(serializers.ModelSerializer):
    """Handle serializing a test specification."""

    name = serializers.SlugField()
    longName = serializers.CharField()
    numberOfVersions = serializers.IntegerField(min_value=1)
    numberOfPages = serializers.IntegerField(min_value=1)
    numberOfQuestions = serializers.IntegerField(min_value=1)
    totalMarks = serializers.IntegerField(min_value=0)
    # TODO: is Seed used?  consider removing from the Specification
    privateSeed = serializers.CharField(default=new_private_seed)
    idPage = serializers.IntegerField(min_value=1)
    doNotMarkPages = serializers.ListField(child=serializers.IntegerField(min_value=1))
    question = serializers.DictField(child=SpecQuestionSerializer())
    allowSharedPages = serializers.BooleanField(default=False)

    class Meta:
        model = Specification
        fields = "__all__"

    def is_valid(self, *, raise_exception: bool = True) -> bool:
        """Perform additional soundness checks on the test spec.

        This isn't a custom thing we added: its part of the superclass
        ``serializers.ModelSerializer`` which comes from the DRF, not
        basic Django.

        Keyword Args:
            raise_exception: Default True, else just return False
                without explanation.  TODO: think this might be a bit
                non-standard viz the superclass.  For example, when
                False, probably errors should be set in .errors?
                See also, that we raise ValueErrors.

        Returns:
            Whether the spec is valid.

        Raises:
            ValueError: explaining what is invalid.
                TODO: maybe these should be re-raised as serializers.ValidationErrors
            serializers.ValidationError: in this case the ``.detail``
                field will contain a list of what is wrong.
        """
        if not super().is_valid(raise_exception=raise_exception):
            return False

        data_with_dummy_num_to_produce = {**deepcopy(self.data), "numberToProduce": -1}
        try:
            vlad = SpecVerifier(data_with_dummy_num_to_produce)
            vlad.verify(_legacy=False)
        except ValueError as e:
            if raise_exception:
                raise e from e
                # raise serializers.ValidationError(e) from e
            return False
        return True

    @transaction.atomic
    def create(self, validated_data) -> Specification:
        """Create a Specification instance and SpecQuestion instances.

        If a spec instance already exists, this method overwrites the old spec.
        """
        Specification.objects.all().delete()
        SpecQuestion.objects.all().delete()

        questions = validated_data.pop("question")
        # TODO: the fields aren't directly validated
        for idx, question in questions.items():
            question["question_index"] = int(idx)
            if isinstance(question.get("select", None), int):
                question["select"] = [question["select"]]
            SpecQuestion.objects.create(**question)
        return Specification.objects.create(**validated_data)


class SolnSpecQuestionSerializer(serializers.ModelSerializer):
    """Handle serializing question-solutions in the soln specification."""

    pages = serializers.ListField(
        child=serializers.IntegerField(min_value=1), allow_empty=False, min_length=1
    )

    class Meta:
        model = SolnSpecQuestion
        fields = ["pages"]


class SolnSpecSerializer(serializers.ModelSerializer):
    """Handle serializing a solution specification."""

    numberOfPages = serializers.IntegerField(min_value=1)
    solution = serializers.DictField(child=SolnSpecQuestionSerializer())

    class Meta:
        model = SolnSpecification
        fields = ["numberOfPages", "solution"]

    def is_valid(self, raise_exception=True):
        """Perform additional soundness checks on the solution spec."""
        super().is_valid(raise_exception=raise_exception)

        try:
            spec = Specification.objects.get()
        except ObjectDoesNotExist:
            raise ValueError("Cannot validate solution spec without a test spec")

        # check that there is a solution for each question
        if len(self.data["solution"]) != spec.numberOfQuestions:
            raise ValueError(
                f"Number of solutions {len(self.data['solution'])} does not match "
                f"number of questions {spec.numberOfQuestions}"
            )
        # check that we have a solution for each question and vice versa
        for qi in range(1, spec.numberOfQuestions + 1):
            if str(qi) not in self.data["solution"]:
                raise ValueError(f"Cannot find solution for question {qi}")
            # check that the page numbers for each solution are in range.
            for pg in self.data["solution"][f"{qi}"]["pages"]:
                if pg < 1:
                    raise ValueError(f"Page {pg} in solution {qi} is not positive")
                elif pg > self.data["numberOfPages"]:
                    raise ValueError(
                        f"Page {pg} in solution {qi} is larger than "
                        f"the number of pages {self.data['numberOfPages']}"
                    )
            # check that the page numbers for each soln are contiguous
            # is sufficient to check that the number of pages = max-min+1.
            min_pg = min(self.data["solution"][f"{qi}"]["pages"])
            max_pg = max(self.data["solution"][f"{qi}"]["pages"])
            if len(self.data["solution"][f"{qi}"]["pages"]) != max_pg - min_pg + 1:
                raise ValueError(
                    f"The list of pages for solution {qi} is not contiguous "
                    f"- {self.data['solution'][f'{qi}']['pages']}"
                )

        return True

    @transaction.atomic
    def create(self, validated_data) -> SolnSpecification:
        """Create a Specification instance and SpecQuestion instances.

        If a spec instance already exists, this method overwrites the old spec.
        """
        SolnSpecification.objects.all().delete()
        SolnSpecQuestion.objects.all().delete()

        solution_dict = validated_data.pop("solution")
        for idx, soln in solution_dict.items():
            soln["question_index"] = int(idx)
            SolnSpecQuestion.objects.create(**soln)
        return SolnSpecification.objects.create(**validated_data)
