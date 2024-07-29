# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2024 Andrew Rechnitzer
# Copyright (C) 2020-2024 Colin B. Macdonald
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Brennen Chiu

from __future__ import annotations

from copy import deepcopy
import logging
from math import ceil
from pathlib import Path
import random
import re
import sys
from typing import Any

if sys.version_info >= (3, 9):
    from importlib import resources
else:
    import importlib_resources as resources

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib
import tomlkit

import plom
from plom.tpv_utils import new_magic_code


specdir = Path("specAndDatabase")
log = logging.getLogger("spec")

# support for colour checkmarks
ansi_green = "\033[92m"
ansi_yellow = "\033[93m"
ansi_red = "\033[91m"
ansi_off = "\033[0m"
# warn_mark = " " + ansi_red + "[warning]" + ansi_off
# check_mark = " " + ansi_green + "[\N{Check Mark}]" + ansi_off
warn_mark = " [warning]"
check_mark = " [check]"
chk = check_mark

MAX_PAPERS_TO_PRODUCE = 9999

# a canonical ordering of spec keys for output to toml
# not used by legacy.
spec_key_order_for_toml_output = [
    "name",
    "longName",
    "publicCode",
    "numberOfVersions",
    "numberOfPages",
    "allowSharedPages",
    "idPage",
    "doNotMarkPages",
    "numberOfQuestions",
    "totalMarks",
    "question",
]


def get_question_label(spec, n: int | str) -> str:
    """Print question label for the nth question from spec dict.

    Args:
        spec (dict/SpecVerifier): a spec dict or a SpecVerifier
            object.
        n: which question, current indexed from 1.  For historical
            reasons it can be a str.

    Returns:
        The custom label of a question or "Qn" if one is not set.

    Raises:
        ValueError: `n` is out of range.

    TODO: change spec question keys to int.
    """
    n = int(n)
    try:
        N = spec["numberOfQuestions"]
    except KeyError:
        N = None
    if N:
        if n < 1 or n > N:
            raise ValueError(f"question={n} out of range [1, {N}]")
    else:
        if n < 1:
            raise ValueError(f"question={n} out of range [1, ...]")
    label = spec["question"][str(n)].get("label", None)
    if label:
        return label
    return "Q{}".format(n)


def get_question_labels(spec) -> list[str]:
    """Get a list of all the question labels from spec dict.

    Args:
        spec (dict/SpecVerifier): a spec dict or a SpecVerifier
            object.

    Returns:
        The labels of each question.
    """
    N = spec["numberOfQuestions"]
    return [get_question_label(spec, n) for n in range(1, N + 1)]


# helper function
def isPositiveInt(s):
    """Check that given string s can be converted to a positive int."""
    try:
        n = int(s)
        if n > 0:
            return True
        else:
            return False
    except ValueError:
        return False


# helper function
def isListPosInt(L: list[str | int], lastPage: int) -> bool:
    """Check for a list of pos-int, bounded below by 1 and above by lastPage.

    It need not be contiguous or ordered.

    Args:
        L: a list of strings or ints.
        lastPage: no element of list can be greater.

    Returns:
        Whether input satisfies these conditions.
    """
    # check it is a list
    if not isinstance(L, list):
        return False
    # check each entry is 0<n<=lastPage
    for n in L:
        if not isPositiveInt(n):
            return False
        n = int(n)
        if n > lastPage:
            return False
    # all tests passed
    return True


# helper function
def isContiguous(L: list[str | int]) -> bool:
    """Check input is a contiguous list of integers.

    Args:
        L: a list of strings or ints.

    Returns:
        bool
    """
    if not isinstance(L, list):
        return False
    sl = set(int(n) for n in L)
    for n in range(min(sl), max(sl) + 1):
        if n not in sl:
            return False
    return True


def build_page_to_group_dict(spec) -> dict[int, str]:
    """Given a valid spec return a dict that translates each page to its containing group.

    Args:
        spec (dict): A validated test spec

    Returns:
        dict: A mapping of page numbers to groups: 'ID', 'DNM', or 'Q7'
    """
    # start with the id page
    page_to_group = {spec["idPage"]: "ID"}
    # now any dnm
    for pg in spec["doNotMarkPages"]:
        page_to_group[pg] = "DNM"
    # now the questions
    for q in spec["question"]:
        for pg in spec["question"][q]["pages"]:
            page_to_group[pg] = get_question_label(spec, q)

    return page_to_group


def build_page_to_version_dict(spec, question_versions):
    """Given the spec and the question-version dict, produce a dict that maps pages to versions.

    Args:
        spec (dict): A validated test spec
        question_versions (dict): A dict mapping question numbers to version numbers.
        Note that typically each exam has a different qv-map.

    Returns:
        dict: A mapping of page numbers to versions. Note idpages and
        dnm pages have version 1.
    """
    # idpage and dnm pages always from version 1
    page_to_version = {spec["idPage"]: 1}
    for pg in spec["doNotMarkPages"]:
        page_to_version[pg] = 1
    for q in spec["question"]:
        for pg in spec["question"][q]["pages"]:
            # be careful, the qv-map keys are ints, while those in the spec are strings
            page_to_version[pg] = question_versions[int(q)]
    return page_to_version


class SpecVerifier:
    """Verify Plom exam specifications.

    Example specification:
    >>> raw = {
    ... 'name': 'plomdemo',
    ... 'longName': 'Midterm Demo using Plom',
    ... 'numberOfVersions': 2,
    ... 'numberOfPages': 6,
    ... 'numberOfQuestions': 3,
    ... 'totalMarks': 25,
    ... 'numberToProduce': 20,
    ... 'privateSeed': '1001378822317872',
    ... 'publicCode': '27038',
    ... 'idPage': 1,
    ... 'doNotMarkPages': [2],
    ... 'question': [
    ...     {'pages': 3, 'mark': 5, 'select': 'shuffle'},
    ...     {'pages': [4], 'mark': 10, 'select': 'fix'},
    ...     {'pages': [5, 6], 'mark': 10, 'select': 'shuffle'}
    ...   ]
    ... }
    >>> spec = SpecVerifier(raw)

    Here `spec` is an object representing a Plom exam specification:
    >>> print(spec)
    Plom exam specification:
      Name of exam = plomdemo
      Long name of exam = Midterm Demo using Plom
      Number of source versions = 2
      Number of tests to produce = 20
      Number of pages = 6
      IDpage = 1
      Do not mark pages = [2]
      Number of questions to mark = 3
        Q1: pages 3, selected as shuffle, worth 5 marks
        Q2: pages [4], selected as fix, worth 10 marks
        Q3: pages [5, 6], selected as shuffle, worth 10 marks
      Exam total = 25 marks


    We can verify that this input is valid:
    >>> spec.verifySpec()     # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
    Checking mandatory specification keys
        contains "name" [check]
        contains "longName" [check]
        ...
        Page 5 used at least once [check]
        Page 6 used at least once [check]

    The spec above already has private and public random numbers, but
    these would typically be autogenerated:
    >>> spec.checkCodes()
    NOTE: this spec has a 'privateSeed': no need to autogenerate
    NOTE: this spec has a 'publicCode': no need to autogenerate

    Write the result for the server to find on disk:
    >>> spec.saveVerifiedSpec()     # doctest: +SKIP

    You can omit some fields such as ``numberOfQuestions`` and
    ``totalMarks``.  They will be automatically calculated on
    verification.  Before that, will print as "TBD*":
    >>> raw = {
    ... 'name': 'plomdemo',
    ... 'longName': 'Midterm Demo using Plom',
    ... 'numberOfVersions': 2,
    ... 'numberOfPages': 4,
    ... 'numberToProduce': 20,
    ... 'idPage': 1,
    ... 'doNotMarkPages': [2],
    ... 'question': [
    ...     {'pages': 3, 'mark': 5},
    ...     {'pages': 4, 'mark': 10},
    ...   ]
    ... }
    >>> spec = SpecVerifier(raw)
    >>> print(spec)
    Plom exam specification:
      Name of exam = plomdemo
      Long name of exam = Midterm Demo using Plom
      Number of source versions = 2
      Number of tests to produce = 20
      Number of pages = 4
      IDpage = 1
      Do not mark pages = [2]
      Number of questions to mark = TBD*
        Q1: pages 3, selected as shuffle*, worth 5 marks
        Q2: pages 4, selected as shuffle*, worth 10 marks
      Exam total = TBD* marks
      (TBD* fields will be filled in on verification)

    >>> spec.verify()
    >>> print(spec)
    Plom exam specification:
      Name of exam = plomdemo
      Long name of exam = Midterm Demo using Plom
      Number of source versions = 2
      Number of tests to produce = 20
      Number of pages = 4
      IDpage = 1
      Do not mark pages = [2]
      Number of questions to mark = 2
        Q1: pages [3], selected as shuffle, worth 5 marks
        Q2: pages [4], selected as shuffle, worth 10 marks
      Exam total = 15 marks

    We also saw that omitting the ``select`` field defaults to
    ``"shuffle"``, whereby each paper will be generated by choosing a
    random version of each question.  If ``"fix"`` is specified, then
    version 1 will always be used.
    """

    def __init__(self, d):
        """Initialize a SpecVerifier from a dict.

        Args:
            d (dict): an exam specification - it will not be modified by the specVerifier, rather
                specVerifier makes a copy of that dict.
        """
        local_d = deepcopy(d)  # see issue 2258
        # Issue #2276, we're removing numberToProduce but legacy servers still need it
        # So its not an error if the new server uses SpecVerifier without a numberToProduce
        local_d.setdefault("numberToProduce", -1)
        question = local_d.get("question", None)
        if not question:
            raise ValueError("Specification error - must contain at least one question")
        if isinstance(question, list):
            local_d["question"] = {str(g + 1): v for g, v in enumerate(question)}
        self.spec = local_d

    @classmethod
    def _template_as_bytes(cls):
        return (resources.files(plom) / "templateTestSpec.toml").read_bytes()

    @classmethod
    def _template_as_string(cls):
        return (resources.files(plom) / "templateTestSpec.toml").read_text()

    @classmethod
    def create_template(cls, fname="testSpec.toml"):
        """Create a documented example exam specification."""
        template = cls._template_as_bytes()
        with open(fname, "wb") as fh:
            fh.write(template)

    @classmethod
    def create_solution_template(cls, fname):
        """Create a documented example exam specification."""
        template = resources.read_binary(plom, "templateSolutionSpec.toml")
        with open(fname, "wb") as fh:
            fh.write(template)

    @classmethod
    def create_demo_template(cls, fname="demoSpec.toml", *, num_to_produce=None):
        """Create a documented demo exam specification.

        This does not create a Spec object, but rather saves the
        template to disc.
        """
        s = cls._demo_str(num_to_produce=num_to_produce)
        with open(fname, "w") as fh:
            fh.write(s)

    @classmethod
    def create_demo_solution_template(cls, fname):
        """Create a documented demo exam-solution specification.

        This does not create a Spec object, but rather saves the
        template to disc.
        """
        with open(fname, "w") as fh:
            fh.write(resources.read_text(plom, "templateSolutionSpec.toml"))

    @classmethod
    def demo(cls, *, num_to_produce=None):
        return cls(tomllib.loads(cls._demo_str(num_to_produce=num_to_produce)))

    @classmethod
    def _demo_str(cls, *, num_to_produce=None):
        s = cls._template_as_string()
        if num_to_produce:
            from plom.create.demotools import getDemoClassListLength

            # TODO: 20 in source file hardcoded here, use regex instead
            s = s.replace(
                "numberToProduce = 20",
                "numberToProduce = {}".format(num_to_produce),
            )
            classlist_len = getDemoClassListLength()
            if num_to_produce > classlist_len:
                raise ValueError(
                    "Demo size capped at classlist length of {}".format(classlist_len)
                )
        return s

    @classmethod
    def from_toml_file(cls, fname="testSpec.toml"):
        """Initialize a SpecVerifier from a toml file."""
        with open(fname, "rb") as f:
            return cls(tomllib.load(f))

    @classmethod
    def load_verified(cls, fname=specdir / "verifiedSpec.toml"):
        """Initialize a SpecVerifier from the default verified toml file.

        By default, this is the CWD/specAndDatabase/verifiedSpec.toml but
        you can override this with the `fname` kwarg.
        """
        # TODO: maybe we should do some testing here?
        with open(fname, "rb") as f:
            return cls(tomllib.load(f))

    def as_toml_string(self, *, _legacy: bool = True):
        """Return the spec as a string in the TOML format."""
        # TODO bit yuck, we hack questions back to a list before saving
        s = deepcopy(self.spec)
        s["question"] = []
        for g in range(len(self.spec["question"])):
            s["question"].append(self.spec["question"][str(g + 1)])
        # legacy spec is ready to go.
        if _legacy:
            return tomlkit.dumps(s)

        # this is deprecated; hide it from the new server
        s.pop("numberToProduce", None)
        # put the keys in a particular order by constructing a
        # new dict since python orders by insertion
        ordered_toml = dict()
        for k in spec_key_order_for_toml_output:
            ordered_toml.update({k: s[k]})
        return tomlkit.dumps(ordered_toml)

    def __getitem__(self, what):
        """Pass access to the keys to underlying dict.

        This allows ``spec["key"]`` instead of ``spec.spec["key"]``.
        """
        return self.spec[what]

    @property
    def number_to_produce(self) -> int:
        return self.spec["numberToProduce"]

    # aliases to match the toml file
    numberToProduce = number_to_produce

    def get_question_label(self, n: int | str) -> str:
        """Get the question label of the nth question, indexed from 1.

        Args:
            n: which question, current indexed from 1.  For historical
                reasons it can be a str.

        Returns:
            The custom label of a question or "Qn" if one is not set.
        """
        return get_question_label(self.spec, n)

    def set_number_papers_add_spares(
        self,
        n: int,
        *,
        spare_percent: int | float = 10,
        min_extra: int = 5,
        max_extra: int = 100,
    ) -> None:
        """Set previously-deferred number of papers to produce and add spares.

        By default this will add 10% extra "spare" papers.

        Args:
            n (int): how many requested.

        Keyword Args:
            spare_percent (int/float): how many extra papers as a
                percentage of `n` (default: 10).
            min_extra (int): minimum number of extra papers (default: 5)
            max_extra (int): maximum extra papers (default: 100)

        Returns:
            None

        Exceptions:
            ValueError: number of papers already set.
        """
        extra = ceil(spare_percent * n / 100)
        extra = min(max(extra, min_extra), max_extra)  # threshold
        if self.number_to_produce >= 0:
            # TODO: consider relaxing this?
            raise ValueError("Number of papers already set: read-only")
        self.spec["numberToProduce"] = n + extra
        log.info(f"deferred number of papers is now set to {self.number_to_produce}")

    def __str__(self):
        """Convert ourselves to a string."""
        N = self.spec.get("numberOfQuestions", "TBD*")
        s = "Plom exam specification:\n  "
        s += "\n  ".join(
            (
                "Name of exam = {}".format(self.spec["name"]),
                "Long name of exam = {}".format(self.spec["longName"]),
                "Number of source versions = {}".format(self.spec["numberOfVersions"]),
                # "Public code (to prevent project collisions) = {}".format(self.spec["publicCode"]),
                # "Private random seed (for randomisation) = {}".format(self.spec["privateSeed"]),
                f"Number of tests to produce = {self.number_to_produce}",
                "Number of pages = {}".format(self.spec["numberOfPages"]),
                "IDpage = {}".format(self.spec["idPage"]),
                "Do not mark pages = {}".format(self.spec["doNotMarkPages"]),
                f"Number of questions to mark = {N}",
            )
        )
        s += "\n"
        for gs, question in self.spec["question"].items():
            s += "    {}: pages {}, selected as {}, worth {} marks\n".format(
                self.get_question_label(gs),
                question["pages"],
                question.get("select", "shuffle*"),
                question["mark"],
            )
        K = self.spec.get("totalMarks", "TBD*")
        s += f"  Exam total = {K} marks"
        if K == "TBD*" or N == "TBD*":
            s += "\n  (TBD* fields will be filled in on verification)"
        return s

    def get_public_spec_dict(self):
        """Return a copy of the spec dict with private info removed."""
        d = self.spec.copy()
        d.pop("privateSeed", None)
        return d

    def group_label_from_page(self, pagenum):
        return build_page_to_group_dict(self)[pagenum]

    def verify(
        self, *, verbose: str | None | bool = False, _legacy: bool = True
    ) -> None:
        """Check that spec contains required attributes and insert default values."""
        self.verifySpec(verbose=verbose, _legacy=_legacy)

    def verifySpec(
        self, *, verbose: str | None | bool = True, _legacy: bool = True
    ) -> None:
        """Check that spec contains required attributes and insert default values.

        Keyword Args:
            verbose: ``None``/``False`` for don't print; ``True`` is print to
                standard output; ``"log"`` means use logging mechanism.

        Returns:
            None

        Exceptions:
            ValueError: with a message indicating the problem.
        """

        def _noop(x):
            return

        prnt: Any = None
        if verbose == "log":
            prnt = log.info
        elif verbose:
            prnt = print
        else:
            prnt = _noop

        self._check_keys(print=prnt)
        self._check_name_and_production_numbers(print=prnt)
        lastPage = self.spec["numberOfPages"]
        self._check_IDPage(lastPage, print=prnt)
        self._check_doNotMarkPages(lastPage, print=prnt)
        prnt("Checking question groups")
        self._check_questions(print=prnt)
        # Note: enable all-or-none check for labels
        # prnt("Checking either all or no questions have labels")
        # has_label = [
        #     "label" in self.spec["question"][str(n + 1)]
        #     for n in range(self.spec["numberOfQuestions"])
        # ]
        # if any(has_label) and not all(has_label):
        #     raise ValueError("Either all should have labels or none should")
        prnt("Checking for unique question labels")
        labels = [
            self.spec["question"][str(n + 1)].get("label", None)
            for n in range(self.spec["numberOfQuestions"])
        ]
        labels = [x for x in labels if x is not None]
        if len(set(labels)) != len(labels):
            raise ValueError(f'Question labels must be unique but we have "{labels}"')
        if any(len(x) > 24 for x in labels):
            raise ValueError(f'Question labels should be at most 24 chars: "{labels}"')

        self._check_pages(print=prnt, _legacy=_legacy)

    def checkCodes(self, *, verbose: bool | str = True) -> None:
        """Add public and private codes if the spec doesn't already have them.

        Keywords Args:
            verbose (bool/str): `None`/`False` for don't print; `True` is print
                to standard output; `"log"` means use logging mechanism.

        Returns:
            None
        """

        def _noop(x):
            return

        prnt: Any = None
        if verbose == "log":
            prnt = log.info
        elif verbose:
            prnt = print
        else:
            prnt = _noop

        if "privateSeed" in self.spec:
            prnt("NOTE: this spec has a 'privateSeed': no need to autogenerate")
        else:
            prnt("Assigning a privateSeed to the spec{}".format(chk))
            self.spec["privateSeed"] = str(random.randrange(0, 10**16)).zfill(16)

        if "publicCode" in self.spec:
            prnt("NOTE: this spec has a 'publicCode': no need to autogenerate")
        else:
            prnt("Assigning a publicCode to the spec{}".format(chk))
            self.spec["publicCode"] = new_magic_code()

    def saveVerifiedSpec(self, *, verbose=False, basedir=Path("."), outfile=None):
        """Saves the verified spec to a particular name.

        Keyword Args:
            verbose (bool): output messages about what is happening.
            basedir (pathlib.Path): save to `basedir/specdir/verifiedSpec.toml`.
            outfile (pathlib.Path): or specify the path and filename instead.
                If both specified, `outfile` takes precedence.
        """
        # TODO bit yuck, we hack questions back to a list before saving
        s = deepcopy(self.spec)
        s["question"] = []
        for g in range(len(self.spec["question"])):
            s["question"].append(self.spec["question"][str(g + 1)])
        if not outfile:
            outfile = basedir / specdir / "verifiedSpec.toml"
        if verbose:
            print(f'Saving the verified spec to "{outfile}"')
        with open(outfile, "w") as fh:
            fh.write("# This file is produced by the plom-create script.\n")
            fh.write(
                "# Do not edit this file. Instead edit testSpec.toml and rerun plom-create.\n"
            )
            fh.write(tomlkit.dumps(s))

    def _check_keys(self, print=print):
        """Check that spec contains required keys."""
        print("Checking mandatory specification keys")
        for x in [
            "name",
            "longName",
            "numberOfVersions",
            "numberOfPages",
            "numberToProduce",
            "idPage",
        ]:
            if x not in self.spec:
                raise ValueError(f'Specification error - must contain "{x}"')
            print(f'  contains "{x}"{chk}')
        if len(self.spec["question"]) < 1:
            raise ValueError("Specification error - must contain at least one question")
        print("  contains at least one question{}".format(chk))
        print("Checking optional specification keys")
        for x in ["doNotMarkPages", "totalMarks", "numberOfQuestions"]:
            if x in self.spec:
                print(f'  contains "{x}"{chk}')
        # check for no longer supported numberToName field
        if "numberToName" in self.spec:
            raise ValueError(
                'The "numberToName" spec-field has been removed in favour'
                ' of the "paper_number" column in the classlist.'
            )

    def _check_name_and_production_numbers(self, print=print) -> None:
        print("Checking specification name and numbers")
        print("  Checking names")
        if not re.match(r"[\w\-\.]+$", self.spec["name"]):
            raise ValueError(
                "Specification error - "
                "Test name must be alphanumeric string without spaces "
                "(underscores, hyphens, and periods are ok)."
            )
        print('    name "{}" is acceptable{}'.format(self.spec["name"], chk))

        if len(self["longName"]) <= 0 or self["longName"].isspace():
            raise ValueError(
                "Specification error - Test should have nonempty longName."
            )
        print('    has long name "{}"{}'.format(self["longName"], chk))

        print("  Checking production numbers")
        for x in ("numberOfVersions", "numberOfPages"):
            if not isPositiveInt(self.spec[x]):
                raise ValueError(
                    'Specification error - "{}" must be a positive integer.'.format(x)
                )
            print('    "{}" = {} is positive integer{}'.format(x, self.spec[x], chk))

        print("  Check an even number of pages:")
        if self.spec["numberOfPages"] % 2 == 1:
            raise ValueError(
                "Specification error - numberOfPages must be an even number."
            )

        for x in ["numberToProduce"]:
            try:
                self.spec[x] = int(self.spec[x])
            except ValueError:
                raise ValueError(
                    'Specification error - "{}" must be an integer.'.format(x)
                ) from None
            print('    "{}" = {} is integer{}'.format(x, self.spec[x], chk))
            if self.spec[x] < 0:
                print(
                    '    "{}" is negative: will determine later from classlist!{}'.format(
                        x, warn_mark
                    )
                )

        if self.number_to_produce == 0:
            raise ValueError('Specification error - "numberToProduce" cannot be zero.')

        if self.number_to_produce > MAX_PAPERS_TO_PRODUCE:
            raise ValueError(
                f'Specification error - "numberToProduce" cannot be greater than {MAX_PAPERS_TO_PRODUCE}.'
            )

    def _check_questions(self, print=print) -> None:
        if "numberOfQuestions" not in self.spec:
            N = len(self.spec["question"])
            self.spec["numberOfQuestions"] = N
            print(f'    "numberOfQuestions" omitted; calculated as {N}{chk}')
        N = self.spec["numberOfQuestions"]
        if not isPositiveInt(N):
            raise ValueError(f'numberOfQuestions = "{N}" must be a positive integer.')
        print(f'    "numberOfQuestions" = {N} is a positive integer{chk}')
        if not N == len(self.spec["question"]):
            raise ValueError(
                f'Inconsistent: "[[question]]" blocks do not match numberOfQuestions={N}'
            )
        for k in range(1, N + 1):
            # TODO: why not integers for key k?  See also elsewhere
            if not str(k) in self.spec["question"]:
                raise ValueError(f"Specification error - could not find question {k}")
            print(f"    Found question {k} of {N}{chk}")

        for k in range(1, N + 1):
            self._check_question_group(k, self.spec["numberOfPages"], print=print)

        print("  Checking mark totals")
        K = sum(m["mark"] for m in self.spec["question"].values())
        if "totalMarks" not in self.spec:
            self.spec["totalMarks"] = K
            print(f'    "totalMarks" omitted; calculated as {K}{chk}')
        else:
            total = self.spec["totalMarks"]
            if not isPositiveInt(total):
                raise ValueError(f'"totalMarks" = {total} must be a positive integer.')
            if self["totalMarks"] != K:
                raise ValueError(
                    f'"totalMarks" = {total} does not match question sum {K}.'
                )
            print(f'    "totalMarks" = {total} matches question sum {K}{chk}')

    def _check_IDPage(self, lastPage, print=print) -> None:
        print("Checking IDpage")
        if not (1 <= self.spec["idPage"] <= lastPage):
            raise ValueError(
                'IDpage error - "idPage" = {} should be a positive integer in range'.format(
                    self.spec["idPage"]
                )
            )
        print("    IDpage is a positive integer" + chk)
        # check that page 1 is in there.
        if self.spec["idPage"] != 1:
            print(
                "Warning - page 1 is not your ID page - are you sure you want to do this?"
                + warn_mark
            )

    def _check_doNotMarkPages(self, lastPage, print=print) -> None:
        print("Checking DoNotMark-pages")
        if "doNotMarkPages" not in self.spec:
            print("    DoNotMark pages is missing: defaulting to empty" + chk)
            self.spec["doNotMarkPages"] = []
        pages = self.spec["doNotMarkPages"]
        if not isinstance(pages, list):
            raise ValueError(
                f'DoNotMark pages "{pages}" is not a list of positive integers'
            )
        for n in pages:
            if not isPositiveInt(n):
                raise ValueError(
                    f"DoNotMark pages {pages} contains {n} which is not a positive integer"
                )
            if n > lastPage:
                raise ValueError(
                    f"DoNotMark page {n} is out of range: larger than lastPage={lastPage}"
                )

        if not self.spec["doNotMarkPages"]:
            print("    DoNotMark pages is empty" + chk)
        else:
            print("    DoNotMark pages is list of positive integers" + chk)

    def _check_question_group(self, g, lastPage, print=print) -> None:
        """Check and in some cases modify the spec of one particular question group."""
        g = str(g)  # TODO: why?
        print("  Checking question group #{}".format(g))
        question = self.spec["question"][g]
        required_keys = set(("pages", "mark"))
        optional_keys = set(("label", "select"))
        for k in required_keys:
            if k not in question:
                raise ValueError(f'Question error - could not find "{k}" key')
        for k in question.keys():
            if k not in required_keys.union(optional_keys):
                raise ValueError(f'Question error - unexpected extra key "{k}"')
        pages = question["pages"]
        if not isinstance(pages, list):
            pages = [pages]
            question["pages"] = pages
        # check each entry is integer 0 < n <= lastPage
        for n in pages:
            if not isPositiveInt(n):
                raise ValueError(f"Question error - page {n} is not a positive integer")
            if n > lastPage:
                raise ValueError(
                    f"Question error - page {n} out of range [1, {lastPage}]"
                )
        if not isContiguous(pages):
            raise ValueError(
                f"Question error - {pages} is not a contiguous list of pages"
            )
        print(f"    pages {pages} is list of contiguous positive integers{chk}")
        # check mark is positive integer
        if not isPositiveInt(question["mark"]):
            raise ValueError(
                f"Question error - mark {question['mark']} is not a positive integer"
            )
        print("    mark {} is positive integer{}".format(question["mark"], chk))
        select = question.get("select")
        if not select:
            select = "shuffle"
            question["select"] = select
            print(f'    missing select key, add default "{select}"' + chk)
        if select not in ("fix", "shuffle"):
            raise ValueError(
                f'Question error - select "{select}" is not "fix" or "shuffle"'
            )
        print('    select is "fix" or "shuffle"' + chk)

    def _check_pages(self, *, print=print, _legacy: bool = True) -> None:
        print("Checking which pages are used:")
        pageUse = {k + 1: 0 for k in range(self.spec["numberOfPages"])}
        pageUse[self.spec["idPage"]] += 1
        if self.spec.get("doNotMarkPages"):
            for p in self.spec["doNotMarkPages"]:
                pageUse[p] += 1
        for g in range(self.spec["numberOfQuestions"]):
            for p in self.spec["question"][str(g + 1)]["pages"]:
                pageUse[p] += 1
        for p in range(1, self.spec["numberOfPages"] + 1):
            if pageUse[p] == 0:
                raise ValueError(f"Page {p} unused, perhaps it should be DNM?")
            print(f"  Page {p} used at least once{chk}")
        if _legacy or not self.spec.get("allowSharedPages"):
            for p in range(1, self.spec["numberOfPages"] + 1):
                if pageUse[p] > 1:
                    # or perhaps this should be a warning, if we had such a mechanism
                    raise ValueError(
                        f"Page {p} overused {pageUse[p]} times but shared pages disabled"
                    )
        for g in range(self.spec["numberOfQuestions"]):
            for p in self.spec["question"][str(g + 1)]["pages"]:
                if p in self.spec["doNotMarkPages"]:
                    raise ValueError(
                        f"Page {p} cannot be shared b/w DNM and question idx {g + 1}"
                    )


def checkSolutionSpec(testSpec, solutionSpec):
    """Check the given solution spec against the validated test-spec and confirm its validity.

    Args:
        testSpec (dict): a validated plom test specification
        solutionSpec (dict): for example:
            { "numberOfVersions": 2, "numberOfPages": 6, "numberOfQuestions": 3, 'solution': {'1': {'pages': [3]}, '2': {'pages': [4]}, '3': {'pages': [5]} } }

    Returns:
        Tuple[bool, str]: Either ``(True, "All ok")`` or ``(False, Error message)``.
    """
    print("Checking = ", solutionSpec)
    # make sure keys are present
    for x in [
        "numberOfVersions",
        "numberOfPages",
        "numberOfQuestions",
        "solution",
    ]:
        if x not in solutionSpec:
            return (False, f"Missing key = {x}")
    # check Q/V values match test-spec
    for x in ["numberOfVersions", "numberOfQuestions"]:
        if solutionSpec[x] != testSpec[x]:
            return (False, f"Value of {x} does not match test spec")
    # check pages is pos-int
    if isPositiveInt(solutionSpec["numberOfPages"]) is False:
        return (False, "numberOfPages must be a positive integer.")

    # make sure right number of question-keys - match test-spec
    if len(solutionSpec["solution"]) != solutionSpec["numberOfQuestions"]:
        return (
            False,
            f"Question keys incorrect = {list(solutionSpec['solution'].keys())}",
        )
    # make sure each pagelist is contiguous an in range
    for q in range(1, solutionSpec["numberOfQuestions"] + 1):
        if str(q) not in solutionSpec["solution"]:
            return (
                False,
                f"Question keys incorrect = {list(solutionSpec['solution'].keys())}",
            )
        if (isinstance(solutionSpec["solution"][str(q)]["pages"], list) is False) or (
            len(solutionSpec["solution"][str(q)]["pages"]) == 0
        ):
            return (False, f"Pages for solution {q} must be a non-empty list")
        if (
            isListPosInt(
                solutionSpec["solution"][str(q)]["pages"], solutionSpec["numberOfPages"]
            )
            is False
        ):
            return (
                False,
                f"Pages for solution {q} are not a list in of positive integers between 1 and {solutionSpec['numberOfPages']}",
            )
    return (True, "All ok")
