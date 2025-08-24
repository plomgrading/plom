# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2024 Aidan Murphy
# Copyright (C) 2024 Aden Chan

from django.db import models

from plom_server.Base.models import SingletonABCModel


class SpecQuestion(models.Model):
    """A question in the test specification.

    Fields:
        pages: a list of pages where student work for this question should be found.
        marks: the maximum marks available for this question
        select: used to control how the question is chosen when there are multiple
            versions.  ``"fix"`` means always choose version 1.  ``"shuffle"`` means
            choose randomly from all versions.  In practice, the question-version
            map can be custom-set in non-random ways.  Its not clearly defined what
            happens if the version-map in practice contradicts this setting.
            See also Issue #2261 which proposes a more general mechanism.
        label: a human identifiable label for this question, e.g. Q1, Ex1, etc.
        question_index: a one-based index, used for unambiguous access and
            to define label if label isn't specified.
    """

    pages = models.JSONField()
    mark = models.PositiveIntegerField(null=False)
    select = models.JSONField(null=True)
    label = models.TextField(null=True)
    question_index = models.PositiveIntegerField(null=False, unique=True)


class Specification(SingletonABCModel):
    """Store the json of the test specification dictionary.

    There can be at most one Specification entry.

    WET alert: for some reason, changing code here also requires changing
    the serializer as well in ``Papers/serializers.py``.  Both specify
    defaults, with no verification that those defaults match (?).  Boo,
    write everything twice :-(
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
    allowSharedPages = models.BooleanField(default=False)

    def __getattr__(self, name):
        """If querying for questions, return a dictionary of all the spec questions."""
        if name == "question":
            return self.get_question_dict()
        else:
            raise AttributeError(f"Member {name} not found in test specification.")

    def get_question_dict(self):
        """Return all the questions in the form of a dictionary, where keys are question indices.

        TODO: for some reason, the keys are strings.
        TODO: is this used?
        """
        return {str(q.question_index): q for q in SpecQuestion.objects.all()}

    def get_question_list(self):
        """Return the questions in the form of a list."""
        return list(SpecQuestion.objects.all())

    @classmethod
    def load(cls):
        """Return the singleton instance of the Specification model.

        Raises:
            Specification.DoesNotExist: If the Specification model does not exist.
        """
        return cls.objects.get(pk=1)


class SolnSpecQuestion(models.Model):
    """A solution to a question in the solution specification."""

    pages = models.JSONField()
    question_index = models.PositiveIntegerField(null=False, unique=True)


class SolnSpecification(SingletonABCModel):
    """Store the json of the solution specification dictionary.

    Note that
      * There can be at most one SolutionSpecification entry
      * The number of versions is given by the test spec - so not in soln spec
      * The number of questions is given by test spec - so not in soln spec

    numberOfPages (int): The number of pages in the solution.
    """

    numberOfPages = models.PositiveIntegerField(null=False)

    def __getattr__(self, name):
        """If querying for solution, return a dictionary of all the soln-spec solutions."""
        if name == "solution":
            return self.get_solution_dict()
        else:
            raise AttributeError(f"Member {name} not found in solution Specification.")

    def get_solution_dict(self):
        """Return all the solution questions in the form of a dictionary, where keys are str question indices."""
        return {str(s.question_index): s for s in SolnSpecQuestion.objects.all()}

    def get_soltion_list(self):
        """Return the solution questions in the form of a list."""
        return list(SolnSpecQuestion.objects.all())

    @classmethod
    def load(cls):
        """Return the singleton instance of the SolnSpecification model.

        Raises:
            SolnSpecification.DoesNotExist: If the Solm=nSpecification model
                does not exist.
        """
        return cls.objects.get(pk=1)
