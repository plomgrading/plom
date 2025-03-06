# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024-2025 Colin B. Macdonald

import sys
from typing import Any

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib


from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from plom_server.Base.compat import load_toml_from_path
from ..models import (
    Specification,
    SolnSpecification,
    SolnSpecQuestion,
)
from ..serializers import SolnSpecSerializer
from ..services import SpecificationService


@transaction.atomic
def load_soln_spec_from_dict(
    soln_spec_dict: dict[str, Any],
) -> Specification:
    """Load a soln spec from a dictionary and save to the database.

    Will call the SolnSpecSerializer on the loaded TOML string and validate.

    Args:
        soln_spec_dict: the dictionary describing the structure of the
            solution of this assessment.

    Returns:
        Specification: saved test spec instance.
    """
    # Note: we must re-format the soln list-of-dicts into a dict-of-dicts in order to the serializer happy.
    if "solution" in soln_spec_dict.keys():
        soln_spec_dict["solution"] = soln_list_to_dict(soln_spec_dict["solution"])
    serializer = SolnSpecSerializer(data=soln_spec_dict)
    assert serializer.is_valid(), "Unexpectedly invalid serializer"

    return serializer.create(serializer.validated_data)


def load_soln_spec_from_toml(
    pathname: str,
) -> Specification:
    """Load a test spec from a TOML file and save it to the database."""
    data = load_toml_from_path(pathname)
    return load_soln_spec_from_dict(data)


def load_soln_spec_from_toml_string(toml_string: str) -> Specification:
    """Load a test spec from a TOML file and save it to the database."""
    try:
        dat = tomllib.loads(toml_string)
    except tomllib.TOMLDecodeError as err:
        raise ValueError(err)
    return load_soln_spec_from_dict(dat)


def validate_soln_spec_from_toml_string(toml_string: str) -> bool:
    """Load a test spec from a TOML file and validate it without saving."""
    try:
        soln_spec_dict = tomllib.loads(toml_string)
    except tomllib.TOMLDecodeError as err:
        raise ValueError(err)

        # Note: we must re-format the soln list-of-dicts into a dict-of-dicts in order to the serializer happy.
    if "solution" in soln_spec_dict.keys():
        soln_spec_dict["solution"] = soln_list_to_dict(soln_spec_dict["solution"])
    serializer = SolnSpecSerializer(data=soln_spec_dict)
    return serializer.is_valid()


@transaction.atomic
def is_there_a_soln_spec() -> bool:
    """Has a solution-specification been uploaded to the database."""
    return SolnSpecification.objects.count() == 1


@transaction.atomic
def get_the_soln_spec() -> dict:
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
def get_the_soln_spec_as_toml() -> str:
    """Return the soln-specification from the database as a valid toml string."""
    soln_spec = get_the_soln_spec()
    # Hack some toml... instead of using tomlkit.
    # Not ideal but allows us to put in comments
    toml_string = f"""# Solution spec for '{SpecificationService.get_longname()}'

numberOfPages = {soln_spec["numberOfPages"]}
    """
    # Now insert a comment after after each "[[solution]]"
    for n, dat in soln_spec["solution"].items():
        toml_string += f"""
# for question {int(n)}
[[solution]]
pages = {dat['pages']}
        """
    return toml_string


@transaction.atomic
def store_validated_soln_spec(validated_soln_spec: dict) -> None:
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


def n_pages_for_question(question_one_index: int) -> int:
    """Return the pages used for the solution to the given question."""
    question = SolnSpecQuestion.objects.get(question_number=question_one_index)
    return len(question.pages)


def soln_list_to_dict(solns: list[dict]) -> dict[str, dict]:
    """Convert a list of question dictionaries to a nested dict with question indices as str keys."""
    if not isinstance(solns, list):
        raise ValueError("'solution' field should be a list")
    return {str(i + 1): s for i, s in enumerate(solns)}


def get_unused_pages() -> list[int]:
    """Return a list of pages in the solution that are not used in any particular question.

    Note that the soln spec has numberOfPages, but we are not required to use all of those
    pages to generate solutions. For example, if the solution is hand-written on the
    original paper, we don't need to use the ID-page or DNM pages, even though those
    pages would be present in a source solution pdf.
    """
    # get all the used pages in a flattened list
    used_pages = [p for q in SolnSpecQuestion.objects.all() for p in q.pages]
    unused_pages = [p for p in range(1, get_n_pages() + 1) if p not in used_pages]
    return unused_pages


def get_unused_pages_in_toml_string(toml_string: str) -> list[int]:
    """As per 'get_unused_pages' except from the supplied toml string."""
    try:
        soln_spec_dict = tomllib.loads(toml_string)
    except tomllib.TOMLDecodeError as err:
        raise ValueError(err)

    used_pages = [p for s in soln_spec_dict["solution"] for p in s["pages"]]
    unused_pages = [
        p for p in range(1, soln_spec_dict["numberOfPages"] + 1) if p not in used_pages
    ]
    return unused_pages
