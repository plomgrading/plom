# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2024 Colin B. Macdonald
# Copyright (C) 2022 Brennen Chiu

from __future__ import annotations

from copy import deepcopy
import html
import logging
from typing import Any, Optional, Tuple

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.utils.text import slugify
from django.db import transaction
from django.db.models import Max

from plom import SpecVerifier

from Base.compat import load_toml_from_path
from ..models import Specification, SpecQuestion
from ..serializers import SpecSerializer

# TODO - build similar for solution specs
# NOTE - this does not **validate** test specs, it assumes the spec is valid


log = logging.getLogger("ValidatedSpecService")


def validate_spec_from_dict(spec_dict: dict[str, Any]) -> bool:
    """Load a test spec from a dictionary and validate it.

    Will call the SpecSerializer on the proposed spec dict and validate.

    Args:
        spec_dict: a dictionary of the proposed spec.

    Returns:
        True if the spec seems valid.

    Raises:
        ValueError: explaining what is invalid.
        ValidationError: in this case the ``.detail`` field will contain
            a list of what is wrong.
    """
    # Note: we must re-format the question list-of-dicts into a dict-of-dicts in order to make SpecVerifier happy.
    # Also, this function does not care if there are no questions in the spec dictionary. It assumes
    # the serializer/SpecVerifier will catch it.
    if "question" in spec_dict.keys():
        spec_dict["question"] = question_list_to_dict(spec_dict["question"])
    serializer = SpecSerializer(data=spec_dict)
    return serializer.is_valid()


@transaction.atomic
def load_spec_from_dict(
    spec_dict: dict[str, Any],
    *,
    public_code: Optional[str] = None,
) -> Specification:
    """Load a test spec from a dictionary and save to the database.

    Will call the SpecSerializer on the loaded TOML string and validate.

    Args:
        spec_dict:

    Keyword Args:
        public_code: optionally pass a manually specified public code (mainly for unit testing)

    Returns:
        Specification: saved test spec instance.
    """
    # Note: we must re-format the question list-of-dicts into a dict-of-dicts in order to make SpecVerifier happy.
    # Also, this function does not care if there are no questions in the spec dictionary. It assumes
    # the serializer/SpecVerifier will catch it.
    if "question" in spec_dict.keys():
        spec_dict["question"] = question_list_to_dict(spec_dict["question"])
    serializer = SpecSerializer(data=spec_dict)
    serializer.is_valid()
    valid_data = serializer.validated_data

    if public_code:
        valid_data["publicCode"] = public_code

    return serializer.create(serializer.validated_data)


@transaction.atomic
def load_spec_from_toml(
    pathname,
    public_code=None,
) -> Specification:
    """Load a test spec from a TOML file and save it to the database."""
    data = load_toml_from_path(pathname)
    return load_spec_from_dict(data, public_code=public_code)


@transaction.atomic
def is_there_a_spec() -> bool:
    """Has a test-specification been uploaded to the database."""
    return Specification.objects.count() == 1


@transaction.atomic
def get_the_spec() -> dict:
    """Return the test-specification from the database.

    Returns:
        The exam specification as a dictionary.

    Exceptions:
        ObjectDoesNotExist: no exam specification yet.
    """
    try:
        spec = Specification.objects.get()
        serializer = SpecSerializer(
            spec, context={"question": SpecQuestion.objects.all()}
        )
        return serializer.data
    except Specification.DoesNotExist:
        raise ObjectDoesNotExist("The database does not contain a test specification.")


@transaction.atomic
def get_the_spec_as_toml():
    """Return the test-specification from the database.

    If present, remove the private seed.  But the public code
    is included (if present).
    """
    spec = get_the_spec()
    spec.pop("id", None)
    spec.pop("privateSeed", None)

    for idx, question in spec["question"].items():
        for key, val in deepcopy(question).items():
            if val is None or key == "id":
                question.pop(key, None)

    sv = SpecVerifier(spec)
    return sv.as_toml_string()


@transaction.atomic
def get_private_seed() -> str:
    """Return the private seed."""
    spec = Specification.objects.get()
    return spec.privateSeed


@transaction.atomic
def get_the_spec_as_toml_with_codes():
    """Return the test-specification from the database.

    .. warning::
        Note this includes both the public code and the private
        seed.  If you are calling this, consider carefully whether
        you need the private seed.  At the time of writing, no one
        is calling this.
    """
    spec = get_the_spec()

    for idx, question in spec["question"].items():
        for key, val in deepcopy(question).items():
            if val is None or key == "id":
                question.pop(key, None)

    sv = SpecVerifier(spec)
    return sv.as_toml_string()


@transaction.atomic
def store_validated_spec(validated_spec: dict) -> None:
    """Takes the validated test specification and stores it in the db.

    Args:
        validated_spec: A dictionary containing a validated test
            specification.
    """
    serializer = SpecSerializer()
    serializer.create(validated_spec)


@transaction.atomic
def remove_spec() -> None:
    """Removes the test specification from the db, if possible.

    This can only be done if no tests have been created.

    Raises:
        ObjectDoesNotExist: no exam specification yet.
        MultipleObjectsReturned: cannot remove spec because
            there are already papers.
    """
    if not is_there_a_spec():
        raise ObjectDoesNotExist("The database does not contain a test specification.")

    from .paper_info import PaperInfoService

    if PaperInfoService().is_paper_database_populated():
        raise MultipleObjectsReturned("Database is already populated with test-papers.")

    Specification.objects.filter().delete()


@transaction.atomic
def get_longname() -> str:
    """Get the long name of the exam.

    Exceptions:
        ObjectDoesNotExist: no exam specification yet.
    """
    spec = Specification.objects.get()
    return spec.longName


@transaction.atomic
def get_shortname() -> str:
    """Get the short name of the exam.

    Exceptions:
        ObjectDoesNotExist: no exam specification yet.
    """
    spec = Specification.objects.get()
    return spec.name


@transaction.atomic
def get_short_name_slug() -> str:
    """Get the short name of the exam, slugified.

    Exceptions:
        ObjectDoesNotExist: no exam specification yet.
    """
    return slugify(get_shortname())


@transaction.atomic
def get_n_questions() -> int:
    """Get the number of questions in the test.

    Exceptions:
        ObjectDoesNotExist: no exam specification yet.
    """
    spec = Specification.objects.get()
    return spec.numberOfQuestions


@transaction.atomic
def get_n_versions() -> int:
    """Get the number of test versions.

    Exceptions:
        ObjectDoesNotExist: no exam specification yet.
    """
    spec = Specification.objects.get()
    return spec.numberOfVersions


@transaction.atomic
def get_n_pages() -> int:
    """Get the number of pages in the test.

    Exceptions:
        ObjectDoesNotExist: no exam specification yet.
    """
    spec = Specification.objects.get()
    return spec.numberOfPages


@transaction.atomic
def get_question_mark(question_one_index: str | int) -> int:
    """Get the max mark of a given question.

    Args:
        question_one_index: question index, indexed from 1.

    Returns:
        The maximum mark.

    Raises:
        ObjectDoesNotExist: no question exists with the given index.
    """
    question = SpecQuestion.objects.get(question_number=question_one_index)
    return question.mark


@transaction.atomic
def get_max_all_question_mark() -> int:
    """Get the maximum mark of all questions."""
    # the aggregate function returns dict {"mark__max": n}
    return SpecQuestion.objects.all().aggregate(Max("mark"))["mark__max"]


@transaction.atomic
def get_total_marks() -> int:
    """Get the total maximum possible mark (over all questions).

    Returns:
        The maximum mark.
    """
    spec = Specification.objects.get()
    return spec.totalMarks


@transaction.atomic
def n_pages_for_question(question_one_index) -> int:
    question = SpecQuestion.objects.get(question_number=question_one_index)
    return len(question.pages)


@transaction.atomic
def get_question_label(question_one_index: str | int) -> str:
    """Get the question label from its one-index.

    Args:
        question_one_index: question number indexed from 1.
            TODO: does it really accept string input?

    Returns:
        The question label, including a default value if a
        custom question label was not used.

    Raises:
        ObjectDoesNotExist: no question exists with the given index.
    """
    question = SpecQuestion.objects.get(question_number=question_one_index)
    if question.label is None:
        return f"Q{question_one_index}"
    return question.label


def get_question_index_label_pairs() -> list[Tuple[int, str]]:
    """Get the question indices and labels as a list of pairs of tuples.

    Returns:
        The question indices and labels as pairs of tuples in a list.
        The pairs are ordered by their indices.
    """
    return [(i, get_question_label(i)) for i in range(1, get_n_questions() + 1)]


def get_question_labels() -> list[str]:
    """Get the question labels in a list.

    Returns:
        The question labels in a list, in the order of
        increasing question index.
    """
    return [label for _, label in get_question_index_label_pairs()]


def get_question_labels_map() -> dict[int, str]:
    """Get the question labels as a mapping from unit-indexed question indices.

    Returns:
        The question labels as a dictionary mapping from unit-indexed
        question indices.
    """
    return {i: label for i, label in get_question_index_label_pairs()}


def get_question_html_label_triples() -> list[Tuple[int, str, str]]:
    """Get the question indices, string labels and fancy HTML labels as a list of triples."""
    return [
        (i, get_question_label(i), render_html_question_label(i))
        for i in range(1, get_n_questions() + 1)
    ]


def question_list_to_dict(questions: list[dict]) -> dict[str, dict]:
    """Convert a list of question dictionaries to a nested dict with question numbers as keys."""
    return {str(i + 1): q for i, q in enumerate(questions)}


def render_html_question_label(qidx: int) -> str:
    """HTML rendering of the question label for a particular question index."""
    qlabel = get_question_label(qidx)
    qlabel = html.escape(qlabel)
    if qlabel == f"Q{qidx}":
        return qlabel
    else:
        return f'<abbr title="question index {qidx}">{qlabel}</abbr>'


def render_html_flat_question_label_list(qindices: list[int] | None) -> str:
    """HTML code for rendering a specified list of question labels.

    If the list is empty or the special value ``None``, then return the
    string ``"None"``.
    """
    if not qindices:
        return "None"
    return ", ".join(render_html_question_label(qidx) for qidx in qindices)
