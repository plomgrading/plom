# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020, 2023 Colin B. Macdonald

from pytest import raises

from PyQt5.QtCore import Qt
from plom.client.rubric_list import AddRubricBox


def test_AddRubricBox_add_new(qtbot):
    d = AddRubricBox(None, "user", 10, 1, "Q1", 1, 3, None)
    qtbot.addWidget(d)
    assert d.windowTitle().startswith("Add")
    qtbot.mouseClick(d.TE, Qt.LeftButton)
    qtbot.keyClicks(d.TE, "new rubric")
    qtbot.mouseClick(d.typeRB_relative, Qt.LeftButton)
    # don't care what the default is but start at 2...
    d.relative_value_SB.setValue(2)
    # then decrement x3, should skip zero and give -2
    qtbot.keyClick(d.relative_value_SB, Qt.Key_Down)
    qtbot.keyClick(d.relative_value_SB, Qt.Key_Down)
    qtbot.keyClick(d.relative_value_SB, Qt.Key_Down)
    # path = qtbot.screenshot(d)
    # assert False, path
    d.accept()
    out = d.gimme_rubric_data()
    assert out["kind"] == "relative"
    assert out["display_delta"] == "-2"
    assert out["value"] == -2
    assert isinstance(out["value"], int)
    assert out["text"] == "new rubric"


def test_AddRubricBox_modify(qtbot):
    rub = {
        "id": 1234,
        "kind": "relative",
        "display_delta": "+1",
        "value": 1,
        "text": "some text",
    }
    d = AddRubricBox(None, "user", 10, 1, "Q1", 1, 3, rub)
    qtbot.addWidget(d)
    assert d.windowTitle().startswith("Modify")
    assert not d.typeRB_neutral.isChecked()
    assert d.typeRB_relative.isChecked()

    # TODO: seems clicking doesn't work to set RadioButtons:
    qtbot.mouseClick(d.typeRB_neutral, Qt.LeftButton)
    qtbot.wait(10)
    qtbot.mouseClick(d.typeRB_neutral, Qt.LeftButton, delay=10)
    qtbot.wait(10)
    # times out after 5 seconds:
    # qtbot.waitUntil(lambda: d.typeRB_neutral.isChecked())
    # how to take a screenshot
    # path = qtbot.screenshot(d)
    # assert False, path
    # TODO: so instead we send it space bar
    qtbot.keyClicks(d.typeRB_neutral, " ")

    qtbot.keyClicks(d.TE, "-more")
    d.accept()
    out = d.gimme_rubric_data()
    assert out["kind"] == "neutral"
    assert out["display_delta"] == "."
    assert out["value"] == 0
    assert out["text"] == "some text-more"


def test_AddRubricBox_modify_invalid(qtbot):
    rub = {
        "text": "no id, lots of missing fields",
    }
    with raises(KeyError):
        AddRubricBox(None, "user", 10, 1, "Q1", 1, 3, rub)
    rub = {
        "id": 1234,
        "kind": "man_unkind",
        "display_delta": "+1",
        "value": 1,
        "out_of": 0,
        "text": "some text",
    }
    with raises(RuntimeError, match="unexpected kind"):
        AddRubricBox(None, "user", 10, 1, "Q1", 1, 3, rub)


def test_AddRubricBox_absolute_rubrics(qtbot):
    rub = {
        "id": 1234,
        "kind": "absolute",
        "display_delta": "1 of 3",
        "value": 1,
        "out_of": 3,
        "text": "some text",
    }
    d = AddRubricBox(None, "user", 10, 1, "Q1", 1, 3, rub, experimental=True)
    qtbot.addWidget(d)
    assert not d.typeRB_neutral.isChecked()
    assert not d.typeRB_relative.isChecked()
    assert d.typeRB_absolute.isChecked()
    qtbot.keyClick(d.abs_value_SB, Qt.Key_Up)
    qtbot.keyClick(d.abs_out_of_SB, Qt.Key_Up)
    qtbot.keyClick(d.abs_out_of_SB, Qt.Key_Up)
    d.accept()
    out = d.gimme_rubric_data()
    assert out["kind"] == "absolute"
    assert out["display_delta"] == "2 of 5"
    assert out["value"] == 2
    assert out["out_of"] == 5


def test_AddRubricBox_harvest(qtbot):
    rub = {
        "id": 1234,
        "kind": "relative",
        "display_delta": "+1",
        "value": 1,
        "text": "will be replaced",
    }
    d = AddRubricBox(None, "user", 10, 1, "Q1", 1, 3, rub, reapable=["AAA", "BBB"])
    qtbot.addWidget(d)
    qtbot.keyClicks(d.reapable_CB, "BBB")
    d.accept()
    out = d.gimme_rubric_data()
    assert out["text"] == "BBB"


def test_AddRubricBox_optional_meta_field(qtbot):
    rub = {
        "id": 1234,
        "kind": "neutral",
        "text": "some text",
        "meta": "meta",
    }
    d = AddRubricBox(None, "user", 10, 1, "Q1", 1, 2, rub)
    qtbot.addWidget(d)
    qtbot.keyClicks(d.TEmeta, " very meta")
    d.accept()
    out = d.gimme_rubric_data()
    assert out["meta"] == "meta very meta"


def test_AddRubricBox_optional_username(qtbot):
    d = AddRubricBox(None, "userA", 10, 1, "Q1", 1, 2, None)
    qtbot.addWidget(d)
    d.accept()
    out = d.gimme_rubric_data()
    assert out["username"] == "userA"

    # still owned by A if B modifies it
    d = AddRubricBox(None, "userB", 10, 1, "Q1", 1, 2, out)
    qtbot.addWidget(d)
    d.accept()
    out = d.gimme_rubric_data()
    assert out["username"] == "userA"


def test_AddRubricBox_parameterize(qtbot):
    for v in (1, 2):
        d = AddRubricBox(None, "user", 10, 1, "Q1", v, 2, None, experimental=True)
        qtbot.addWidget(d)
        qtbot.keyClicks(d.TE, "tex: foo  $x$")
        # move back to the middle
        qtbot.keyClick(d.TE, Qt.Key_Left)
        qtbot.keyClick(d.TE, Qt.Key_Left)
        qtbot.keyClick(d.TE, Qt.Key_Left)
        qtbot.keyClick(d.TE, Qt.Key_Left)
        # insert param1 in the middle
        qtbot.mouseClick(d.scopeButton, Qt.LeftButton)
        qtbot.mouseClick(d.addParameterButton, Qt.LeftButton)
        qtbot.wait(10)
        # highlight the "x" text and replace it with param2
        qtbot.keyClick(d.TE, Qt.Key_End)
        qtbot.keyClick(d.TE, Qt.Key_Left)
        qtbot.keyClick(d.TE, Qt.Key_Left, modifier=Qt.ShiftModifier)
        qtbot.mouseClick(d.addParameterButton, Qt.LeftButton)
        qtbot.wait(10)
        # path = qtbot.screenshot(d)
        # assert False, path
        d.accept()
        out = d.gimme_rubric_data()
        assert out["text"] == "tex: foo <param1> $<param2>$"
        # the current version is replaced with the highlighted text
        exp = ['x', ''] if v == 1 else ['', 'x']
        assert out["parameters"] == [['<param1>', ['', '']], ['<param2>', exp]]


def test_AddRubricBox_specific_to_version(qtbot):
    for v in (1, 2):
        d = AddRubricBox(None, "user", 10, 1, "Q1", v, 3, None)
        qtbot.addWidget(d)
        qtbot.keyClicks(d.TE, "foo")
        qtbot.mouseClick(d.scopeButton, Qt.LeftButton)
        qtbot.mouseClick(d.version_specific_cb, Qt.LeftButton)
        qtbot.keyClicks(d.version_specific_le, ", 3")
        d.accept()
        out = d.gimme_rubric_data()
        # by default, you get the current version upon clicking the checkbox
        # but users can type into the lineedit as well
        assert out["versions"] == [v, 3]


def test_AddRubricBox_change_existing_versions(qtbot):
    rub = {
        "id": 1234,
        "kind": "neutral",
        "text": "some text",
        "versions": [1, 3],
    }
    d = AddRubricBox(None, "user", 10, 1, "Q1", 1, 3, rub)
    qtbot.addWidget(d)
    qtbot.mouseClick(d.scopeButton, Qt.LeftButton)
    # unchecking
    qtbot.mouseClick(d.version_specific_cb, Qt.LeftButton)
    d.accept()
    out = d.gimme_rubric_data()
    assert out["versions"] == []

    d = AddRubricBox(None, "user", 10, 1, "Q1", 1, 3, rub)
    qtbot.addWidget(d)
    qtbot.mouseClick(d.scopeButton, Qt.LeftButton)
    qtbot.keyClicks(d.version_specific_le, ", 2")
    d.accept()
    out = d.gimme_rubric_data()
    assert set(out["versions"]) == set([1, 2, 3])


def test_AddRubricBox_add_to_group(qtbot):
    groups = ("(a)", "(b")
    for group in groups:
        d = AddRubricBox(None, "user", 10, 1, "Q1", 1, 2, None, groups=groups)
        qtbot.addWidget(d)
        qtbot.keyClicks(d.TE, "foo")
        qtbot.mouseClick(d.scopeButton, Qt.LeftButton)
        qtbot.mouseClick(d.group_checkbox, Qt.LeftButton)
        qtbot.keyClicks(d.group_combobox, group)
        d.accept()
        out = d.gimme_rubric_data()
        assert out["tags"] == f"group:{group}"


def test_AddRubricBox_add_to_group_exclusive(qtbot):
    groups = ("(a)", "(b")
    for group in groups:
        d = AddRubricBox(None, "user", 10, 1, "Q1", 1, 2, None, groups=groups)
        qtbot.addWidget(d)
        qtbot.keyClicks(d.TE, "foo")
        qtbot.mouseClick(d.scopeButton, Qt.LeftButton)
        qtbot.mouseClick(d.group_checkbox, Qt.LeftButton)
        qtbot.keyClicks(d.group_combobox, group)
        qtbot.mouseClick(d.group_excl, Qt.LeftButton)
        d.accept()
        out = d.gimme_rubric_data()
        assert out["tags"] == f"group:{group} exclusive:{group}"


def test_AddRubricBox_group_without_group_list(qtbot):
    rub = {
        "id": 1234,
        "kind": "relative",
        "display_delta": "+1",
        "value": 1,
        "text": "some text",
        "tags": "unrelated_tag group:(bar)",
    }
    d = AddRubricBox(None, "user", 10, 1, "Q1", 1, 2, rub)
    qtbot.addWidget(d)
    qtbot.mouseClick(d.scopeButton, Qt.LeftButton)
    qtbot.mouseClick(d.group_excl, Qt.LeftButton)
    d.accept()
    out = d.gimme_rubric_data()
    assert "unrelated_tag" in out["tags"]
    assert "group:(bar) exclusive:(bar)" in out["tags"]


def test_AddRubricBox_change_group_make_exclusive(qtbot):
    rub = {
        "id": 1234,
        "kind": "relative",
        "display_delta": "+1",
        "value": 1,
        "text": "some text",
        "tags": "group:(b)",
    }
    groups = ("(a)", "(b")
    for group in groups:
        d = AddRubricBox(None, "user", 10, 1, "Q1", 1, 2, rub, groups=groups)
        qtbot.addWidget(d)
        qtbot.mouseClick(d.scopeButton, Qt.LeftButton)
        qtbot.keyClicks(d.group_combobox, group)
        qtbot.mouseClick(d.group_excl, Qt.LeftButton)
        d.accept()
        out = d.gimme_rubric_data()
        assert out["tags"] == f"group:{group} exclusive:{group}"


def test_AddRubricBox_change_group_remove_exclusive(qtbot):
    rub = {
        "id": 1234,
        "kind": "relative",
        "display_delta": "+1",
        "value": 1,
        "text": "some text",
        "tags": "group:(b) exclusive:(b)",
    }
    groups = ("(a)", "(b")
    for group in groups:
        d = AddRubricBox(None, "user", 10, 1, "Q1", 1, 2, rub, groups=groups)
        qtbot.addWidget(d)
        qtbot.mouseClick(d.scopeButton, Qt.LeftButton)
        assert d.group_checkbox.isChecked()
        assert d.group_excl.isChecked()
        qtbot.keyClicks(d.group_combobox, group)
        qtbot.mouseClick(d.group_excl, Qt.LeftButton)
        d.accept()
        out = d.gimme_rubric_data()
        assert out["tags"] == f"group:{group}"


def test_AddRubricBox_group_too_complicated(qtbot):
    rub = {
        "id": 1234,
        "kind": "relative",
        "display_delta": "+1",
        "value": 1,
        "text": "some text",
    }
    rub["tags"] = "group:(a) group:(b)"
    d = AddRubricBox(None, "user", 10, 1, "Q1", 1, 2, rub)
    qtbot.addWidget(d)
    qtbot.mouseClick(d.scopeButton, Qt.LeftButton)
    assert d.group_checkbox.isChecked()
    assert not d.group_excl.isChecked()
    assert not d.group_checkbox.isEnabled()
    assert not d.group_excl.isEnabled()
    d.accept()
    out = d.gimme_rubric_data()
    assert out["tags"] == rub["tags"]

    rub["tags"] = "group:(a) exclusive:(b)"
    d = AddRubricBox(None, "user", 10, 1, "Q1", 1, 2, rub)
    qtbot.addWidget(d)
    qtbot.mouseClick(d.scopeButton, Qt.LeftButton)
    assert d.group_checkbox.isChecked()
    assert d.group_excl.isChecked()
    assert not d.group_checkbox.isEnabled()
    assert not d.group_excl.isEnabled()
    d.accept()
    out = d.gimme_rubric_data()
    assert out["tags"] == rub["tags"]

    rub["tags"] = "group:(a) group:(b) exclusive:(b)"
    d = AddRubricBox(None, "user", 10, 1, "Q1", 1, 2, rub)
    qtbot.addWidget(d)
    qtbot.mouseClick(d.scopeButton, Qt.LeftButton)
    assert d.group_checkbox.isChecked()
    assert d.group_excl.isChecked()
    assert not d.group_checkbox.isEnabled()
    assert not d.group_excl.isEnabled()
    d.accept()
    out = d.gimme_rubric_data()
    assert out["tags"] == rub["tags"]

    rub["tags"] = "exclusive:(b)"
    d = AddRubricBox(None, "user", 10, 1, "Q1", 1, 2, rub)
    qtbot.addWidget(d)
    qtbot.mouseClick(d.scopeButton, Qt.LeftButton)
    assert not d.group_checkbox.isChecked()
    assert d.group_excl.isChecked()
    assert not d.group_checkbox.isEnabled()
    assert not d.group_excl.isEnabled()
    d.accept()
    out = d.gimme_rubric_data()
    assert out["tags"] == rub["tags"]

    rub["tags"] = "group:(a) exclusive:(a) exclusive:(b)"
    d = AddRubricBox(None, "user", 10, 1, "Q1", 1, 2, rub, groups=["(a)"])
    qtbot.addWidget(d)
    qtbot.mouseClick(d.scopeButton, Qt.LeftButton)
    assert d.group_checkbox.isChecked()
    assert d.group_excl.isChecked()
    assert not d.group_checkbox.isEnabled()
    assert not d.group_excl.isEnabled()
    # path = qtbot.screenshot(d)
    # assert False, path
    d.accept()
    out = d.gimme_rubric_data()
    assert out["tags"] == rub["tags"]
