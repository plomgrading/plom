# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald

import logging
from math import ceil
from pathlib import Path
import random
import sys

if sys.version_info >= (3, 7):
    import importlib.resources as resources
else:
    import importlib_resources as resources

import toml

import plom


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
        spec (dict): a spec dict.
        n (int): which question, current indexed from 1.

    TODO: change spec question keys to int.

    raises:
        ValueError: `n` is out of range.
    """
    n = int(n)
    if n < 1 or n > spec["numberOfQuestions"]:
        raise ValueError(f'question={n} out of range [1, {spec["numberOfQuestions"]}]')
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
    if type(l) is not list:
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
    if type(l) is not list:
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
    ... 'numberToName': 10,
    ... 'privateSeed': '1001378822317872',
    ... 'publicCode': '270385',
    ... 'idPage': 1,
    ... 'doNotMarkPages': [2],
    ... 'question': {
    ...     '1': {'pages': [3], 'mark': 5, 'select': 'shuffle'},
    ...     '2': {'pages': [4], 'mark': 10, 'select': 'fix'},
    ...     '3': {'pages': [5, 6], 'mark': 10, 'select': 'shuffle'}
    ...    }
    ... }
    >>> spec = SpecVerifier(raw)

    Here `spec` is an object representing a Plom exam specification:
    >>> print(spec)
    Plom exam specification:
      Name of exam = plomdemo
      Long name of exam = Midterm Demo using Plom
      Number of source versions = 2
      Number of tests to produce = 20
      Number of those to be printed with names = 10
      Number of pages = 6
      IDpage = 1
      Do not mark pages = [2]
      Number of questions to mark = 3
        Question.1: pages [3], selected as shuffle, worth 5 marks
        Question.2: pages [4], selected as fix, worth 10 marks
        Question.3: pages [5, 6], selected as shuffle, worth 10 marks
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
    """

    def __init__(self, d):
        """Initialize a SpecVerifier from a dict.

        Args:
            d (dict): an exam specification.
        """
        self.spec = d

    @classmethod
    def _template_as_bytes(cls):
        return resources.read_binary(plom, "templateTestSpec.toml")

    @classmethod
    def _template_as_string(cls):
        return resources.read_text(plom, "templateTestSpec.toml")

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
        s = cls._template_as_string()
        if num_to_produce:
            from plom.create.demotools import getDemoClassListLength

            # TODO: 20 and 10 in source file hardcoded here, use regex instead
            s = s.replace(
                "numberToProduce = 20",
                "numberToProduce = {}".format(num_to_produce),
            )
            classlist_len = getDemoClassListLength()
            if num_to_produce > classlist_len:
                raise ValueError(
                    "Demo size capped at classlist length of {}".format(classlist_len)
                )
            s = s.replace(
                "numberToName = 10",
                "numberToName = {}".format(min(num_to_produce // 2, classlist_len)),
            )
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
    def demo(cls):
        return cls(toml.loads(cls._template_as_string()))

    @classmethod
    def from_toml_file(cls, fname="testSpec.toml"):
        """Initialize a SpecVerifier from a toml file."""
        return cls(toml.load(fname))

    @classmethod
    def load_verified(cls, fname=specdir / "verifiedSpec.toml"):
        """Initialize a SpecVerifier from the default verified toml file.

        By default, this is the CWD/specAndDatabase/verifiedSpec.toml but
        you can override this with the `fname` kwarg.
        """
        # TODO: maybe we should do some testing here?
        return cls(toml.load(fname))

    # this allows spec["key"] instead of spec.spec["key"] for all
    def __getitem__(self, what):
        return self.spec[what]

    @property
    def number_to_produce(self):
        return self.spec["numberToProduce"]

    @property
    def number_to_name(self):
        return self.spec["numberToName"]

    # aliases to match the toml file
    numberToProduce = number_to_produce
    numberToName = number_to_name

    def set_number_papers_to_name(self, n):
        """Set previously-deferred number of named papers.

        exceptions:
            ValueError: number of named papers already set.
        """
        if self.numberToName >= 0:
            raise ValueError("Number of named papers already set: read-only")
        self.spec["numberToName"] = n
        log.info('deferred number of named papers now set to "{}"'.format(n))

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
                "Number of those to be printed with names = {}".format(
                    self.numberToName
                ),
                "Number of pages = {}".format(self.spec["numberOfPages"]),
                "IDpage = {}".format(self.spec["idPage"]),
                "Do not mark pages = {}".format(self.spec["doNotMarkPages"]),
                f"Number of questions to mark = {N}",
            )
        )
        s += "\n"
        for g in range(len(self.spec["question"])):
            # TODO: replace with integers
            gs = str(g + 1)
            s += "    Question.{}: pages {}, selected as {}, worth {} marks\n".format(
                gs,
                self.spec["question"][gs]["pages"],
                self.spec["question"][gs].get("select", "shuffle*"),
                self.spec["question"][gs]["mark"],
            )
        K = self.spec.get("totalMarks", "TBD*")
        s += f"  Exam total = {K} marks"
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
            self.spec["privateSeed"] = str(random.randrange(0, 10 ** 16)).zfill(16)

        if "publicCode" in self.spec:
            prnt("WARNING - publicCode is already set. Not replacing this.")
        else:
            prnt("Assigning a publicCode to the spec{}".format(chk))
            self.spec["publicCode"] = str(random.randrange(0, 10 ** 6)).zfill(6)

    def saveVerifiedSpec(self, verbose=False, basedir=Path(".")):
        """Saves the verified spec to a particular name."""
        f = basedir / specdir / "verifiedSpec.toml"
        if verbose:
            print(f'Saving the verified spec to "{f}"')
        with open(f, "w") as fh:
            fh.write("# This file is produced by the plom-create script.\n")
            fh.write(
                "# Do not edit this file. Instead edit testSpec.toml and rerun plom-create.\n"
            )
            toml.dump(self.spec, fh)

    def check_keys(self, print=print):
        """Check that spec contains required keys."""
        print("Checking mandatory specification keys")
        for x in [
            "name",
            "longName",
            "numberOfVersions",
            "numberOfPages",
            "numberToProduce",
            "numberToName",
            "idPage",
        ]:
            if x not in self.spec:
                raise ValueError('Specification error - must contain "{}"'.format(x))
            print(f'  contains "{x}"{chk}')
        if "1" not in self.spec["question"]:
            raise ValueError(
                'Specification error - must contain at least one question (i.e., "question.1")'
            )
        print('  contains at least one question (ie "question.1"){}'.format(chk))
        print("Checking optional specification keys")
        for x in ["doNotMarkPages", "totalMarks", "numberOfQuestions"]:
            if x in self.spec:
                print(f'  contains "{x}"{chk}')

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

        for x in ("numberToName", "numberToProduce"):
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

        if self.numberToProduce > 0:
            if self.numberToProduce < self.numberToName:
                raise ValueError(
                    "Specification error - insufficient papers: producing fewer papers {} than you wish to name {}. Produce more papers.".format(
                        self.numberToProduce, self.numberToName
                    )
                )
            print("    Producing enough papers to cover named papers" + chk)
            if self.numberToProduce < 1.05 * self.numberToName:
                print(
                    "WARNING: you are producing less than 5% un-named papers; you may want more spares"
                    + warn_mark
                )
            else:
                print("    Producing sufficiently many spare papers" + chk)

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
                f'Inconsistent: "[question.n]" blocks do not match numberOfQuestions={N}'
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
        if type(pages) is not list:
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
        g = str(g)  # TODO: why?
        print("  Checking question group #{}".format(g))
        required_keys = set(("pages", "mark"))
        optional_keys = set(("label", "select"))
        for k in required_keys:
            if k not in self.spec["question"][g]:
                raise ValueError('Question error - could not find "{}" key'.format(k))
        for k in self.spec["question"][g].keys():
            if k not in required_keys.union(optional_keys):
                raise ValueError('Question error - unexpected extra key "{}"'.format(k))
        pages = self.spec["question"][g]["pages"]
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
        if not isPositiveInt(self.spec["question"][g]["mark"]):
            raise ValueError(
                "Question error - mark {} is not a positive integer".format(
                    self.spec["question"][g]["mark"]
                )
            )
        print(
            "    mark {} is positive integer{}".format(
                self.spec["question"][g]["mark"], chk
            )
        )
        select = self.spec["question"][g].get("select")
        if not select:
            select = "shuffle"
            self.spec["question"][g]["select"] = select
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
            if pageUse[p] != 1:
                raise ValueError(
                    f"Page under/overused - page {p} used {pageUse[p]} times"
                )
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
