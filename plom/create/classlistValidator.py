# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2022 Andrew Rechnitzer
# Copyright (C) 2019-2022 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2020 Dryden Wiebe

from collections import defaultdict
import csv
import pandas
from plom.rules import validateStudentNumber


possible_sid_fields = ["id"]
possible_fullname_fields = ["name", "studentName", "fullName"]
possible_papernumber_fields = ["paperNum", "paperNumber"]

canvas_columns_format = ("Student", "ID", "SIS User ID", "SIS Login ID")
# combine all of these potential column headers into one casefolded list
potential_column_names = [
    x.casefold()
    for x in possible_sid_fields
    + possible_fullname_fields
    + possible_papernumber_fields
    + list(canvas_columns_format)
]


class PlomClasslistValidator:
    """The Plom Classlist Validator has methods to help ensure compatible classlists."""

    def __init__(
        self,
    ):
        pass

    def readClassList(self, filename):
        """Read classlist from filename and return as list of dicts

        Arguments:
            filename (pathlib.Path/str): csv-file to be loaded.

        Returns:
            list(dict): list of dictionaries (keys are column titles)
        """
        classAsDict = []
        with open(filename) as csvfile:
            # look at start of file to guess 'dialect', and then return to start of file
            sample = csvfile.read(1024)
            csvfile.seek(0)
            # guess the dialect
            dialect = csv.Sniffer().sniff(sample)
            # build the dict_reader
            reader = csv.DictReader(csvfile, dialect=dialect)
            # check it has a header - csv.sniffer.has_header is a bit flakey
            # instead check that we have some of the potential keys - careful of case
            column_names = [x.casefold() for x in reader.fieldnames]
            if any(x in potential_column_names for x in column_names):
                print("Appears to have reasonable header - continuing.")
            else:
                print(
                    "The header is either unreadable or has no fields that Plom recognises."
                )
                raise ValueError("No header")
            # now actually read the entries
            for row in reader:
                row["_src_line"] = reader.line_num
                classAsDict.append(row)
            # return the list
            return classAsDict

    def checkHeaders(self, rowFromDict):
        """Check existence of id and name columns in the classlist.

        Checks the column titles (as given by the supplied row from
        the classlist).  Tests for an id column, name-column, and an
        (optional) papernumber column. Names must be a single
        column. To avoid issues with upper and lower case, everything
        needs to be tested by casefolding.

        Arguments:
            rowFromDict (dict): a row from the classlist encoded as a dictionary.
                The keys give the column titles.

        Returns:
            dict: If errors then return {'success': False, 'errors': error-list},
                else return {'success': True, 'id': id_key, 'fullname': fullname_key, 'papernumber': papernumber_key/None}

        """
        id_keys = []
        fullname_keys = []
        papernumber_keys = []
        for x in rowFromDict.keys():
            cfx = x.casefold()
            if cfx in map(str.casefold, possible_sid_fields):
                id_keys.append(x)
            if cfx in map(str.casefold, possible_fullname_fields):
                fullname_keys.append(x)
            if cfx in map(str.casefold, possible_papernumber_fields):
                papernumber_keys.append(x)

        err = []
        # Must have at most one of each column
        if len(id_keys) > 1:
            err.append("Cannot have multiple id columns")
        if len(fullname_keys) > 1:  # must have exactly one such column
            err.append("Cannot have multiple full-name columns")
        if len(papernumber_keys) > 1:
            err.append("Cannot have multiple paper-number columns")
        # Must have an id column
        if not id_keys:
            err.append("Missing id column")
        # And a name (ie full name) column
        if not fullname_keys:
            err.append("Missing name column")
        # if no papernumber_key then put None into list for return value
        if not papernumber_keys:
            papernumber_keys.append(None)

        if err:
            return {"success": False, "errors": err}
        return {
            "success": True,
            "id": id_keys[0],
            "name": fullname_keys[0],
            "papernumber": papernumber_keys[0],
        }

    def check_ID_column(self, id_key, classList):
        """Check the ID column of the classlist"""
        err = []
        ids_used = defaultdict(list)
        for x in classList:
            # this is separate function - will be institution dependent.
            # will be better when we move to UIDs.
            idv = validateStudentNumber(x[id_key])
            if idv[0] is False:
                err.append([x["_src_line"], idv[1]])
            ids_used[x[id_key]].append(x["_src_line"])
        for x, v in ids_used.items():
            if len(v) > 1:
                err.append([v[0], f"ID '{x}' is used multiple times - on lines {v}"])
        if len(err) > 0:
            return (False, err)
        else:
            return (True, [])

    def check_papernumber_column(self, papernum_key, classList):
        """Check the papernumber column of the classlist"""
        if papernum_key is None:
            return (True, [])

        err = []
        numbers_used = defaultdict(list)
        for x in classList:
            try:
                int(x[papernum_key])
            except ValueError:
                err.append(
                    [
                        x["_src_line"],
                        f"Paper-number {x[papernum_key]} is not an integer",
                    ]
                )
            numbers_used[x[papernum_key]].append(x["_src_line"])
        for x, v in numbers_used.items():
            if len(v) > 1:
                err.append(
                    [v[0], f"Paper-number '{x}' is used multiple times - on lines {v}"]
                )
        if len(err) > 0:
            return (False, err)
        else:
            return (True, [])

    def check_name_column(self, fullname_key, classList):
        """Check name column return any warnings"""
        warn = []
        for x in classList:
            # check non-trivial length after removing spaces and commas
            tmp = x[fullname_key].replace(" ", "").replace(",", "")
            # warn if name-field is very short
            if len(tmp) < 2:  # Is this okay? TODO - decide a better bound here
                warn.append(
                    [x["_src_line"], f"Name '{tmp}' is very short  - please verify."]
                )
            # warn if non-latin char present
            try:
                tmp = x[fullname_key].encode("Latin-1")
            except UnicodeEncodeError:
                warn.append(
                    [
                        x["_src_line"],
                        f"Non-latin characters - {x[fullname_key]} - Apologies for the eurocentricity.",
                    ]
                )
        # return any warnings
        return warn

    def check_classlist_against_spec(self, spec, classlist_length):
        """
        Validate the classlist-length against spec parameters

        Args:
            spec (None/dict/SpecVerifier): an optional test specification,
                 if given then run additional classlist-related tests.
            classlist_length (int): the number of students in the classlist.

        Returns:
            list: if 'numberToProduce' is positive but less than classlist_length then returns [warning_message], else returns empty list.
        """
        if spec is None:
            return []
        elif spec["numberToProduce"] == -1:
            return []
        elif spec["numberToProduce"] < classlist_length:
            return [
                f"Classlist is long. Classlist contains {classlist_length} names, but spec:numberToProduce is {spec['numberToProduce']}"
            ]

    def validate_csv(self, filename, spec=None):
        """
        Validate the classlist csv and return summaries of any errors and warnings.

        Args:
            filename (str/pathlib.Path): a csv file from which to try to
                load the classlist.

        Keyword Args:
            spec (None/dict/SpecVerifier): an optional test specification,
                 if given then run additional classlist-related tests.

        Returns:
            tuple: (valid, warnings_and_errors) where "valid" is either
            True or False and "warnings_and_errors" is a list of
            dicts.  Each dict encodes a single warning or an error: see
            doc for precise format.  It is possible for "valid" to be True
            and still have non-empty "warnings_and_errors" for example
            when there are only warnings.
        """
        try:
            cl_as_dicts = self.readClassList(filename)
        except FileNotFoundError:
            return (False, [f"Cannot open {filename}"])
        except ValueError:
            return (False, [f"No header in {filename}"])
        except Exception as err:
            return (False, [f"Some other sort of error reading {filename} - {err}"])

        werr = []

        # check the headers - potentially un-recoverable errors here
        cl_header_info = self.checkHeaders(cl_as_dicts[0])
        if cl_header_info["success"] is False:  # format errors and bail-out
            for e in cl_header_info["errors"]:
                werr.append({"warn_or_err": "error", "werr_line": 0, "werr_text": e})
            return (False, werr)

        # collect all errors and warnings before bailing out.
        validity = True
        # check the ID column - again, potentially errors here (not just warnings)
        success, errors = self.check_ID_column(cl_header_info["id"], cl_as_dicts)
        if not success:  # format errors and set invalid
            validity = False
            for e in errors:
                werr.append(
                    {"warn_or_err": "error", "werr_line": e[0], "werr_text": e[1]}
                )

        # check the paperNumber column - again, potentially errors here (not just warnings)
        success, errors = self.check_papernumber_column(
            cl_header_info["papernumber"], cl_as_dicts
        )
        if not success:  # format errors and set invalid
            validity = False
            for e in errors[1]:
                werr.append(
                    {"warn_or_err": "error", "werr_line": e[0], "werr_text": e[1]}
                )
        # check against spec - only warnings returned
        for w in self.check_classlist_against_spec(spec, len(cl_as_dicts)):
            werr.append({"warn_or_err": "warning", "werr_line": 0, "werr_text": w})
        # check the name column - only warnings returned
        for w in self.check_name_column(cl_header_info["name"], cl_as_dicts):
            werr.append(
                {"warn_or_err": "warning", "werr_line": w[0], "werr_text": w[1]}
            )

        return (validity, werr)

    def check_is_canvas_csv(self, csv_file_name):
        """Detect if a csv file is likely a Canvas-exported classlist.

        Arguments:
            csv_file_name (pathlib.Path/str): csv file to be checked.

        Returns:
            bool: True if we think the input was from Canvas, based on
                presence of certain header names.  Otherwise False.
        """
        with open(csv_file_name) as csvfile:
            csv_reader = csv.DictReader(csvfile, skipinitialspace=True)
            csv_fields = csv_reader.fieldnames
        return all(x in csv_fields for x in canvas_columns_format)

    def check_is_non_canvas_csv(self, csv_file_name):
        """Read the csv file and check if id and name columns exist.

        1. Check if id is present or any of possible_sid_fields.
        2. Check if name is preset or any of possible_fullname_fields.

        Arguments:
            csv_file_name (pathlib.Path/str): the csv file.

        Returns:
            bool
        """

        student_info_df = pandas.read_csv(csv_file_name, dtype="object")
        print(
            'Loading from non-Canvas csv file to check file: "{0}"'.format(
                csv_file_name
            )
        )
        # strip excess whitespace from column names
        student_info_df.rename(
            columns=lambda x: str(x).strip(), inplace=True
        )  # avoid issues with blanks

        id_cols = []
        fullname_cols = []
        for x in student_info_df.columns:
            cfx = x.casefold()
            print(">>>> checking ", cfx)
            if cfx in map(str.casefold, possible_sid_fields):
                id_cols.append(x)
            if cfx in map(str.casefold, possible_fullname_fields):
                fullname_cols.append(x)

        if not id_cols:
            print(f"Cannot find an id column - {id_cols}")
            print("Columns present = {}".format(student_info_df.columns))
            return False
        elif len(id_cols) > 1:
            print(f"Multiple id columns - {id_cols}")
            print("Columns present = {}".format(student_info_df.columns))
            return False

        if not fullname_cols:
            print(f"Cannot find an name column - {fullname_cols}")
            print("Columns present = {}".format(student_info_df.columns))
            return False
        elif len(fullname_cols) > 1:
            print("Multiple name columns - {fullname_cols}")
            print("Columns present = {}".format(student_info_df.columns))
            return False

        return True

    @classmethod
    def print_classlist_warnings_errors(cls, warn_err):
        # separate into warn and err
        warn = [X for X in warn_err if X["warn_or_err"] == "warning"]
        err = [X for X in warn_err if X["warn_or_err"] != "warning"]
        # sort by line number
        warn.sort(key=lambda X: X["werr_line"])
        err.sort(key=lambda X: X["werr_line"])

        if warn:
            print("Classlist validation warnings:")
            for X in warn:
                print(f"\tline {X['werr_line']}: {X['werr_text']}")
        if err:
            print("Classlist validation errors:")
            for X in err:
                print(f"\tline {X['werr_line']}: {X['werr_text']}")
