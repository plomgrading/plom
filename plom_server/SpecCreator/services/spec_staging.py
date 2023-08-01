# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

import copy
import json
import pathlib
from typing import Any, Dict, List, Union

from django.utils.text import slugify
from plom.specVerifier import SpecVerifier

from ..models import StagingSpecification


class StagingSpecificationService:
    """All functions related to staging a test specification.

    E.g., keeping track of the user's progress in the specification creator wizard.
    """

    def specification(self):
        """Get the latest form of the StagingSpecification instance.

        Returns:
            StagingSpecification: the singleton DB object.
        """
        spec = StagingSpecification.load()
        return spec

    def reset_specification(self):
        """Clear the StagingSpecification object.

        Returns:
            StagingSpecification: the newly-cleared DB object.
        """
        spec = self.specification()
        spec.name = ""
        spec.longName = ""
        spec.numberOfPages = 0
        spec.numberOfVersions = 0
        spec.totalMarks = 0
        spec.numberOfQuestions = 0
        spec.pages = {}
        spec.questions = {}
        spec.save()
        return spec

    def get_long_name(self):
        """Return the TestSpecInfo long_name field.

        Returns:
            str: the test's long name.
        """
        return self.specification().longName

    def set_long_name(self, long_name: str):
        """Set the test's long name.

        Args:
            long_name: the new long name.
        """
        test_spec = self.specification()
        test_spec.longName = long_name
        test_spec.save()

    def get_short_name(self):
        """Return the TestSpecInfo short_name field.

        Returns:
            str: the test's short name
        """
        return self.specification().name

    def get_short_name_slug(self) -> str:
        """Return django-sluggified TestSpecInfo short_name field.

        This ensures that it is sanitised for use, say, in filenames.

        Returns:
            str: slug of the test's short name
        """
        return slugify(self.specification().name)

    def set_short_name(self, short_name: str) -> None:
        """Set the short name of the test.

        Args:
            short_name: the short name
        """
        test_spec = self.specification()
        test_spec.name = short_name
        test_spec.save()

    def get_n_versions(self) -> int:
        """Get the number of test versions.

        Returns:
            int: versions.
        """
        return self.specification().numberOfVersions

    def set_n_versions(self, n: int) -> None:
        """Set the number of test versions.

        Args:
            n: number of versions.
        """
        test_spec = self.specification()
        test_spec.numberOfVersions = n
        test_spec.save()

    def get_n_questions(self) -> int:
        """Get the number of questions.

        Returns:
            The number of questions in the test.
        """
        return self.specification().numberOfQuestions

    def set_n_questions(self, n: int) -> None:
        """Set the number of questions in the test.

        Args:
            n: the number of questions.
        """
        test_spec = self.specification()
        test_spec.numberOfQuestions = n
        test_spec.save()

    def get_total_marks(self) -> int:
        """Get the total number of marks in the test.

        Returns:
            How many total marks.
        """
        return self.specification().totalMarks

    def set_total_marks(self, total: int) -> None:
        """Set the total number of marks in the test.

        Args:
            total: full number of marks.
        """
        test_spec = self.specification()
        test_spec.totalMarks = total
        test_spec.save()

    def set_pages(self, n_pages: int) -> None:
        """Initialize page dictionary.

        Args:
            n_pages: number of pages in the reference PDF.
        """
        test_spec = self.specification()
        test_spec.pages = {}

        thumbnail_folder = pathlib.Path("SpecCreator") / "thumbnails" / "spec_reference"

        for i in range(n_pages):
            thumbnail_path = thumbnail_folder / f"thumbnail{i}.png"
            test_spec.pages[i] = {
                "id_page": False,
                "dnm_page": False,
                "question_page": False,
                "thumbnail": str(thumbnail_path),
            }
        test_spec.numberOfPages = n_pages
        test_spec.save()

    def get_page_list(self) -> List[Dict[str, Any]]:
        """Convert page dict into a list of dicts for looping over in a template.

        Returns:
            List of page dictionaries in order.
        """
        test_spec = self.specification()
        return [test_spec.pages[str(i)] for i in range(len(test_spec.pages))]

    def clear_pages(self):
        """Clear the page dictionary."""
        self.set_pages(0)

    def get_n_pages(self):
        """Get the number of pages in the test specification."""
        return self.specification().numberOfPages

    def set_id_page(self, page_idx: int) -> None:
        """Set a page as the test's only ID page.

        Args:
            page_idx: the index of the ID page
        """
        test_spec = self.specification()
        str_idx = str(page_idx)
        for idx, value in test_spec.pages.items():
            if idx == str_idx:
                test_spec.pages[idx]["id_page"] = True
            else:
                test_spec.pages[idx]["id_page"] = False
        test_spec.save()

    def clear_id_page(self) -> None:
        """Remove the ID page from the test."""
        test_spec = self.specification()
        for idx, value in test_spec.pages.items():
            test_spec.pages[idx]["id_page"] = False
        test_spec.save()

    def get_id_page_number(self) -> Union[int, None]:
        """Get the 1-indexed page number of the ID page.

        Returns:
            ID page index or None if there isn't yet an ID page.
        """
        pages = self.specification().pages
        for idx, page in pages.items():
            if page["id_page"]:
                return int(idx) + 1

        return None

    def set_do_not_mark_pages(self, pages: list) -> None:
        """Set these pages as the test's do-not-mark pages.

        Args:
            page: list of ints, 0-indexed page numbers.

        Returns:
            None
        """
        test_spec = self.specification()
        str_ids = [str(i) for i in pages]
        for idx, page in test_spec.pages.items():
            if idx in str_ids:
                test_spec.pages[idx]["dnm_page"] = True
            else:
                test_spec.pages[idx]["dnm_page"] = False
        test_spec.save()

    def get_dnm_page_numbers(self) -> List[int]:
        """Return a list of one-indexed page numbers for do-not-mark pages.

        Returns:
            0-indexed page numbers.
        """
        dnm_pages = []
        pages = self.specification().pages
        for idx, page in pages.items():
            if page["dnm_page"]:
                dnm_pages.append(int(idx) + 1)
        return dnm_pages

    def set_question_pages(self, pages: list, question: int) -> None:
        """Set these pages as the test's pages for a particular question.

        Args:
            pages: 0-indexed list of page numbers
            question: question id
        """
        test_spec = self.specification()
        str_ids = [str(i) for i in pages]
        for idx, page in test_spec.pages.items():
            if idx in str_ids:
                test_spec.pages[idx]["question_page"] = question
            elif test_spec.pages[idx]["question_page"] == question:
                test_spec.pages[idx]["question_page"] = False

        test_spec.save()

    def get_question_pages(self, question_id: int) -> List[int]:
        """Returns a 1-indexed list of page numbers for a question.

        Args:
            question_id: index of the question

        Returns:
            0-indexed page numbers.
        """
        question_pages = []
        pages = self.specification().pages
        for idx, page in pages.items():
            if page["question_page"] == question_id:
                question_pages.append(int(idx) + 1)
        return question_pages

    def set_questions(self, n_questions: int) -> None:
        """Initialize questions dictionary.

        Args:
            n_questions: number of questions in the specification
        """
        the_spec = self.specification()

        questions = {}
        for i in range(n_questions):
            one_index = i + 1
            questions[one_index] = {
                "pages": [],
                "mark": 0,
                "label": "",
                "select": "fix",
            }
        the_spec.questions = questions
        the_spec.numberOfQuestions = n_questions
        the_spec.save()

    def clear_questions(self) -> None:
        """Clear the questions dictionary."""
        self.set_questions(0)
        self.set_total_marks(0)

        # clear questions from pages
        the_spec = self.specification()
        for i in range(self.get_n_pages()):
            page = the_spec.pages[str(i)]
            page["question_page"] = False
        the_spec.save()

    def create_or_replace_question(
        self, one_index: int, label: str, mark: int, shuffle: bool, pages=[]
    ) -> None:
        """Create a question for the specification. If a question with the same index exists, overwrite it.

        Args:
            one_index: question number
            label: question label
            mark: max marks for the question
            shuffle: Randomize question across test versions?
            pages (optional): list of 1-indexed page numbers: on what pages does this
                question appear?
        """
        select = "fix"
        if shuffle:
            select = "shuffle"

        question_dict = {"pages": pages, "mark": mark, "label": label, "select": select}
        the_spec = self.specification()
        the_spec.questions[one_index] = question_dict
        the_spec.save()

        if pages:
            self.set_question_pages(
                [p - 1 for p in pages], one_index
            )  # warning: page list is zero-indexed and pages in the spec are one-indexed

    def set_question_select(self, one_index: int, set_as_shuffle: bool) -> None:
        """Change the status of a question's 'select' property.

        Args:
            one_index: the question number
            set_as_shuffle: when true, change to 'shuffle,' otherwise set to 'fix'
        """
        the_spec = self.specification()
        if set_as_shuffle:
            the_spec.questions[one_index].update({"select": "shuffle"})
        else:
            the_spec.questions[one_index].update({"select": "fix"})
        the_spec.save()

    def fix_all_questions(self) -> None:
        """Set all questions to 'fix': used when the number of versions is set to 1."""
        for i in range(self.get_n_questions()):
            one_index = i + 1
            self.set_question_select(one_index, False)

    def has_question(self, one_index: int) -> bool:
        """Return True if the staging spec has question 'one_index'."""
        return str(one_index) in self.specification().questions  # JSON field!

    def get_question(self, one_index: int) -> Union[Dict, None]:
        """Return a question dictionary given its one-index. If it doesn't exist, return None."""
        if self.has_question(one_index):
            return self.specification().questions[str(one_index)]  # JSON field!
        return None

    def get_marks_assigned_to_other_questions(self, one_index: int) -> int:
        """Return the total number of marks assigned to questions other than the one at one_index."""
        the_spec = self.specification()
        total = 0
        for q in the_spec.questions:
            if q == one_index:
                continue
            qdict = self.get_question(q)
            if not qdict:
                continue
            total += qdict["mark"]

        return total

    def get_staging_spec_dict(self) -> Dict:
        """Generate a dictionary from the current state of the specification."""
        spec_dict = self.specification().__dict__

        # remove django model-related fields
        spec_dict.pop("_state")
        spec_dict.pop("id")

        pages = spec_dict.pop("pages")
        spec_dict["idPage"] = self.get_id_page_number()
        spec_dict["doNotMarkPages"] = self.get_dnm_page_numbers()

        questions = spec_dict.pop("questions")
        questions_list = [questions[str(i + 1)] for i in range(self.get_n_questions())]
        spec_dict["question"] = questions_list
        return spec_dict

    def get_valid_spec_dict(self, verbose=True) -> Dict:
        """Validate specification and get public code/private seed, return as dict."""
        valid_dict = self.validate_specification(verbose=verbose)
        return valid_dict

    def validate_specification(self, verbose=True) -> Dict:
        """Verify the specification, assign public/private codes, return validated spec.

        Uses the original SpecVerifier.
        """
        spec_dict = self.get_staging_spec_dict()
        spec_w_default_quest_labels = self.insert_default_question_labels(
            copy.deepcopy(spec_dict)
        )
        verifier = SpecVerifier(spec_w_default_quest_labels)
        verifier.verifySpec(verbose=verbose)
        verifier.checkCodes(verbose=verbose)
        return verifier.spec

    def insert_default_question_labels(self, spec_dict: dict) -> Dict:
        """If any question labels are missing. insert default question labels.

        This might happen if the staging spec is from a user-uploaded toml file.
        """
        verifier = SpecVerifier(spec_dict)
        for i in range(spec_dict["numberOfQuestions"]):
            one_index = i + 1
            question = spec_dict["question"][i]
            if question["label"] == "":
                default_label = verifier.get_question_label(one_index)
                question["label"] = default_label
                self.create_or_replace_question(
                    one_index,
                    default_label,
                    question["mark"],
                    (question["select"] == "shuffle"),
                    question["pages"],
                )
        return spec_dict

    def is_valid(self) -> bool:
        """Return True if the current state of the specification is valid."""
        try:
            valid_spec = self.validate_specification()
        except ValueError:
            return False
        if valid_spec:
            return True
        return False

    def dump_json(self) -> str:
        """Convert the specification to a JSON object and dump into a string."""
        spec_dict = self.get_staging_spec_dict()
        return json.dumps(spec_dict)

    def create_from_dict(self, spec_dict: dict) -> None:
        """Take a dictionary (which has previously been validated) and stage a test specification from it.

        Returns:
            None, but modifies the internal state.
        """
        self.set_long_name(spec_dict["longName"])
        self.set_short_name(spec_dict["name"])
        self.set_n_versions(spec_dict["numberOfVersions"])
        self.set_total_marks(spec_dict["totalMarks"])
        self.set_n_questions(spec_dict["numberOfQuestions"])

        self.set_pages(spec_dict["numberOfPages"])
        self.set_id_page(spec_dict["idPage"] - 1)
        self.set_do_not_mark_pages([p - 1 for p in spec_dict["doNotMarkPages"]])

        questions = spec_dict["question"]
        # make sure the questions are a dict-of-dicts
        if not isinstance(questions, dict):
            questions_dict = {}
            for i in range(len(questions)):
                questions_dict[str(i + 1)] = questions[i]
            spec_dict["question"] = questions_dict
            questions = questions_dict

        for i in range(len(questions)):
            one_index = i + 1
            question = questions[str(one_index)]

            # we can create a default label later
            if "label" in question:
                label = question["label"]
            else:
                label = ""
            mark = question["mark"]

            if "select" in question:
                select = question["select"] == "shuffle"
            else:
                select = "fix"

            pages = question["pages"]
            self.create_or_replace_question(one_index, label, mark, select, pages)

    def are_all_pages_selected(self) -> Union[bool, None]:
        """Return True if all of the pages in the specification are selected, otherwise return false. If there are no pages, return None."""
        if self.get_n_pages() == 0:
            return None

        for page_key, page in self.specification().pages.items():
            if (
                not page["id_page"]
                and not page["dnm_page"]
                and not page["question_page"]
            ):
                return False
        return True

    def get_progress_dict(self) -> Dict[str, Any]:
        """Get a dict representing the completion state of the specification."""
        progress_dict = {
            "has_names": len(self.get_short_name()) > 0
            and len(self.get_long_name()) > 0,
            "has_versions": self.get_n_versions() > 0,
            "has_n_pages": self.get_n_pages() > 0,
            "has_id_page": self.get_id_page_number() is not None,
            "has_questions": self.get_n_questions() > 0,
            "has_total_marks": self.get_total_marks() > 0,
            "all_pages_selected": self.are_all_pages_selected(),
        }

        complete_questions = []
        for i in range(self.get_n_questions()):
            one_index = i + 1
            question = self.get_question(one_index)
            if (
                question
                and question["label"]
                and question["mark"]
                and question["select"]
                and question["pages"]
            ):
                complete_questions.append(one_index)

        progress_dict.update({"complete_questions": complete_questions})
        return progress_dict

    def not_empty(self) -> bool:
        """Return True if the staging specification isn't empty."""
        prog_dict = self.get_progress_dict()
        for key, item in prog_dict.items():
            if item:
                return True
        return False

    def compare_spec(self, spec) -> bool:
        """Return True if the input specification is the same as that saved to the StagingSpecification table."""
        staged_spec_dict = self.get_staging_spec_dict()
        # if questions is a list-of-dicts, convert to dict
        if isinstance(staged_spec_dict["question"], list):
            questions = staged_spec_dict.pop("question")
            question_dict = {}
            for i in range(len(questions)):
                one_index = str(i + 1)
                question_dict[one_index] = questions[i]
            staged_spec_dict["question"] = question_dict

        spec_copy = copy.deepcopy(spec)
        spec_copy.pop("publicCode", None)
        spec_copy.pop("privateSeed", None)

        return staged_spec_dict == spec_copy
