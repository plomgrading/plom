# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Andrew Rechnitzer

import csv

from plom.rules import validateStudentNumber


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


class PlomCLValidator:
    def __init__(
        self,
    ):
        pass

    def readClassList(self, filename):
        classAsDict = []
        with open(filename) as csvfile:
            # look at start of file to guess 'dialect', and then return to start of file
            sample = csvfile.read(1024)
            csvfile.seek(0)
            # guess the dialect
            dialect = csv.Sniffer().sniff(sample)
            # check it has a header
            if csv.Sniffer().has_header(sample) is False:
                raise ValueError("No header")
            # now read the entries
            reader = csv.DictReader(csvfile, dialect=dialect)
            l = 1
            for row in reader:
                l += 1
                row["line"] = l
                classAsDict.append(row)
            # return the list
            return classAsDict

    def getGivenNameKeys(self, casefoldKeyList):
        rl = []
        for n in possible_given_name_fields:
            if n.casefold() in casefoldKeyList:
                rl.append(n)
        return rl

    def getSurnameKeys(self, casefoldKeyList):
        rl = []
        for n in possible_surname_fields:
            if n.casefold() in casefoldKeyList:
                rl.append(n)
        return rl

    def checkHeaders(self, rowFromDict):
        theKeys = rowFromDict.keys()
        casefoldKeyList = [x.casefold() for x in theKeys]
        gnk = self.getGivenNameKeys(casefoldKeyList)
        snk = self.getSurnameKeys(casefoldKeyList)

        err = []
        if "id" not in theKeys:  # must have an id column
            err.append("Missing id column")
        if "studentName" in theKeys:  # if studentName then no other name column
            if len(gnk) > 0:
                err.append(
                    "Cannot have both 'studentName' column and '{}' column(s)".format(
                        gnk
                    )
                )
            if len(snk) > 0:
                err.append(
                    "Cannot have both 'studentName' column and '{}' column(s)".format(
                        snk
                    )
                )
        else:  # must have one surname col and one given name col
            if len(snk) == 0:
                err.append("Must have one surname column")
            elif len(snk) > 1:
                err.append(
                    "Must have one surname column - you have supplied '{}'".format(snk)
                )
            if len(gnk) == 0:
                err.append("Must have at least one given-name column")
            elif len(gnk) > 1:
                err.append(
                    "Must have one given-name column - you have supplied '{}'".format(
                        gnk
                    )
                )
        if len(err) > 0:
            return [False, err]
        if len(snk) == 0 and len(gnk) == 0:
            return [True, "id", "studentName"]
        else:
            return [True, "id", snk[0], gnk[0]]

    def check_ID_StudentName(self, classList):
        """Check ID and StudentName when student-name is a single field"""
        err = []
        warn = []
        for x in classList:
            # this is separate function - will be institution dependent.
            # will be better when we move to UIDs.
            idv = validateStudentNumber(x["id"])
            if idv[0] is False:
                err.append([x["line"], idv[1]])
            # check non-trivial length after removing spaces and commas
            tmp = x["studentName"].replace(" ", "").replace(",", "")
            # any other checks?
            if len(tmp) < 2:  # what is sensible here?
                err.append([x["line"], "Missing name"])
            # warn if non-latin char present
            try:
                tmp = x["studentName"].encode("Latin-1")
            except UnicodeEncodeError:
                warn.append([x["line"], f"Non-latin characters - {x['studentName']}"])
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
                err.append([x["line"], idv[1]])
            # check non-trivial length after removing spaces and commas
            tmp = x[surnameKey].replace(" ", "").replace(",", "")
            if len(tmp) < 2:  # what is sensible here?
                err.append([x["line"], "Missing surname"])
            tmp = x[givenNameKey].replace(" ", "").replace(",", "")
            if len(tmp) < 2:  # what is sensible here?
                err.append([x["line"], "Missing given name"])
            # warn if non-latin char present
            try:
                tmp = (x[surnameKey] + x[givenNameKey]).encode("Latin-1")
            except UnicodeEncodeError:
                warn.append([x["line"], f"Non-latin characters - {x['studentName']}"])
        if len(err) > 0:
            return [False, warn, err]
        else:
            return [True, warn]

    def validate_csv(self, filename, spec=None):
        """
        Validate the classlist csv and return (True, []) or (False, warnings_and_errors)
        If spec given then run tests against that too.
        """

        try:
            cl_as_dicts = self.readClassList(filename)
        except FileNotFoundError:
            return (False, [f"Cannot open {filename}"])
        except ValueError:
            return (False, [f"No header in {filename}"])
        except Exception:
            return (False, [f"Some other sort of error reading {filename}"])

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
                        "werr_text": f"Classlist too short. Classlist contains {len(cl_as_dicts)} names, but spec:numberToName is {spec['numberToName']}",
                    }
                )
                return (False, werr)  # Fail out here

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
