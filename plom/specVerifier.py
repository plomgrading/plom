# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2022 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald

from copy import deepcopy
import logging
from math import ceil
from pathlib import Path
import random
import sys

if sys.version_info >= (3, 9):
    import importlib.resources as resources
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


# Some helper functions


def get_question_label(spec, n):
    """Print question label for the nth question from spec dict

    args:
        spec (dict/SpecVerifier): a spec dict or a SpecVerifier
            object.
        n (int/str): which question, current indexed from 1.

    returns:
        str: the custom label of a question or "Qn" if one is not set.
    TODO: change spec question keys to int.

    raises:
        ValueError: `n` is out of range.
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


def isPositiveInt(s):
    """Check that given string s can be converted to a positive int"""
    try:
        n = int(s)
        if n > 0:
            return True
        else:
            return False
    except ValueError:
        return False


def isListPosInt(l, lastPage):
    """Check given list is a list of pos-int, or string that can be converted to pos-ints, bounded below by 1 and above by lastPage. It need not be contiguous or ordered.

    args:
        l (list): a list of strings or ints
        lastPage (int): no element of list can be greater.

    returns:
        Bool

    """
    # check it is a list
    if not isinstance(l, list):
        return False
    # check each entry is 0<n<=lastPage
    for n in l:
        if not isPositiveInt(n):
            return False
        if n > lastPage:
            return False
    # all tests passed
    return True


def isContiguous(l):
    """Check input is a contiguous list of integers.

    args:
        l (list): a list of strings or ints

    returns:
        bool:
    """
    if not isinstance(l, list):
        return False
    sl = set(l)
    for n in range(min(sl), max(sl) + 1):
        if n not in sl:
            return False
    return True


def build_page_to_group_dict(spec):
    """Given a valid spec return a dict that translates each page to its containing group.

    args:
        spec (dict): A validated test spec
    returns:
        (dict): A dict mapping page numbers to groups: 'ID', 'DNM', or 'Q7'
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

    args:
        spec (dict): A validated test spec
        question_versions (dict): A dict mapping question numbers to version numbers.
        Note that typically each exam has a different qv-map.
    returns:
        (dict): A dict mapping page numbers to versions. Note idpages and dnm pages have version 1.
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
        Page 5 used once [check]
        Page 6 used once [check]

    The spec above already has private and public random numbers, but
    these would typically be autogenerated:
    >>> spec.checkCodes()
    WARNING - privateSeed is already set. Not replacing this.
    WARNING - publicCode is already set. Not replacing this.

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

    def as_toml_string(self):
        """Return the spec as a string in the TOML format."""
        # TODO bit yuck, we hack questions back to a list before saving
        s = deepcopy(self.spec)
        s["question"] = []
        for g in range(len(self.spec["question"])):
            s["question"].append(self.spec["question"][str(g + 1)])
        return tomlkit.dumps(s)

    # this allows spec["key"] instead of spec.spec["key"] for all
    def __getitem__(self, what):
        return self.spec[what]

    @property
    def number_to_produce(self):
        return self.spec["numberToProduce"]

    # aliases to match the toml file
    numberToProduce = number_to_produce

    def get_question_label(self, n):
        """Get the question label of the nth question, indexed from 1.

        Args:
            spec (dict/SpecVerifier): a spec dict or a SpecVerifier
                object.
             n (int/str): which question, current indexed from 1.


        Returns:
            str: the custom label of a question or "Qn" if one is not set.
        """
        return get_question_label(self.spec, n)

    def set_number_papers_add_spares(
        self, n, spare_percent=10, min_extra=5, max_extra=100
    ):
        """Set previously-deferred number of papers to produce and add spares.

        By default this will add 10% extra "spare" papers.

        args:
            n (int): how many requested.

        kwargs:
            spare_percent (int/float): how many extra papers as a
                percentage of `n` (default: 10).
            min_extra (int): minimum number of extra papers (default: 5)
            max_extra (int): maximum extra papers (default: 100)

        exceptions:
            ValueError: number of papers already set.
        """
        extra = ceil(spare_percent * n / 100)
        extra = min(max(extra, min_extra), max_extra)  # threshold
        if self.numberToProduce >= 0:
            # TODO: consider relaxing this?
            raise ValueError("Number of papers already set: read-only")
        self.spec["numberToProduce"] = n + extra
        log.info(
            "deferred number of papers is now set to {}".format(self.numberToProduce)
        )

    def __str__(self):
        N = self.spec.get("numberOfQuestions", "TBD*")
        s = "Plom exam specification:\n  "
        s += "\n  ".join(
            (
                "Name of exam = {}".format(self.spec["name"]),
                "Long name of exam = {}".format(self.spec["longName"]),
                "Number of source versions = {}".format(self.spec["numberOfVersions"]),
                # "Public code (to prevent project collisions) = {}".format(self.spec["publicCode"]),
                # "Private random seed (for randomisation) = {}".format(self.spec["privateSeed"]),
                "Number of tests to produce = {}".format(self.numberToProduce),
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

    def verify(self, verbose=False):
        """Check that spec contains required attributes and insert default values."""
        self.verifySpec(verbose=verbose)

    def verifySpec(self, verbose=True):
        """Check that spec contains required attributes and insert default values.

        args:
            verbose: `None`/`False` for don't print; `True` is print to
                standard output; `"log"` means use logging mechanism.

        return:
            None

        exceptions:
            ValueError: with a message indicating the problem.
        """
        if verbose == "log":
            prnt = log.info
        elif verbose:
            prnt = print
        else:

            def prnt(x):
                return None  # no-op

        self.check_keys(print=prnt)
        self.check_name_and_production_numbers(print=prnt)
        lastPage = self.spec["numberOfPages"]
        self.check_IDPage(lastPage, print=prnt)
        self.check_doNotMarkPages(lastPage, print=prnt)
        prnt("Checking question groups")
        self.check_questions(print=prnt)
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

        self.check_pages(print=prnt)

    def checkCodes(self, verbose=True):
        """Add public and private codes if the spec doesn't already have them.

        args:
            verbose: `None`/`False` for don't print; `True` is print to
                standard output; `"log"` means use logging mechanism.
        """
        if verbose == "log":
            prnt = log.info
        elif verbose:
            prnt = print
        else:

            def prnt(x):
                return None  # no-op

        if "privateSeed" in self.spec:
            prnt("WARNING - privateSeed is already set. Not replacing this.")
        else:
            prnt("Assigning a privateSeed to the spec{}".format(chk))
            self.spec["privateSeed"] = str(random.randrange(0, 10**16)).zfill(16)

        if "publicCode" in self.spec:
            prnt("WARNING - publicCode is already set. Not replacing this.")
        else:
            prnt("Assigning a publicCode to the spec{}".format(chk))
            self.spec["publicCode"] = new_magic_code()

    def saveVerifiedSpec(self, *, verbose=False, basedir=Path("."), outfile=None):
        """Saves the verified spec to a particular name.

        Keyword Args:
            verbose (bool)
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

    def check_keys(self, print=print):
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

    def check_name_and_production_numbers(self, print=print):
        print("Checking specification name and numbers")
        print("  Checking names")
        if not self.spec["name"].isalnum() or len(self.spec["name"]) <= 0:
            raise ValueError(
                "Specification error - Test name must be an alphanumeric string of non-zero length."
            )
        print('    name "{}" has non-zero length{}'.format(self.spec["name"], chk))
        print('    name "{}" is alphanumeric{}'.format(self.spec["name"], chk))

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

        if self.numberToProduce == 0:
            raise ValueError('Specification error - "numberToProduce" cannot be zero.')

    def check_questions(self, print=print):
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
            # TODO: why not integers for key k?  See also elsewhere
            k = str(k)
            self.check_question_group(k, self.spec["numberOfPages"], print=print)

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

    def check_IDPage(self, lastPage, print=print):
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

    def check_doNotMarkPages(self, lastPage, print=print):
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

    def check_question_group(self, g, lastPage, print=print):
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

    def check_pages(self, print=print):
        print("Checking all pages used exactly once:")
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
            elif pageUse[p] != 1:
                raise ValueError(f"Page {p} overused - {pageUse[p]} times")
            print("  Page {} used once{}".format(p, chk))


def checkSolutionSpec(testSpec, solutionSpec):
    """Check the given solution spec against the validated test-spec and confirm its validity.

    Args:
        testSpec (dict): a validated plom test specification
        solutionSpec (dict): for example
        { "numberOfVersions": 2, "numberOfPages": 6, "numberOfQuestions": 3, 'solution': {'1': {'pages': [3]}, '2': {'pages': [4]}, '3': {'pages': [5]} } }

    Returns:
        Pair(Bool, str): Either (True,"All ok") or (False, Error message)
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
            f"Question keys incorrect = {list(solutionSpec['solution'].keys() )}",
        )
    # make sure each pagelist is contiguous an in range
    for q in range(1, solutionSpec["numberOfQuestions"] + 1):
        if str(q) not in solutionSpec["solution"]:
            return (
                False,
                f"Question keys incorrect = {list(solutionSpec['solution'].keys() )}",
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
