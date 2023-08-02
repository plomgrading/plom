# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates

from copy import deepcopy
from rest_framework import serializers

from plom import SpecVerifier

from .models import SpecQuestion, Specification


class SpecQuestionSerializer(serializers.ModelSerializer):
    """Handle serializing questions in the test specification."""

    pages = serializers.ListField(child=serializers.IntegerField(min_value=1))
    mark = serializers.IntegerField(min_value=0)
    select = serializers.ChoiceField(choices=["fix", "shuffle"], default="fix")
    label = serializers.CharField(required=False)

    class Meta:
        model = SpecQuestion
        exclude = ["question_number"]


class SpecSerializer(serializers.ModelSerializer):
    """Handle serializing a test specification."""

    name = serializers.SlugField()
    longName = serializers.CharField()
    numberOfVersions = serializers.IntegerField(min_value=1)
    numberOfPages = serializers.IntegerField(min_value=1)
    numberOfQuestions = serializers.IntegerField(min_value=1)
    totalMarks = serializers.IntegerField(min_value=0)
    privateSeed = serializers.CharField(required=False)
    publicCode = serializers.CharField(required=False)
    idPage = serializers.IntegerField(min_value=1)
    doNotMarkPages = serializers.ListField(child=serializers.IntegerField(min_value=1))
    question = serializers.DictField(child=SpecQuestionSerializer())

    class Meta:
        model = Specification
        fields = "__all__"

    def is_valid(self, raise_exception=True):
        """Perform additional soundness checks on the test spec."""
        is_valid = super().is_valid(raise_exception=raise_exception)

        data_with_dummy_num_to_produce = {**deepcopy(self.data), "numberToProduce": -1}
        try:
            vlad = SpecVerifier(data_with_dummy_num_to_produce)
            vlad.verify()
            return True
        except ValueError as e:
            if raise_exception:
                raise e from None  # TODO: Best practice for re-raising exceptions?
            else:
                return False

    def create(self, validated_data):
        """Create a Specification instance and SpecQuestion instances."""
        questions = validated_data.pop("question")
        for idx, question in questions.items():
            question["question_number"] = int(idx)
            SpecQuestion.objects.create(**question)
        return Specification.objects.create(**validated_data)
