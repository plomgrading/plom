# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Andrew Rechnitzer
# Copyright (C) 2022 Edith Coates
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


class Specification(SingletonBaseModel):
    """Store the json of the test specification dictionary.

    There can be at most one Specification entry

    spec_dict (json): The json'd test specification dictionary.
    """

    spec_dict = models.JSONField()


class SolutionSpecification(SingletonBaseModel):
    """Store the json of the solution specification dictionary.

    There can be at most one SolutionSpecification entry

    spec_dict (json): The json'd solution specification dictionary.
    """

    spec_dict = models.JSONField()
