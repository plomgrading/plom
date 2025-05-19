# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2024 Andrew Rechnitzer
# Copyright (C) 2019-2025 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2024 Aden Chan

from collections import defaultdict
import csv
from pathlib import Path
from typing import Any, Sequence

from plom.rules import validateStudentID

# important classlist headers - all casefolded
sid_field = "id".casefold()
fullname_field = "name".casefold()
papernumber_field = "paper_number".casefold()

canvas_columns_format = ("Student", "ID", "SIS User ID", "SIS Login ID")


class PlomClasslistValidator:
    """The Plom Classlist Validator has methods to help ensure compatible classlists."""

    def readClassList(self, filename: Path | str) -> list[dict[str, Any]]:
        """Read classlist from filename and return as list of dicts.

        Arguments:
            filename: csv-file to be loaded.

        Returns:
            List of dictionaries (keys are column titles).  We canonicalize the
            header names so that we have at least ``"id", "name", "paper_number"``
            and ``"_src_line"``, the latter used for error messages in further
            validation.  The ``"paper_number"`` key might or might not be present.

        Raises:
            ValueError: the file does not contain a header line, or if the file
                does not contain any of the header names we might expect, or
                there is some other problem with the headers.
        """
        classAsDicts = []
        # Note newline: https://docs.python.org/3/library/csv.html#id4
        with open(filename, newline="") as csvfile:
            # look at start of file to guess 'dialect', and then return to start of file
            # TODO: what if there isn't 1024 bytes?
            sample = csvfile.read(1024)
            csvfile.seek(0)
            # guess the dialect
            dialect = csv.Sniffer().sniff(sample)
            # build the dict_reader
            reader = csv.DictReader(csvfile, dialect=dialect)

            id_key, name_key, paper_number_key = self._checkHeaders(reader.fieldnames)

            # now actually read the entries
            for row in reader:
                row["_src_line"] = reader.line_num
                # canonicalize cases, replacing whatever case was there before
                row[sid_field] = row.pop(id_key)
                row[fullname_field] = row.pop(name_key)
                if paper_number_key is not None:
                    row[papernumber_field] = row.pop(paper_number_key)
                classAsDicts.append(row)
            return classAsDicts

    def _checkHeaders(self, headers: Sequence[str]) -> list[str | None]:
        """Check existence of id and name columns in the classlist.

        Checks the column titles (as given by the supplied row from
        the classlist).  Tests for an id column, name-column, and the
        papernumber column. Names must be a single column. To avoid
        issues with upper and lower case, everything needs to be tested
        by casefolding.

        Arguments:
            headers: the list of keys of the column titles.

        Returns:
            A list of the key names, dict of the form
            ``[id_key, fullname_key, papernumber_key]``.
            If there is no ``"paper_number"`` column, then the
            ``paper_number_key`` will be `None`.

        Raises:
            ValueError: with a message about what column header problem we found.
                You might need to call multiple times to get all the problems:
                this fails fast on the first problem found.
        """
        id_keys = []
        fullname_keys = []
        papernumber_keys: list[str | None] = []
        for x in headers:
            cfx = x.casefold()
            if cfx == sid_field:
                id_keys.append(x)
            if cfx == fullname_field:
                fullname_keys.append(x)
            if cfx == papernumber_field:
                papernumber_keys.append(x)

        # Check for repeated column names, Issue #3667.
        if len(id_keys) > 1:
            raise ValueError(
                f'Column "id" is repeated multiple times in the '
                f'CSV header: {", ".join(x for x in headers)}'
            )
        if len(fullname_keys) > 1:  # must have exactly one such column
            raise ValueError(
                f'Column "name" is repeated multiple times in the '
                f'CSV header: {", ".join(x for x in headers)}'
            )
        if len(papernumber_keys) > 1:
            raise ValueError(
                f'Column "paper_number" is repeated multiple times in the '
                f'CSV header: {", ".join(x for x in headers)}'
            )
        # Must have an id, name and paper_number columns
        if not id_keys:
            raise ValueError(f"Missing 'id' column in columns {headers}")
        if not fullname_keys:
            raise ValueError(f"Missing 'name' column in columns {headers}")
        if not papernumber_keys:
            # Issue #2273
            # raise ValueError("Missing paper_number column")
            papernumber_keys = [None]

        # We explicitly allow casefolding (but could change our minds?)
        # See #3822 and #1140.
        # if id_keys != [sid_field]:
        #     raise ValueError(f"'id' present but incorrect case; header: {headers}")
        # if fullname_keys != [fullname_field]:
        #     raise ValueError(f"'name' present but incorrect case; header: {headers}")

        return [id_keys[0], fullname_keys[0], papernumber_keys[0]]

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
                if len(str(x)) == 0:  # for #3091 - explicit error for blank ID
                    err.append([v[0], f"Blank ID appears on multiple lines {v}"])
                else:
                    err.append(
                        [v[0], f"ID '{x}' is used multiple times - on lines {v}"]
                    )
        if len(err) > 0:
            return (False, err)
        else:
            return (True, [])

    @staticmethod
    def is_paper_number_sentinel(x: int | float | str | None) -> bool:
        """True if the input is None, blank, -1 or '-1'.

        Note: zero is not sentinel.
        """
        return x in ("", None, "-1", -1)

    def check_paper_number_column(self, papernum_key, classList) -> tuple[bool, list]:
        """Check the papernumber column of the classlist.

        Entries must either be blank, or integers >= -1.
        Note that:
            * no integer >=0 can be used twice, and
            * blank or -1 are sentinel values used to indicate 'do not prename'
        """

        def is_an_int(x: int | float | str) -> bool:
            """True if input can be converted to an int."""
            try:
                int(x)
            except ValueError:
                return False
            return True

        def is_nearly_a_non_negative_int(x: int | float | str) -> bool:
            """True input can be converted to a non-negative float which has integer value.

            eg - returns true for "1.0", but false for "0.9", "-2", "-2.1", "13.2" and so on.
            """
            try:
                v = float(x)
            except ValueError:
                return False
            return (int(v) == v) and (v >= 0)

        err = []
        numbers_used = defaultdict(list)
        for x in classList:
            pn = x.get(papernum_key, None)
            # see #3099 - we can reuse papernum = -1 since it is a sentinel value, so ignore any -1's
            if self.is_paper_number_sentinel(pn):
                continue  # notice that this handles pn being None.
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
            werr.append({"warn_or_err": "error", "werr_line": 0, "werr_text": f"{err}"})
            return (False, werr)
        except Exception as err:
            e = f"Some other sort of error reading {filename}: {type(err)} {err}"
            werr.append({"warn_or_err": "error", "werr_line": 0, "werr_text": e})
            return (False, werr)

        if len(cl_as_dicts) == 0:
            # Headers were OK, followed by no data. That's degenerate, but valid.
            e = "CSV file seems to be empty (headers only)"
            werr.append({"warn_or_err": "warn", "werr_line": 0, "werr_text": e})

        # collect all errors and warnings before bailing out.
        validity = True
        # check the ID column - again, potentially errors here (not just warnings)
        success, errors = self.check_ID_column(sid_field, cl_as_dicts)
        if not success:  # format errors and set invalid
            validity = False
            for e in errors:
                werr.append(
                    {"warn_or_err": "error", "werr_line": e[0], "werr_text": e[1]}
                )

        # check the paperNumber column - again, potentially errors here (not just warnings)
        success, errors = self.check_paper_number_column(papernumber_field, cl_as_dicts)
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
        for w in self.check_name_column(fullname_field, cl_as_dicts):
            werr.append(
                {"warn_or_err": "warning", "werr_line": w[0], "werr_text": w[1]}
            )

        # TODO: return cl_as_dicts as well?
        return (validity, werr)

    def check_is_canvas_csv(self, csv_file_name: Path | str) -> bool:
        """Detect if a csv file is likely a Canvas-exported classlist.

        Arguments:
            csv_file_name: csv file to be checked.

        Returns:
            True if we think the input was from Canvas, based on
            presence of certain header names.  Otherwise False.
        """
        # Note newline: https://docs.python.org/3/library/csv.html#id4
        with open(csv_file_name, newline="") as f:
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
        # Note newline: https://docs.python.org/3/library/csv.html#id4
        with open(csv_file_name, newline="") as f:
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
