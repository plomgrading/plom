# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021-2024 Colin B. Macdonald
# Copyright (C) 2024 Andrew Rechnitzer

from copy import deepcopy
from pathlib import Path
import sys

from pytest import raises

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

from plom import SpecVerifier, get_question_label


raw = SpecVerifier.demo().spec


def test_spec_demo():
    s = SpecVerifier.demo()
    assert s.number_to_produce


def test_spec_verify():
    s = SpecVerifier.demo()
    s.verifySpec(verbose=False)


def test_spec_verify_quiet():
    s = SpecVerifier.demo()
    s.verify()


def test_removed_numberToName():
    s = SpecVerifier.demo()
    s.spec["numberToName"] = 10
    with raises(ValueError):
        s.verify()


def test_spec_wrong_number_questions():
    r = raw.copy()
    r["numberOfQuestions"] = 2
    with raises(ValueError, match="not match"):
        SpecVerifier(r).verify()
    r["numberOfQuestions"] = 10
    with raises(ValueError, match="not match"):
        SpecVerifier(r).verify()


def test_spec_autocount_questions():
    r = raw.copy()
    r.pop("numberOfQuestions")
    s = SpecVerifier(r)
    s.verify()
    assert s["numberOfQuestions"] == 3


def test_spec_question_pages_non_positive():
    r = deepcopy(raw)
    r["question"]["1"]["pages"] = [-1]
    with raises(ValueError, match="not a positive int"):
        SpecVerifier(r).verify()


def test_spec_pages_not_even():
    r = deepcopy(raw)
    r["numberOfPages"] = 7
    r["question"]["3"]["pages"] = [5, 6, 7]
    with raises(ValueError, match="even"):
        SpecVerifier(r).verify()


def test_spec_question_pages_non_contiguous():
    r = deepcopy(raw)
    r["numberOfPages"] = 16
    r["question"]["1"]["pages"] = [3, 16]
    with raises(ValueError, match="contiguous"):
        SpecVerifier(r).verify()


def test_spec_question_pages_out_of_range():
    r = deepcopy(raw)
    r["question"]["1"]["pages"] = [14, 15, 16, 17]
    with raises(ValueError, match="range"):
        SpecVerifier(r).verify()


def test_spec_wrong_total_marks():
    r = raw.copy()
    r["totalMarks"] += 1
    with raises(ValueError):
        SpecVerifier(r).verify()


def test_spec_autocount_missing_total_marks():
    r = raw.copy()
    y = r.pop("totalMarks")
    s = SpecVerifier(r)
    s.verify()
    assert s.spec["totalMarks"] == y


def test_spec_negatives_still_pass():
    r = raw.copy()
    r["numberToProduce"] = -1
    SpecVerifier(r).verify()


def test_spec_setting_adds_spares():
    r = raw.copy()
    r["numberToProduce"] = -1
    s = SpecVerifier(r)
    s.set_number_papers_add_spares(16)
    # creates some spares
    assert s.numberToProduce > 16
    s.verify()


def test_spec_question_extra_key():
    r = deepcopy(raw)
    r["question"]["1"]["libel"] = "defamation"
    with raises(ValueError):
        SpecVerifier(r).verify()


def test_spec_question_missing_key():
    required_keys = ("pages", "mark")
    for k in required_keys:
        r = deepcopy(raw)
        r["question"]["1"].pop(k)
        with raises(ValueError):
            SpecVerifier(r).verify()


def test_spec_question_select_key_takes_default():
    r = deepcopy(raw)
    # the demo spec does not have a select key for Q1.  but leave this
    # here in case we change the demo spec in the future
    r["question"]["1"].pop("select", None)
    # make sure pop fails gracefully - see #2558
    s = SpecVerifier(r)
    s.verify()
    assert s["question"]["1"]["select"] == "shuffle"


def test_spec_valid_shortname():
    r = raw.copy()
    r["name"] = "test42"
    SpecVerifier(r).verify()
    r["name"] = "udder_score"
    SpecVerifier(r).verify()
    r["name"] = "42nd"
    SpecVerifier(r).verify()
    r["name"] = "dotty.exam"
    SpecVerifier(r).verify()
    r["name"] = "hy-phen"
    SpecVerifier(r).verify()


def test_spec_invalid_shortname():
    r = raw.copy()
    r["name"] = "no spaces allowed"
    with raises(ValueError):
        SpecVerifier(r).verify()
    r["name"] = ""
    with raises(ValueError):
        SpecVerifier(r).verify()


def test_spec_longname_slash_issue1364():
    r = raw.copy()
    r["longName"] = 'Math123 / Bio321 Midterm ∫∇·Fdv — "have fun!"😀'
    SpecVerifier(r).verify()


def test_spec_invalid_select():
    r = deepcopy(raw)
    r["question"]["1"]["select"] = "consult the oracle"


def test_spec_question_label_printer():
    sd = SpecVerifier.demo()
    r = deepcopy(raw)
    r["question"]["1"]["label"] = "Track 1"
    r["question"]["2"]["label"] = ""
    s = SpecVerifier(r)
    assert get_question_label(s, 1) == "Track 1"
    assert get_question_label(s, 2) == "Q2"
    assert get_question_label(s, 3) == get_question_label(sd, 3)
    # OO works too
    assert s.get_question_label(1) == "Track 1"
    assert s.get_question_label(2) == "Q2"
    assert s.get_question_label(3) == get_question_label(sd, 3)


def test_spec_question_label_str_index():
    s = SpecVerifier.demo()
    assert s.get_question_label("1") == s.get_question_label(1)


def test_spec_question_label_printer_errors():
    s = SpecVerifier.demo()
    N = s["numberOfQuestions"]
    with raises(ValueError):
        get_question_label(s, N + 1)
    with raises(ValueError):
        get_question_label(s, -1)
    with raises(ValueError):
        get_question_label(s, 0)


def test_spec_question_string():
    s = SpecVerifier.demo()
    with raises(ValueError):
        get_question_label(s, "c")
    assert get_question_label(s, "1") == get_question_label(s, 1)


def test_spec_unique_labels():
    r = deepcopy(raw)
    r["question"]["1"]["label"] = "ExA"
    r["question"]["2"]["label"] = "ExA"
    with raises(ValueError):
        SpecVerifier(r).verify()


def test_spec_label_too_long():
    r = deepcopy(raw)
    r["question"]["1"]["label"] = "Distrust That Particular Flavour"
    with raises(ValueError):
        SpecVerifier(r).verify()


def test_spec_shared_page_not_allowed():
    r = deepcopy(raw)
    r["question"]["2"]["pages"] = [3, 4]
    with raises(ValueError, match="overused"):
        SpecVerifier(r).verify(_legacy=True)
    with raises(ValueError, match="overused"):
        SpecVerifier(r).verify(_legacy=False)


def test_spec_shared_page_explicit_disallowed():
    r = deepcopy(raw)
    r["allowSharedPages"] = False
    r["question"]["2"]["pages"] = [3, 4]
    with raises(ValueError, match="overused"):
        SpecVerifier(r).verify(_legacy=True)
    with raises(ValueError, match="overused"):
        SpecVerifier(r).verify(_legacy=False)


def test_spec_shared_page_must_be_explicitly_allowed():
    r = deepcopy(raw)
    r["allowSharedPages"] = True
    r["question"]["2"]["pages"] = [3, 4]
    SpecVerifier(r).verify(_legacy=False)


def test_spec_DNM_page_cannot_be_shared():
    r = deepcopy(raw)
    r["allowSharedPages"] = True
    r["question"]["1"]["pages"] = [2, 3]
    with raises(ValueError, match="shared.*DNM.*question"):
        SpecVerifier(r).verify(_legacy=False)


def test_spec_legacy_overused_page():
    r = deepcopy(raw)
    r["question"]["1"]["pages"] = [1, 2, 3]
    with raises(ValueError, match="overused"):
        SpecVerifier(r).verify()
    r = deepcopy(raw)
    r["question"]["3"]["pages"] = [4]
    with raises(ValueError, match="unused"):
        SpecVerifier(r).verify()


def test_spec_donotmark_default():
    r = deepcopy(raw)
    r.pop("doNotMarkPages")
    r["question"]["1"]["pages"] = [2, 3]
    s = SpecVerifier(r)
    s.verify()
    assert s["doNotMarkPages"] == []


def test_spec_invalid_donotmark():
    r = deepcopy(raw)
    r["doNotMarkPages"] = "Fragments of a Hologram Rose"
    with raises(ValueError) as e:
        SpecVerifier(r).verify()
    assert "not a list" in e.value.args[0]
    r["doNotMarkPages"] = [2, -17]
    with raises(ValueError) as e:
        SpecVerifier(r).verify()
    assert "not a positive integer" in e.value.args[0]
    r["doNotMarkPages"] = [2, 42]
    with raises(ValueError) as e:
        SpecVerifier(r).verify()
    assert "larger than" in e.value.args[0]


def test_spec_str():
    st = str(SpecVerifier.demo())
    assert st.startswith("Plom exam specification")


def test_spec_str_missing_numberOfQuestions():
    r = deepcopy(raw)
    r.pop("numberOfQuestions")
    s = SpecVerifier(r)
    st = str(s)
    assert "TBD*" in st
    s.verify()
    st = str(s)
    assert "TBD*" not in st


def test_spec_str_missing_totalMarks():
    r = deepcopy(raw)
    r.pop("totalMarks")
    s = SpecVerifier(r)
    st = str(s)
    assert "TBD*" in st
    s.verify()
    st = str(s)
    assert "TBD*" not in st


def test_spec_str_missing_select_in_q1():
    s = SpecVerifier.demo()
    assert s["question"]["1"].get("select", None) is None
    st = str(s)
    assert "shuffle*" in st
    s.verify()
    st = str(s)
    assert "shuffle*" not in st


def test_spec_zero_question_issue617():
    s = SpecVerifier.demo()
    s["question"]["1"]["mark"] = 0
    with raises(ValueError):
        s.verify()


def test_spec_page_to_group_label():
    s = SpecVerifier.demo()
    s.group_label_from_page(1) == "ID"
    s.group_label_from_page(2) == "DNM"
    s.group_label_from_page(3) == "Q.1"
    s.group_label_from_page(4) in ("Q.2", "Q(2)")
    s.group_label_from_page(5) in ("Q.3", "Ex.3")
    s.group_label_from_page(6) in ("Q.3", "Ex.3")
    with raises(KeyError):
        s.group_label_from_page(100)
    with raises(KeyError):
        s.group_label_from_page("3")


def test_spec_not_legacy_format():
    old = """
        name = "oldtemplate"
        longName = "An old pre-v10 template, deprecated but not yet an error"
        numberOfVersions = 2
        numberOfPages = 4
        totalMarks = 10

        numberToProduce = 20
        idPage = 1
        doNotMarkPages = [2]

        [question.1]
        pages = [3]
        mark = 5

        [question.2]
        pages = [4]
        mark = 5
    """
    A = tomllib.loads(old)
    sv = SpecVerifier(A)
    sv.verify()


def test_spec_legacy_dupe_question_fails_to_load(tmpdir):
    tmpdir = Path(tmpdir)
    old = """
        name = "oldtemplate"
        longName = "old pre-v10 template, with erroneously repeated question"
        numberOfVersions = 2
        numberOfPages = 4
        totalMarks = 10

        numberToProduce = 20
        idPage = 1
        doNotMarkPages = [2]

        [question.1]
        pages = [3]
        mark = 5

        [question.1]
        pages = [4]
        mark = 5
    """
    with open(tmpdir / "Fawlty.toml", "w") as f:
        f.write(old)
    with raises(tomllib.TOMLDecodeError):
        SpecVerifier.from_toml_file(tmpdir / "Fawlty.toml")
