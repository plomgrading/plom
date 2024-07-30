# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2024 Andrew Rechnitzer
# Copyright (C) 2019-2024 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2024 Aden Chan

from __future__ import annotations

from collections import defaultdict
import csv
from pathlib import Path
from typing import Any

from plom.rules import validateStudentID

# important classlist headers - all casefolded
sid_field = "id".casefold()
fullname_field = "name".casefold()
papernumber_field = "paper_number".casefold()

canvas_columns_format = ("Student", "ID", "SIS User ID", "SIS Login ID")
# combine all of these potential column headers into one casefolded list
potential_column_names = [
    sid_field,
    fullname_field,
    papernumber_field,
] + [x.casefold() for x in canvas_columns_format]


class PlomClasslistValidator:
    """The Plom Classlist Validator has methods to help ensure compatible classlists."""

    def readClassList(self, filename: Path | str) -> list[dict[str, Any]]:
        """Read classlist from filename and return as list of dicts.

        Arguments:
            filename: csv-file to be loaded.

        Returns:
            List of dictionaries (keys are column titles).
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
            if not reader.fieldnames:
                raise ValueError("No header")
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

    def checkHeaders(self, rowFromDict: dict[str, Any]) -> dict[str, Any]:
        """Check existence of id and name columns in the classlist.

        Checks the column titles (as given by the supplied row from
        the classlist).  Tests for an id column, name-column, and the
        papernumber column. Names must be a single column. To avoid
        issues with upper and lower case, everything needs to be tested
        by casefolding.

        Arguments:
            rowFromDict: a row from the classlist encoded as a dictionary.
                The keys give the column titles.

        Returns:
            dict: If errors then return ``{'success': False, 'errors': error-list}``,
            else return ``{'success': True, 'id': id_key, 'fullname': fullname_key, 'papernumber': papernumber_key}``.
            If there is no ``"paper_number"`` column, then the
            ``paper_number_key`` will be `None`.
        """
        id_keys = []
        fullname_keys = []
        papernumber_keys: list[str | None] = []
        headers = list(rowFromDict.keys())
        for x in headers:
            cfx = x.casefold()
            if cfx == sid_field:
                id_keys.append(x)
            if cfx == fullname_field:
                fullname_keys.append(x)
            if cfx == papernumber_field:
                papernumber_keys.append(x)

        err = []
        # Must have at most one of each column
        if len(id_keys) > 1:
            err.append("Cannot have multiple id columns")
        if len(fullname_keys) > 1:  # must have exactly one such column
            err.append("Cannot have multiple name columns")
        if len(papernumber_keys) > 1:
            err.append("Cannot have multiple paper number columns")
        # Must have an id, name and paper_number columns
        if not id_keys:
            err.append(f"Missing 'id' column in columns {headers}")
        if not fullname_keys:
            err.append(f"Missing 'name' column in columns {headers}")
        if not papernumber_keys:
            # Issue #2273
            # err.append("Missing paper number column")
            papernumber_keys = [None]

        if err:
            return {"success": False, "errors": err}
        return {
            "success": True,
            "id": id_keys[0],
            "name": fullname_keys[0],
            "papernumber": papernumber_keys[0],
        }

    def check_ID_column(self, id_key, classList) -> tuple[bool, list]:
        """Check the ID column of the classlist."""
        err = []
        ids_used = defaultdict(list)
        for x in classList:
            # this is separate function - will be institution dependent.
            # will be better when we move to UIDs.
            idv = validateStudentID(x[id_key])
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

    def check_papernumber_column(self, papernum_key, classList) -> tuple[bool, list]:
        """Check the papernumber column of the classlist.

        Entries must either be blank, or integers >= -1.
        Note that:
            * no integer >=0 can be used twice, and
            * blank or -1 are sentinel values used to indicate 'do not prename'
        """

        def is_sentinel(x):
            return x in ["", "-1"]

        def is_an_int(x):
            try:
                int(x)
            except ValueError:
                return False
            return True

        def is_nearly_a_non_negative_int(x):
            try:
                v = float(x)
            except ValueError:
                return False
            return (int(v) == v) and (v >= 0)

        err = []
        numbers_used = defaultdict(list)
        for x in classList:
            pn = x[papernum_key]
            # see #3099 - we can reuse papernum = -1 since it is a sentinel value, so ignore any -1's
            if is_sentinel(pn):
                continue
            if is_an_int(pn):
                if int(pn) < 0:
                    err.append(
                        [
                            x["_src_line"],
                            f"Paper-number {x[papernum_key]} must be a non-negative integer, or blank or '-1' to indicate 'do not prename'",
                        ]
                    )
            else:
                if is_nearly_a_non_negative_int(x[papernum_key]):
                    err.append(
                        [
                            x["_src_line"],
                            f"Paper-number {x[papernum_key]} is nearly, but not quite, a non-negative integer",
                        ]
                    )
                    continue
                else:
                    err.append(
                        [
                            x["_src_line"],
                            f"Paper-number {x[papernum_key]} is not a non-negative integer",
                        ]
                    )
                    continue

            # otherwise store the used papernumber.
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

    def check_name_column(self, fullname_key, classList) -> list:
        """Check name column return any warnings."""
        warn = []
        for x in classList:
            # check non-trivial length after removing spaces and commas
            tmp = x[fullname_key].replace(" ", "").replace(",", "")
            # warn if name-field is very short
            if len(tmp) < 2:  # TODO - decide a better bound here
                warn.append(
                    [x["_src_line"], f"Name '{tmp}' is very short  - please verify."]
                )
        return warn

    def check_classlist_against_spec(self, spec, classlist_length: int) -> list[str]:
        """Validate the classlist-length against spec parameters.

        Args:
            spec (None/dict/SpecVerifier): an optional test specification,
                if given then run additional classlist-related tests.
            classlist_length: the number of students in the classlist.

        Returns:
            If 'numberToProduce' is positive but less than classlist_length
            then returns [warning_message], else returns empty list.
        """
        if spec is None:
            return []
        elif spec["numberToProduce"] == -1:
            return []
        elif spec["numberToProduce"] < classlist_length:
            return [
                f"Classlist is long. Classlist contains {classlist_length} names, but spec:numberToProduce is {spec['numberToProduce']}"
            ]
        return []

    def validate_csv(
        self, filename: Path | str, *, spec=None
    ) -> tuple[bool, list[dict[str, Any]]]:
        """Validate the classlist csv and return summaries of any errors and warnings.

        Args:
            filename: a csv file from which to try to load the classlist.

        Keyword Args:
            spec (None/dict/SpecVerifier): an optional test specification,
                 if given then run additional classlist-related tests.

        Returns:
            ``(valid, warnings_and_errors)`` where "valid" is either
            True or False and "warnings_and_errors" is a list of
            dicts.  Each dict encodes a single warning or an error: see
            code for precise format.  It is possible for "valid" to be True
            and still have non-empty "warnings_and_errors" for example
            when there are only warnings.
        """
        werr = []
        try:
            cl_as_dicts = self.readClassList(filename)
        except (ValueError, FileNotFoundError) as err:
            e = f"Can't read {filename}: {err}"
            werr.append({"warn_or_err": "error", "werr_line": 0, "werr_text": e})
            return (False, werr)
        except Exception as err:
            e = f"Some other sort of error reading {filename}: {err}"
            werr.append({"warn_or_err": "error", "werr_line": 0, "werr_text": e})
            return (False, werr)

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
        if cl_header_info["papernumber"] is not None:
            success, errors = self.check_papernumber_column(
                cl_header_info["papernumber"], cl_as_dicts
            )
            if not success:  # format errors and set invalid
                validity = False
                for e in errors:
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

    def check_is_canvas_csv(self, csv_file_name: Path | str) -> bool:
        """Detect if a csv file is likely a Canvas-exported classlist.

        Arguments:
            csv_file_name: csv file to be checked.

        Returns:
            True if we think the input was from Canvas, based on
            presence of certain header names.  Otherwise False.
        """
        with open(csv_file_name) as f:
            csv_reader = csv.DictReader(f, skipinitialspace=True)
            csv_fields = csv_reader.fieldnames
            if csv_fields is None:
                csv_fields = []
        return all(x in csv_fields for x in canvas_columns_format)

    def check_is_non_canvas_csv(self, csv_file_name: Path | str) -> bool:
        """Read the csv file and check if id and name columns exist.

        1. Check if id is present or any of possible_sid_fields.
        2. Check if name is preset or any of possible_fullname_fields.

        Arguments:
            csv_file_name: the csv file.

        Returns:
            bool
        """
        print(f'Loading from non-Canvas csv file to check file: "{csv_file_name}"')
        with open(csv_file_name) as f:
            csv_reader = csv.DictReader(f, skipinitialspace=True)
            column_names = csv_reader.fieldnames
            if column_names is None:
                column_names = []
        # strip excess whitespace from column names to avoid issues with blanks
        column_names = [str(x).strip() for x in column_names]

        id_cols = []
        fullname_cols = []
        papernumber_cols = []
        for x in column_names:
            cfx = x.casefold()
            print(">>>> checking ", cfx)
            if cfx == sid_field:
                id_cols.append(x)
            if cfx == fullname_field:
                fullname_cols.append(x)
            if cfx == papernumber_field:
                papernumber_cols.append(x)

        if not id_cols:
            print(f"Cannot find an id column - {id_cols}")
            print(f"Columns present = {column_names}")
            return False
        elif len(id_cols) > 1:
            print(f"Multiple id columns - {id_cols}")
            print(f"Columns present = {column_names}")
            return False

        if not fullname_cols:
            print(f"Cannot find an name column - {fullname_cols}")
            print(f"Columns present = {column_names}")
            return False
        elif len(fullname_cols) > 1:
            print("Multiple name columns - {fullname_cols}")
            print(f"Columns present = {column_names}")
            return False

        if not papernumber_cols:
            # Issue #2273
            # print(f"Cannot find a paper number column - {papernumber_cols}")
            # print(f"Columns present = {column_names}")
            # return False
            pass
        elif len(papernumber_cols) > 1:
            print("Multiple paper number columns - {papernumber_cols}")
            print(f"Columns present = {column_names}")
            return False

        return True

    @classmethod
    def print_classlist_warnings_errors(cls, warn_err: list[dict[str, Any]]) -> None:
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
