# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald

import logging
from math import ceil
import random
from pathlib import Path
import pkg_resources

import toml

specdir = "specAndDatabase"
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


class SpecVerifier:
    """Verify Plom exam specifications.

    Example specification:
    >>> raw = {
    ... 'name': 'plomdemo',
    ... 'longName': 'Midterm Demo using Plom',
    ... 'numberOfVersions': 2,
    ... 'numberOfPages': 6,
    ... 'numberToProduce': 20,
    ... 'numberToName': 10,
    ... 'numberOfQuestions': 3,
    ... 'privateSeed': '1001378822317872',
    ... 'publicCode': '270385',
    ... 'idPages': {'pages': [1]},
    ... 'doNotMark': {'pages': [2]},
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
      Name of test = plomdemo
      Long name of test = Midterm Demo using Plom
      Number of source versions = 2
      Number of tests to produce = 20
      Number of those to be printed with names = 10
      Number of pages = 6
      IDpages = [1]
      Do not mark pages = [2]
      Number of questions to mark = 3
        Question.1: pages [3], selected as shuffle, worth 5 marks
        Question.2: pages [4], selected as fix, worth 10 marks
        Question.3: pages [5, 6], selected as shuffle, worth 10 marks
      Test total = 25 marks


    We can verify that this input is valid:
    >>> spec.verifySpec()     # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
    Checking specification keys
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
        return pkg_resources.resource_string("plom", "templateTestSpec.toml")

    @classmethod
    def _template_as_string(cls):
        # TODO: or just use a triple-quoted inline string
        return cls._template_as_bytes().decode()

    @classmethod
    def create_template(cls, fname="testSpec.toml"):
        """Create a documented example exam specification."""
        template = cls._template_as_bytes()
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
            from plom.produce.demotools import getDemoClassListLength

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
    def demo(cls):
        return cls(toml.loads(cls._template_as_string()))

    @classmethod
    def from_toml_file(cls, fname="testSpec.toml"):
        """Initialize a SpecVerifier from a toml file."""
        return cls(toml.load(fname))

    @classmethod
    def load_verified(cls, fname=Path(specdir) / "verifiedSpec.toml"):
        """Initialize a SpecVerifier from the default verified toml file."""
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
        s = "Plom exam specification:\n  "
        s += "\n  ".join(
            (
                "Name of test = {}".format(self.spec["name"]),
                "Long name of test = {}".format(self.spec["longName"]),
                "Number of source versions = {}".format(self.spec["numberOfVersions"]),
                # "Public code (to prevent project collisions) = {}".format(self.spec["publicCode"]),
                # "Private random seed (for randomisation) = {}".format(self.spec["privateSeed"]),
                "Number of tests to produce = {}".format(self.numberToProduce),
                "Number of those to be printed with names = {}".format(
                    self.numberToName
                ),
                "Number of pages = {}".format(self.spec["numberOfPages"]),
                "IDpages = {}".format(self.spec["idPages"]["pages"]),
                "Do not mark pages = {}".format(self.spec["doNotMark"]["pages"]),
                "Number of questions to mark = {}".format(
                    self.spec["numberOfQuestions"]
                ),
            )
        )
        s += "\n"
        tot = 0
        for g in range(self.spec["numberOfQuestions"]):
            gs = str(g + 1)
            tot += self.spec["question"][gs]["mark"]
            s += "    Question.{}: pages {}, selected as {}, worth {} marks\n".format(
                gs,
                self.spec["question"][gs]["pages"],
                self.spec["question"][gs]["select"],
                self.spec["question"][gs]["mark"],
            )
        s += "  Test total = {} marks".format(tot)
        return s

    def get_public_spec_dict(self):
        """Return a copy of the spec dict with private info removed."""
        d = self.spec.copy()
        d.pop("privateSeed")
        return d

    def verifySpec(self, verbose=True):
        """Check that spec contains required attributes.

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
            prnt = lambda x: None  # no-op

        self.check_keys(print=prnt)
        self.check_name_and_production_numbers(print=prnt)
        lastPage = self.spec["numberOfPages"]
        self.check_IDPages(lastPage, print=prnt)
        self.check_doNotMark(lastPage, print=prnt)
        prnt("Checking question groups")
        for g in range(self.spec["numberOfQuestions"]):
            self.check_group(str(g + 1), lastPage, print=prnt)
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
            prnt = lambda x: None  # no-op

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

    def saveVerifiedSpec(self, verbose=False):
        """Saves the verified spec to a particular name."""
        if verbose:
            print('Saving the verified spec to "verifiedSpec.toml"')
        with open(Path(specdir) / "verifiedSpec.toml", "w+") as fh:
            fh.write("# This file is produced by the plom-build script.\n")
            fh.write(
                "# Do not edit this file. Instead edit testSpec.toml and rerun plom-build.\n"
            )
            toml.dump(self.spec, fh)

    # a couple of useful functions
    def isPositiveInt(self, s):
        try:
            n = int(s)
            if n > 0:
                return True
            else:
                return False
        except ValueError:
            return False

    def isNonNegInt(self, s):
        try:
            n = int(s)
            if n >= 0:
                return True
            else:
                return False
        except ValueError:
            return False

    def isContiguousListPosInt(self, l, lastPage):
        # check it is a list
        if type(l) is not list:
            return False
        # check each entry is 0<n<=lastPage
        for n in l:
            if not self.isPositiveInt(n):
                return False
            if n > lastPage:
                return False
        # check it is contiguous
        sl = set(l)
        for n in range(min(sl), max(sl) + 1):
            if n not in sl:
                return False
        # all tests passed
        return True

    def check_keys(self, print=print):
        """Check that spec contains required keys."""
        print("Checking specification keys")
        for x in [
            "name",
            "longName",
            "numberOfVersions",
            "numberOfPages",
            "numberToProduce",
            "numberToName",
            "numberOfQuestions",
            "idPages",
            "doNotMark",
        ]:
            if x not in self.spec:
                raise ValueError('Specification error - must contain "{}"'.format(x))
            print('  contains "{}"{}'.format(x, chk))
        if "1" not in self.spec["question"]:
            raise ValueError(
                'Specification error - must contain at least one question (i.e., "question.1")'
            )
        print('  contains at least one question (ie "question.1"){}'.format(chk))

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
        for x in ("numberOfVersions", "numberOfPages", "numberOfQuestions"):
            if not self.isPositiveInt(self.spec[x]):
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

        for k in range(1, self.spec["numberOfQuestions"] + 1):
            if not str(k) in self.spec["question"]:
                raise ValueError(
                    "Specification error - could not find question {}".format(k)
                )
            print(
                "    Found question {} of {}{}".format(
                    k, self.spec["numberOfQuestions"], chk
                )
            )

    def check_IDPages(self, lastPage, print=print):
        print("Checking IDpages")
        if "pages" not in self.spec["idPages"]:
            raise ValueError('IDpages error - could not find "pages" key')
        if not self.isContiguousListPosInt(self.spec["idPages"]["pages"], lastPage):
            raise ValueError(
                'IDpages error - "pages" = {} should be a list of positive integers in range'.format(
                    self.spec["idPages"]["pages"]
                )
            )
        print("    IDpages is contiguous list of positive integers" + chk)
        # check that page 1 is in there.
        if self.spec["idPages"]["pages"][0] != 1:
            print(
                "Warning - page 1 is not part if your ID pages - are you sure you want to do this?"
                + warn_mark
            )

    def check_doNotMark(self, lastPage, print=print):
        print("Checking DoNotMark-pages")
        if "pages" not in self.spec["doNotMark"]:
            raise ValueError('DoNotMark pages error - could not find "pages" key')
        if type(self.spec["doNotMark"]["pages"]) is not list:
            raise ValueError(
                'DoNotMark pages error - "pages" = {} should be a list of positive integers'.format(
                    self.spec["doNotMark"]["pages"]
                )
            )
        # should be a list of positive integers
        for n in self.spec["doNotMark"]["pages"]:
            if self.isPositiveInt(n) and n <= lastPage:
                pass
            else:
                raise ValueError(
                    'DoNotMark pages error - "pages" = {} should be a list of positive integers in range'.format(
                        self.spec["doNotMark"]["pages"]
                    )
                )
        print("    DoNotMark pages is list of positive integers" + chk)

    def check_group(self, g, lastPage, print=print):
        print("  Checking question group #{}".format(g))
        # each group has keys
        for x in ["pages", "select", "mark"]:
            if x not in self.spec["question"][g]:
                raise ValueError("Question error - could not find {} key".format(x))
        # check pages is contiguous list of positive integers
        if not self.isContiguousListPosInt(self.spec["question"][g]["pages"], lastPage):
            raise ValueError(
                "Question error - pages {} is not list of contiguous positive integers".format(
                    self.spec["question"][g]["pages"]
                )
            )
        print(
            "    pages {} is list of contiguous positive integers{}".format(
                self.spec["question"][g]["pages"], chk
            )
        )
        # check mark is positive integer
        if not self.isPositiveInt(self.spec["question"][g]["mark"]):
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
        # check select is "fix" or "shuffle"
        if self.spec["question"][g]["select"] not in ["fix", "shuffle"]:
            raise ValueError(
                'Question error - select {} is not "fix" or "shuffle"'.format(
                    self.spec["question"][g]["select"]
                )
            )
        print('    select is "fix" or "shuffle"' + chk)

    def check_pages(self, print=print):
        print("Checking all pages used exactly once:")
        pageUse = {k + 1: 0 for k in range(self.spec["numberOfPages"])}
        for p in self.spec["idPages"]["pages"]:
            pageUse[p] += 1
        for p in self.spec["doNotMark"]["pages"]:
            pageUse[p] += 1
        for g in range(self.spec["numberOfQuestions"]):
            for p in self.spec["question"][str(g + 1)]["pages"]:
                pageUse[p] += 1
        for p in range(1, self.spec["numberOfPages"] + 1):
            if pageUse[p] != 1:
                raise ValueError(
                    "Page overused - page {} used {} times".format(p, pageUse[p])
                )
            print("  Page {} used once{}".format(p, chk))
