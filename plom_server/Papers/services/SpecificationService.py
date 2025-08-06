# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2025 Colin B. Macdonald
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2024 Aden Chan
# Copyright (C) 2025 Philip D. Loewen

import html
import logging
from copy import deepcopy
from pathlib import Path
from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.utils.text import slugify
from django.db import transaction
from django.db.models import Max

from plom.spec_verifier import SpecVerifier

from plom_server.Base.compat import load_toml_from_path, load_toml_from_string
from plom_server.Base.compat import TOMLDecodeError  # noqa: F401
from ..models import Specification, SpecQuestion
from ..serializers import SpecSerializer
from plom_server.Preparation.services.preparation_dependency_service import (
    assert_can_modify_spec,
)
from plom_server.Papers.models import MobilePage

log = logging.getLogger("SpecificationService")


def validate_spec_from_dict(spec_dict: dict[str, Any]) -> bool:
    """Validate an assessment specification (as a dict), but don't install it on server.

    Will call the SpecSerializer on the proposed spec dict and validate.

    Args:
        spec_dict: a dictionary of the proposed spec.

    Returns:
        True if the spec serializes correctly

    Raises:
        ValueError: explaining what is invalid.
        serializers.ValidationError: in this case the ``.detail`` field
            will contain a list of what is wrong.
    """
    spec_dict = deepcopy(spec_dict)  # Defend input dict from changes

    # Note: we must re-format the question list-of-dicts into a dict-of-dicts in order to make SpecVerifier happy.
    # Also, this function does not care if there are no questions in the spec dictionary. It assumes
    # the serializer/SpecVerifier will catch it.
    if "question" in spec_dict.keys():
        spec_dict["question"] = question_list_to_dict(spec_dict["question"])
    serializer = SpecSerializer(data=spec_dict)
    return serializer.is_valid(raise_exception=True)


def validate_spec_from_string(spec_toml_str: str) -> bool:
    """Validate an assessment specification (from a toml format string), but don't install it on server.

    Raises:
        TOMLDecodeError: cannot get toml from the string.
        ValueError: explaining what is invalid.
        serializers.ValidationError: in this case the ``.detail`` field
            will contain a list of what is wrong.
    """
    spec_dict = load_toml_from_string(spec_toml_str)
    return validate_spec_from_dict(spec_dict)


@transaction.atomic
def install_spec_from_dict(
    spec_dict: dict[str, Any],
    *,
    force_public_code: bool = False,
) -> Specification:
    """Load a test spec from a dictionary and save to the database.

    Will call the SpecSerializer on the loaded TOML string and validate.

    Args:
        spec_dict: the dictionary describing the assessment.

    Keyword Args:
        force_public_code: Usually you may not include "publicCode" in
            the specification.  Pass True to allow overriding that default.

    Returns:
        The Specification that was just saved.

    Raises:
        PlomDependencyConflict: if the spec cannot be modified.
        ValueError: existing public code, and other cases.  Currently
            a bit unclear which cases give ValueErrors and which give
            the following serializers.ValidationErrors.  Callers should
            check for both.
        serializers.ValidationError: with more info in the ``.details``.
    """
    # this will Raise a PlomDependencyConflict if cannot modify the spec
    assert_can_modify_spec()

    spec_dict = deepcopy(spec_dict)  # Defend input dict from changes

    # Note: the serializer makes these codes so it seems too late the ask it there
    existing_publicCode = spec_dict.get("publicCode", None)
    if existing_publicCode and not force_public_code:
        # raise serializers.ValidationError(...)?
        raise ValueError("Not allowed to specify a publicCode directly")

    # Note: we must re-format the question list-of-dicts into a dict-of-dicts in order to make SpecVerifier happy.
    # Also, this function does not care if there are no questions in the spec dictionary. It assumes
    # the serializer/SpecVerifier will catch it.
    if "question" in spec_dict.keys():
        spec_dict["question"] = question_list_to_dict(spec_dict["question"])

    serializer = SpecSerializer(data=spec_dict)

    # This raises both serializers.ValidationErrors and ValueErrors
    # TODO: the raising of ValueErrors appears non-standard, consider refactor
    serializer.is_valid(raise_exception=True)

    valid_data = serializer.validated_data

    return serializer.create(valid_data)


def install_spec_from_toml_file(
    pathname: str | Path,
    *,
    force_public_code: bool = False,
) -> Specification:
    """Load a specification from a TOML file and save it to the database.

    Args:
        pathname: what file to load from.

    Keyword Args:
        force_public_code: Usually you may not include "publicCode" in
            the specification.  Pass True to allow overriding that default.

    Raises:
        TOMLDecodeError: cannot read toml.
        PlomDependencyConflict: if the spec cannot be modified.
        ValueError: see :func:`install_spec_from_dict`.
        serializers.ValidationError: see :func:`install_spec_from_dict`.
    """
    data = load_toml_from_path(pathname)
    return install_spec_from_dict(data, force_public_code=force_public_code)


def install_spec_from_toml_string(
    tomlstr: str,
    *,
    force_public_code: bool = False,
) -> Specification:
    """Load a specification from a string in TOML format and save it to the database.

    Args:
        tomlstr: a string containing toml.

    Keyword Args:
        force_public_code: Usually you may not include "publicCode" in
            the specification.  Pass True to allow overriding that default.

    Raises:
        TOMLDecodeError: cannot read toml.
        PlomDependencyConflict: if the spec cannot be modified.
        ValueError: see :func:`install_spec_from_dict`.
        serializers.ValidationError: see :func:`install_spec_from_dict`.
    """
    data = load_toml_from_string(tomlstr)
    return install_spec_from_dict(data, force_public_code=force_public_code)


def is_there_a_spec() -> bool:
    """Has a test-specification been uploaded to the database."""
    return Specification.objects.count() == 1


@transaction.atomic
def get_the_spec() -> dict:
    """Return the assessment specification from the database.

    Returns:
        The assessment specification as a dictionary.

    Exceptions:
        ObjectDoesNotExist: no specification yet.
    """
    try:
        spec = Specification.objects.get()
        serializer = SpecSerializer(
            spec, context={"question": SpecQuestion.objects.all()}
        )
        return serializer.data
    except Specification.DoesNotExist:
        raise ObjectDoesNotExist("The database does not contain a test specification.")


def get_the_spec_as_toml(
    *, include_public_code: bool = False, _include_private_seed: bool = False
) -> str:
    """Return the test-specification from the database.

    Generally, the public code and the private seed are removed (hidden
    from the return) but this can be changed with keyword arguments.

    Keyword Args:
        include_public_code: if True, include the current public code.
        _include_private_seed: if True, include the current private seed
            (currently unused, except maybe in testing?)

    Exceptions:
        ObjectDoesNotExist: no exam specification yet.
    """
    spec = get_the_spec()
    spec.pop("id", None)
    if not _include_private_seed:
        spec.pop("privateSeed", None)
    if not include_public_code:
        spec.pop("publicCode")

    for idx, question in spec["question"].items():
        for key, val in deepcopy(question).items():
            if val is None or key == "id":
                question.pop(key, None)

    sv = SpecVerifier(spec)
    return sv.as_toml_string(_legacy=False)


@transaction.atomic
def get_private_seed() -> str:
    """Return the private seed."""
    spec = Specification.objects.get()
    return spec.privateSeed


def _store_validated_spec(validated_spec: dict) -> None:
    """Takes the validated test specification and stores it in the db.

    Note this is used in unit testing but otherwise has no callers as
    of April 2025.  Instead, consider :func:`install_spec_from_dict` or
    the helpers :func:`install_spec_from_toml_file` and
    :func:`install_spec_from_toml_string`.

    Args:
        validated_spec: A dictionary containing a validated test
            specification.
    """
    serializer = SpecSerializer()
    serializer.create(validated_spec)


def remove_spec() -> None:
    """Removes the specification from the db, if possible.

    This can only be done if no tests have been created.

    Raises:
        ObjectDoesNotExist: no exam specification yet.
        PlomDependencyConflict: cannot modify spec due to dependencies (eg sources uploaded, papers in database, etc)
    """
    if not is_there_a_spec():
        raise ObjectDoesNotExist("The database does not contain a specification.")

    assert_can_modify_spec()
    with transaction.atomic():
        Specification.objects.all().delete()
        SpecQuestion.objects.all().delete()


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
def get_short_and_long_names_or_empty() -> tuple[str, str]:
    """Get the long and short names of the exam, or return empty strings."""
    try:
        spec = Specification.objects.get()
        return (spec.name, spec.longName)
    except ObjectDoesNotExist:
        return ("", "")


@transaction.atomic
def get_short_name_slug() -> str:
    """Get the short name of the exam, slugified.

    Exceptions:
        ObjectDoesNotExist: no exam specification yet.
    """
    return slugify(get_shortname())


@transaction.atomic
def get_id_page_number() -> int:
    """Get the page number of the ID page.

    Exceptions:
        ObjectDoesNotExist: no exam specification yet.
    """
    spec = Specification.objects.get()
    return spec.idPage


@transaction.atomic
def get_dnm_pages() -> list[int]:
    """Get the list of do-no-mark page numbers.

    Exceptions:
        ObjectDoesNotExist: no exam specification yet.
    """
    spec = Specification.objects.get()
    return spec.doNotMarkPages


@transaction.atomic
def get_question_pages() -> dict[int, list[int]]:
    """Get the pages of each question, indexed from one.

    Returns:
        A dictionary of question indices giving a list of the corresponding pages {question_index: question_pages}.
    Exceptions:
        ObjectDoesNotExist: no exam specification yet.
    """
    # check if there is a spec, else raise an exception
    _ = Specification.objects.get()
    question_pages = {
        q_obj.question_index: q_obj.pages for q_obj in SpecQuestion.objects.all()
    }
    return question_pages


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


def get_list_of_versions() -> list[int]:
    """Get a list of the versions.

    If there is no spec, an empty list.
    """
    # get n versions throws an ObjectDoesNotExist when no spec
    try:
        return [v + 1 for v in range(get_n_versions())]
    except ObjectDoesNotExist:
        return []


def get_question_indices() -> list[int]:
    """Get a list of the question indices.

    Question indices start at one, not zero.

    If there is no spec, return an empty list.
    """
    # get n questions throws an ObjectDoesNotExist when no spec
    try:
        return [n + 1 for n in range(get_n_questions())]
    except ObjectDoesNotExist:
        return []


@transaction.atomic
def get_n_pages() -> int:
    """Get the number of pages in the test.

    Exceptions:
        ObjectDoesNotExist: no exam specification yet.
    """
    spec = Specification.objects.get()
    return spec.numberOfPages


def get_list_of_pages() -> list[int]:
    """Get a list of the pages.

    If there is no spec, an empty list.
    """
    if not is_there_a_spec():
        return []
    return [p + 1 for p in range(get_n_pages())]


@transaction.atomic
def get_question_max_mark(question_index: str | int) -> int:
    """Get the max mark of a given question.

    Args:
        question_index: question index, indexed from 1.
            TODO: is str really allowed/encouraged?

    Returns:
        The maximum mark.

    Raises:
        ObjectDoesNotExist: no question exists with the given index.
    """
    question = SpecQuestion.objects.get(question_index=question_index)
    return question.mark


# Some code uses this older synonym but it confuses me without the word "max"
get_question_mark = get_question_max_mark


@transaction.atomic
def get_questions_max_marks() -> dict[int, int]:
    """Get the maximum marks of all questions.

    Returns:
        A dictionary of question indices giving the corresponding maximum marks.
    """
    return {q.question_index: q.mark for q in SpecQuestion.objects.all()}


@transaction.atomic
def get_max_all_question_mark() -> int:
    """Get the maximum mark of all questions, or None if no questions."""
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
def n_pages_for_question(question_index) -> int:
    question = SpecQuestion.objects.get(question_index=question_index)
    return len(question.pages)


@transaction.atomic
def get_question_label(question_index: str | int) -> str:
    """Get the question label from its one-index.

    Args:
        question_index: question indexed from 1.
            TODO: does it really accept string input?

    Returns:
        The question label, including a default value if a
        custom question label was not used.

    Raises:
        ObjectDoesNotExist: no question exists with the given index.
    """
    question = SpecQuestion.objects.get(question_index=question_index)
    if question.label is None:
        return f"Q{question_index}"
    return question.label


def get_question_index_label_pairs() -> list[tuple[int, str]]:
    """Get the question indices and labels as a list of pairs of tuples.

    Returns:
        The question indices and labels as pairs of tuples in a list.
        The pairs are ordered by their indices.
    """
    questions = SpecQuestion.objects.all().order_by("question_index")
    lst = []
    for q in questions:
        qidx = q.question_index
        label = q.label
        if label is None:
            label = f"Q{qidx}"
        lst.append((qidx, label))
    return lst


def get_question_html_label_triples() -> list[tuple[int, str, str]]:
    """Get the question indices, string labels and fancy HTML labels as a list of triples."""
    questions = SpecQuestion.objects.all().order_by("question_index")
    lst = []
    for q in questions:
        qidx = q.question_index
        label = q.label
        if label is None:
            label = f"Q{qidx}"
        lst.append((qidx, label, _render_html_question_label(qidx, label)))
    return lst


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


def get_question_labels_str_and_html_map() -> dict[int, tuple[str, str]]:
    """Get the question labels in str/html as a mapping from unit-indexed question indices.

    Returns:
        The question labels in str/html as a dictionary mapping
        from unit-indexed question indices.
    """
    return {
        i: (label, label_html)
        for i, label, label_html in get_question_html_label_triples()
    }


def get_question_label_str_and_html(qidx: int) -> tuple[str, str]:
    """Get the question string label and fancy HTML label for question index.

    Note: if you need this for multiple questions, it will generally be more
    efficient for the database if you ask for all them at once with
    :func:`get_question_html_label_triples`.
    """
    qlabel = get_question_label(qidx)
    return qlabel, _render_html_question_label(qidx, qlabel)


def question_list_to_dict(questions: list[dict]) -> dict[str, dict]:
    """Convert a list of question dictionaries to a nested dict with question index as str keys."""
    return {str(i + 1): q for i, q in enumerate(questions)}


def _render_html_question_label(qidx: int, qlabel: str) -> str:
    qlabel = html.escape(qlabel)
    if qlabel == f"Q{qidx}":
        return qlabel
    else:
        return f'<abbr title="question index {qidx}">{qlabel}</abbr>'


def render_html_flat_question_label_list(qindices: list[int] | None) -> str:
    """Return a string of question labels, given a list of question indices.

    If the list contains positive integers, return their labels.

    If the list contains the special value MobilePage.DNM_qidx, then return the
    string ``"Do Not Mark"``.

    If the list is empty or the special value ``None``, then return the
    string ``"None"``.
    """
    if not qindices:
        return "None"
    if MobilePage.DNM_qidx in qindices:
        return "Do Not Mark"
    T = get_question_labels_str_and_html_map()
    # return ", ".join(T[qidx][1] for qidx in sorted(qindices)) # Nicer, but breaks CI
    return ", ".join(T[qidx][1] for qidx in qindices)


def get_selection_method_of_all_questions() -> dict[int, list[int] | None]:
    """Get the selection method for all questions.

    Returns:
        Dict of {q_index: selection} where selection is a list of versions, or None.
    """
    selection_method = {}
    for question in SpecQuestion.objects.all().order_by("question_index"):
        selection_method[question.question_index] = question.select
    return selection_method


def _flatten_serializer_errors(errs) -> list[str]:
    error_list = []
    for k, v in errs.detail.items():
        if isinstance(v, list) and len(v) == 1:
            error_list.append(f"{k}: {v[0]}")
            continue
        if k == "question" and isinstance(v, dict):
            # this big ol pile of spaghetti renders errors within questions
            for j, u in v.items():
                if isinstance(u, dict):
                    for i, w in u.items():
                        if isinstance(w, list) and len(w) == 1:
                            (w,) = w
                        error_list.append(f"{k} {j}: {i}: {w}")
                else:
                    error_list.append(f"{k} {j}: {u}")
            continue
        # last ditch effort if neither of the above: make 'em into strings
        error_list.append(f"{k}: {str(v)}")
    return error_list
