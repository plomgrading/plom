# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

from django.db import models

from Base.models import SingletonBaseModel

# ---------------------------------
# Define a singleton model as per
# https://steelkiwi.com/blog/practical-application-singleton-design-pattern/
#
# Then use this to define tables for TestSpecification
# and SolutionSpecification
# ---------------------------------


# class SingletonBaseModel(models.Model):
#     """We define a singleton models for the test-specification. This
#     abstract model ensures that any derived models have at most a single
#     row."""

#     class Meta:
#         abstract = True

#     def save(self, *args, **kwargs):
#         self.pk = 1
#         super().save(*args, **kwargs)

#     def delete(self, *args, **kwargs):
#         pass

#     @classmethod
#     def load(cls):
#         obj, created = cls.objects.get_or_create(pk=1)
#         return obj


class SpecQuestion(models.Model):
    """A question in the test specification."""

    pages = models.JSONField()
    mark = models.PositiveIntegerField(null=False)
    select = models.CharField(
        choices=[("fix", "fix"), ("shuffle", "shuffle")],
        default="shuffle",
        max_length=7,  # length of the string "shuffle"
    )
    label = models.TextField(null=True)
    question_number = models.PositiveIntegerField(null=False, unique=True)


class Specification(SingletonBaseModel):
    """Store the json of the test specification dictionary.

    There can be at most one Specification entry.
    """

    name = models.TextField(null=False)
    longName = models.TextField(null=False)
    numberOfVersions = models.PositiveIntegerField(null=False)
    numberOfPages = models.PositiveIntegerField(null=False)
    numberOfQuestions = models.PositiveIntegerField(null=False)
    totalMarks = models.PositiveIntegerField(null=False)
    privateSeed = models.TextField()
    publicCode = models.TextField()
    idPage = models.PositiveIntegerField()
    doNotMarkPages = models.JSONField()

    def __getattr__(self, name):
        """If querying for questions, return a dictionary of all the spec questions."""
        if name == "question":
            return self.get_question_dict()
        else:
            raise AttributeError(f"Member {name} not found in test specification.")

    def get_question_dict(self):
        """Return all the questions in the form of a dictionary, where keys are question numbers."""
        return {str(q.question_number): q for q in SpecQuestion.objects.all()}

    def get_question_list(self):
        """Return the questions in the form of a list."""
        return list(SpecQuestion.objects.all())


class SolutionSpecification(SingletonBaseModel):
    """Store the json of the solution specification dictionary.

    There can be at most one SolutionSpecification entry

    spec_dict (json): The json'd solution specification dictionary.
    """

    spec_dict = models.JSONField()
