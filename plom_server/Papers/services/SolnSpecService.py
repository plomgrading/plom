# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from copy import deepcopy
import tomlkit

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.utils.text import slugify
from django.db import transaction
from django.db.models import Max

from plom import SpecVerifier

from Base.compat import load_toml_from_path
from ..models import (
    Specification,
    SpecQuestion,
    SolnSpecification,
    SolnSpecQuestion,
)
from ..serializers import SpecSerializer, SolnSpecSerializer

# TODO - build similar for solution specs
# NOTE - this does not **validate** test specs, it assumes the spec is valid


log = logging.getLogger("ValidatedSpecService")


@transaction.atomic
def load_soln_spec_from_dict(
    soln_spec_dict: Dict[str, Any],
) -> Specification:
    """Load a soln spec from a dictionary and save to the database.

    Will call the SolnSpecSerializer on the loaded TOML string and validate.

    Args:
        soln_spec_dict:

    Returns:
        Specification: saved test spec instance.
    """
    # Note: we must re-format the soln list-of-dicts into a dict-of-dicts in order to the serializer happy.
    if "solution" in soln_spec_dict.keys():
        soln_spec_dict["solution"] = soln_list_to_dict(soln_spec_dict["solution"])
    serializer = SolnSpecSerializer(data=soln_spec_dict)
    serializer.is_valid()

    return serializer.create(serializer.validated_data)


@transaction.atomic
def load_soln_spec_from_toml(
    pathname,
) -> Specification:
    """Load a test spec from a TOML file and save it to the database."""
    data = load_toml_from_path(pathname)
    return load_soln_spec_from_dict(data)


@transaction.atomic
def is_there_a_soln_spec() -> bool:
    """Has a solution-specification been uploaded to the database."""
    return SolnSpecification.objects.count() == 1


@transaction.atomic
def get_the_soln_spec() -> Dict:
    """Return the solution-specification from the database.

    Returns:
        The solution specification as a dictionary.

    Exceptions:
        ObjectDoesNotExist: no solution specification yet.
    """
    try:
        soln_spec = SolnSpecification.objects.get()
        serializer = SolnSpecSerializer(
            soln_spec, context={"solution": SolnSpecQuestion.objects.all()}
        )
        return serializer.data
    except SolnSpecification.DoesNotExist:
        raise ObjectDoesNotExist(
            "The database does not contain a solution specification."
        )


@transaction.atomic
def get_the_soln_spec_as_toml():
    """Return the soln-specification from the database."""
    soln_spec = get_the_soln_spec()
    # TODO bit yuck, we hack solutions back to a list before saving
    fixed_spec = {
        "numberOfPages": soln_spec["numberOfPages"],
        "solution": [dat for n, dat in soln_spec["solution"].items()],
    }
    return tomlkit.dumps(fixed_spec)


@transaction.atomic
def store_validated_soln_spec(validated_soln_spec: Dict) -> None:
    """Takes the validated solution specification and stores it in the db.

    Args:
        validated_soln_spec: A dictionary containing a validated solution
            specification.
    """
    serializer = SolnSpecSerializer()
    serializer.create(validated_soln_spec)


@transaction.atomic
def remove_soln_spec() -> None:
    """Removes the solution specification from the db, if possible.

    Raises:
        ObjectDoesNotExist: no solution specification yet.
    """
    if not is_there_a_soln_spec():
        raise ObjectDoesNotExist(
            "The database does not contain a solution specification."
        )

    SolnSpecification.objects.all().delete()


def get_n_pages() -> int:
    """Get the number of pages in the solutions.

    Exceptions:
        ObjectDoesNotExist: no solution specification yet.
    """
    soln_spec = SolnSpecification.objects.get()
    return soln_spec.numberOfPages


def n_pages_for_question(question_one_index) -> int:
    question = SolnSpecQuestion.objects.get(question_number=question_one_index)
    return len(question.pages)


def soln_list_to_dict(solns: list[Dict]) -> Dict[str, Dict]:
    """Convert a list of question dictionaries to a nested dict with question numbers as keys."""
    return {str(i + 1): s for i, s in enumerate(solns)}


def get_unused_pages():
    # get all the used pages in a flattened list
    used_pages = [p for q in SolnSpecQuestion.objects.all() for p in q.pages]
    unused_pages = [p for p in range(1, get_n_pages() + 1) if p not in used_pages]
    return unused_pages
