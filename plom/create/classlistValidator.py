# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2022 Andrew Rechnitzer
# Copyright (C) 2019-2022 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2020 Dryden Wiebe

import csv
import pandas
from plom.rules import validateStudentNumber


possible_sid_fields = ["id"]
possible_one_name_fields = ["studentName"]

possible_surname_fields = ["surname", "familyName", "lastName"]
possible_given_name_fields = [
    "name",
    "givenName",
    "firstName",
    "givenNames",
    "firstNames",
    "preferredName",
    "preferredNames",
    "nickName",
    "nickNames",
]
canvas_columns_format = ("Student", "ID", "SIS User ID", "SIS Login ID")
# combine all of these potential column headers into one casefolded list
potential_column_names = [
    x.casefold()
    for x in possible_sid_fields
    + possible_one_name_fields
    + possible_surname_fields
    + possible_given_name_fields
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
        """Check existence of given-name and surname columns in the classlist.

        Checks the column titles (as given by the supplied row from the classlist).
        Tests for an 'id' column, and then name-columns. Names are either single-column
        or surname/givenname column pair.  To avoid issues with upper
        and lower case, everything needs to be tested by casefolding.

        Arguments:
            rowFromDict (dict): a row from the classlist encoded as a dictionary.
                The keys give the column titles.

        Returns:
            list: If errors then return [False, error-list],
                if single name column then [True, 'id', 'studentName'] ,
                if surname/given name column then [True, "id", surname_key, given_name_key]
        """
        theKeys = rowFromDict.keys()
        casefoldKeyList = [x.casefold() for x in theKeys]
        id_keys = [x for x in possible_sid_fields if x.casefold() in casefoldKeyList]
        given_name_keys = [
            x for x in possible_given_name_fields if x.casefold() in casefoldKeyList
        ]
        surname_keys = [
            x for x in possible_surname_fields if x.casefold() in casefoldKeyList
        ]

        err = []
        if "id" not in casefoldKeyList:  # must have an id column
            err.append("Missing id column")

        if "studentName" in theKeys:  # if studentName then no other name column
            if len(given_name_keys) > 0:
                err.append(
                    "Cannot have both 'studentName' column and '{}' column(s)".format(
                        given_name_keys
                    )
                )
            if len(surname_keys) > 0:
                err.append(
                    "Cannot have both 'studentName' column and '{}' column(s)".format(
                        surname_keys
                    )
                )
        else:  # must have one surname col and one given name col
            if len(surname_keys) == 0:
                err.append("Must have one surname column")
            elif len(surname_keys) > 1:
                err.append(
                    "Must have one surname column - you have supplied '{}'".format(
                        surname_keys
                    )
                )
            if len(given_name_keys) == 0:
                err.append("Must have at least one given-name column")
            elif len(given_name_keys) > 1:
                err.append(
                    "Must have one given-name column - you have supplied '{}'".format(
                        given_name_keys
                    )
                )
        if len(err) > 0:
            return [False, err]
        if len(surname_keys) == 0 and len(given_name_keys) == 0:
            return [True, id_keys[0], "studentName"]
        else:
            return [True, id_keys[0], surname_keys[0], given_name_keys[0]]

    def check_ID_StudentName(self, classList):
        """Check ID and StudentName when student-name is a single field"""
        err = []
        warn = []
        for x in classList:
            # this is separate function - will be institution dependent.
            # will be better when we move to UIDs.
            idv = validateStudentNumber(x["id"])
            if idv[0] is False:
                err.append([x["_src_line"], idv[1]])
            # check non-trivial length after removing spaces and commas
            tmp = x["studentName"].replace(" ", "").replace(",", "")
            # any other checks?
            if len(tmp) < 2:  # what is sensible here?
                err.append([x["_src_line"], "Missing name"])
            # warn if non-latin char present
            try:
                tmp = x["studentName"].encode("Latin-1")
            except UnicodeEncodeError:
                warn.append(
                    [
                        x["_src_line"],
                        f"Non-latin characters - {x['studentName']} - Apologies for the eurocentricity.",
                    ]
                )
        if len(err) > 0:
            return [False, warn, err]
        else:
            return [True, warn]

    def check_ID_Surname_GivenName(self, surnameKey, givenNameKey, classList):
        """Check ID and StudentName when student-name is two-fields"""
        err = []
        warn = []
        for x in classList:
            # this is separate function - will be institution dependent.
            # will be better when we move to UIDs.
            idv = validateStudentNumber(x["id"])
            if idv[0] is False:
                err.append([x["_src_line"], idv[1]])
            # check non-trivial length after removing spaces and commas
            tmp = x[surnameKey].replace(" ", "").replace(",", "")
            if len(tmp) < 2:  # what is sensible here?
                err.append([x["_src_line"], "Missing surname"])
            tmp = x[givenNameKey].replace(" ", "").replace(",", "")
            if len(tmp) < 2:  # what is sensible here?
                err.append([x["_src_line"], "Missing given name"])
            # warn if non-latin char present
            try:
                tmp = (x[surnameKey] + x[givenNameKey]).encode("Latin-1")
            except UnicodeEncodeError:
                warn.append(
                    [
                        x["_src_line"],
                        f"Non-latin characters - {x['studentName']} - Apologies for the eurocentricity.",
                    ]
                )
        if len(err) > 0:
            return [False, warn, err]
        else:
            return [True, warn]

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

        cl_head = self.checkHeaders(cl_as_dicts[0])
        if cl_head[0] is False:
            for e in cl_head[1]:
                werr.append({"warn_or_err": "error", "werr_line": 0, "werr_text": e})
            return (False, werr)

        # if spec is present run sanity tests against that
        if spec is not None:
            if spec["numberToName"] == -1:
                # nothing to check - will use all names in classlist
                pass
            elif spec["numberToName"] > len(cl_as_dicts):
                werr.append(
                    {
                        "warn_or_err": "error",
                        "werr_line": 0,
                        "werr_text": f"Classlist is too short. Classlist contains {len(cl_as_dicts)} names, but spec:numberToName is {spec['numberToName']}",
                    }
                )
                return (False, werr)  # Fail out here
            elif spec["numberToName"] < len(cl_as_dicts):  # see issue 927
                werr.append(
                    {
                        "warn_or_err": "warning",
                        "werr_line": 0,
                        "werr_text": f"Classlist is longer than numberToName. Classlist contains {len(cl_as_dicts)} names, but spec:numberToName is {spec['numberToName']}",
                    }
                )

            if spec["numberToProduce"] == -1:
                # nothing to check - will produce as many as in classlist
                pass
            elif spec["numberToProduce"] < len(cl_as_dicts):
                werr.append(
                    {
                        "warn_or_err": "warning",
                        "werr_line": 0,
                        "werr_text": f"Classlist is long. Classlist contains {len(cl_as_dicts)} names, but spec:numberToProduce is {spec['numberToProduce']}",
                    }
                )

        if len(cl_head) == 3:  # is true, id, studentName
            cid = self.check_ID_StudentName(cl_as_dicts)
        elif len(cl_head) == 4:  # is true, id, surname, givenname
            cid = self.check_ID_Surname_GivenName(cl_head[2], cl_head[3], cl_as_dicts)
        else:
            return (False, werr)
        # now look at the errors / warnings
        if len(cid[1]) > 0:
            for w in cid[1]:
                werr.append(
                    {"warn_or_err": "warning", "werr_line": w[0], "werr_text": w[1]}
                )
        if cid[0] is False:  # big errors in id/name checking
            for e in cid[2]:
                werr.append(
                    {"warn_or_err": "error", "werr_line": e[0], "werr_text": e[1]}
                )
            return (False, werr)
        else:
            return (True, werr)

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
        """Read the csv file and check if id and appropriate student name exist.

        1. Check if id is present.
        2. Check if studentName is preset.
        3. If not, check for given name and surname in the document.

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

        if "id" not in [x.casefold() for x in student_info_df.columns]:
            print('Cannot find "id" column')
            print("Columns present = {}".format(student_info_df.columns))
            return False

        # if we have don't have  then we are good to go.
        if "studentName" not in student_info_df.columns:

            # we need one of some approx of last-name field
            firstname_column_title = None
            for column_title in student_info_df.columns:
                if column_title.casefold() in (
                    x.casefold() for x in possible_surname_fields
                ):
                    print('"{}" column present'.format(column_title))
                    firstname_column_title = column_title
                    break
            if firstname_column_title is None:
                print(
                    'Cannot find column to use for "surname", tried: {}'.format(
                        ", ".join(possible_surname_fields)
                    )
                )
                print("Columns present = {}".format(student_info_df.columns))
                return False

            # we need one of some approx of given-name field
            lastname_column_title = None
            for column_title in student_info_df.columns:
                if column_title.casefold() in (
                    x.casefold() for x in possible_given_name_fields
                ):
                    print('"{}" column present'.format(column_title))
                    lastname_column_title = column_title
                    break
            if lastname_column_title is None:
                print(
                    'Cannot find column to use for "given name", tried: {}'.format(
                        ", ".join(possible_given_name_fields)
                    )
                )
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