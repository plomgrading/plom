# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

import random
from copy import deepcopy
from rest_framework import serializers

from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from plom import SpecVerifier
from plom.tpv_utils import new_magic_code

from .models import SpecQuestion, Specification, SolnSpecification, SolnSpecQuestion


class SpecQuestionSerializer(serializers.ModelSerializer):
    """Handle serializing questions in the test specification."""

    pages = serializers.ListField(child=serializers.IntegerField(min_value=1))
    mark = serializers.IntegerField(min_value=0)
    select = serializers.ChoiceField(choices=["fix", "shuffle"], default="shuffle")
    label = serializers.CharField(required=False)

    class Meta:
        model = SpecQuestion
        exclude = ["question_number"]


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
    privateSeed = serializers.CharField(default=new_private_seed)
    publicCode = serializers.CharField(default=new_magic_code)
    idPage = serializers.IntegerField(min_value=1)
    doNotMarkPages = serializers.ListField(child=serializers.IntegerField(min_value=1))
    question = serializers.DictField(child=SpecQuestionSerializer())

    class Meta:
        model = Specification
        fields = "__all__"

    def is_valid(self, *, raise_exception: bool = True) -> bool:
        """Perform additional soundness checks on the test spec.

        Keyword Args:
            raise_exception: Default True, else just return False
                without explanation.

        Returns:
            Whether the spec is valid.

        Raises:
            ValueError: explaining what is invalid.
            ValidationError: in this case the ``.detail`` field will contain
                a list of what is wrong.
        """
        is_valid = super().is_valid(raise_exception=raise_exception)
        if not is_valid:
            return False

        data_with_dummy_num_to_produce = {**deepcopy(self.data), "numberToProduce": -1}
        try:
            vlad = SpecVerifier(data_with_dummy_num_to_produce)
            vlad.verify()
            return True
        except ValueError as e:
            if raise_exception:
                raise e from None
            return False

    @transaction.atomic
    def create(self, validated_data):
        """Create a Specification instance and SpecQuestion instances.

        If a spec instance already exists, this method overwrites the old spec.
        """
        Specification.objects.all().delete()
        SpecQuestion.objects.all().delete()

        questions = validated_data.pop("question")
        for idx, question in questions.items():
            question["question_number"] = int(idx)
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
        fields = "__all__"

    def is_valid(self, raise_exception=True):
        """Perform additional soundness checks on the test spec."""
        is_valid = super().is_valid(raise_exception=raise_exception)

        try:
            spec = Specification.objects.get()
        except ObjectDoesNotExist:
            raise ValueError("Cannot validate solution spec without a test spec")

        # check that there is a solution for each question
        if len(self.data["solution"]) != spec.numberOfQuestions:
            raise ValueError(
                "Number of solutions {len(solution)} does not match number of questions {spec.numberOfQuestions}"
            )
        # check that the solution numbers match question-numbers
        for sn in range(1, spec.numberOfQuestions + 1):
            if str(sn) not in self.data["solution"]:
                raise ValueError(f"Cannot find solution for question {sn}")
            # check that the page numbers for each solution are in range.
            for pg in self.data["solution"][f"{sn}"]["pages"]:
                if pg < 1:
                    raise ValueError(f"Page {pg} in solution {sn} is not positive")
                elif pg > self.data["numberOfPages"]:
                    raise ValueError(
                        f"Page {pg} in solution {sn} is larger than the number of pages {self.data['numberOfPages']}"
                    )
            # check that the page numbers for each soln are contiguous
            # is sufficient to check that the number of pages = max-min+1.
            min_pg = min(self.data["solution"][f"{sn}"]["pages"])
            max_pg = max(self.data["solution"][f"{sn}"]["pages"])
            if len(self.data["solution"][f"{sn}"]["pages"]) != max_pg - min_pg + 1:
                raise ValueError(
                    f"The list of pages for solution {sn} is not contiguous - {self.data['solution'][f'{sn}']['pages']}"
                )

        return True

    @transaction.atomic
    def create(self, validated_data):
        """Create a Specification instance and SpecQuestion instances.

        If a spec instance already exists, this method overwrites the old spec.
        """
        SolnSpecification.objects.all().delete()
        SolnSpecQuestion.objects.all().delete()

        solution_dict = validated_data.pop("solution")
        for idx, soln in solution_dict.items():
            soln["solution_number"] = int(idx)
            SolnSpecQuestion.objects.create(**soln)
        return SolnSpecification.objects.create(**validated_data)
