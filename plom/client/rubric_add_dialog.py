# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2023 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2021 Forest Kobayashi

import re
import sys
from typing import Any, Dict, List, Tuple

if sys.version_info >= (3, 9):
    from importlib import resources
else:
    import importlib_resources as resources

from PyQt6.QtCore import Qt, QRegularExpression
from PyQt6.QtGui import (
    QColor,
    QPixmap,
    QSyntaxHighlighter,
    QTextCharFormat,
    QRegularExpressionValidator,
)


from PyQt6.QtWidgets import (
    QCheckBox,
    QLabel,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QInputDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QRadioButton,
    QToolButton,
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

import plom.client.icons
from plom.misc_utils import next_in_longest_subsequence
from .useful_classes import InfoMsg, WarnMsg, SimpleQuestion


class SignedSB(QSpinBox):
    # add an explicit sign to spinbox and no 0
    # range is from -N,..,-1,1,...N
    # note - to fix #1561 include +/- N in this range.
    # else 1 point questions become very problematic
    def __init__(self, maxMark):
        super().__init__()
        self.setRange(-maxMark, maxMark)
        self.setValue(1)

    def stepBy(self, steps):
        self.setValue(self.value() + steps)
        # to skip 0.
        if self.value() == 0:
            self.setValue(self.value() + steps)

    def textFromValue(self, n):
        t = QSpinBox().textFromValue(n)
        if n > 0:
            return "+" + t
        else:
            return t


class SubstitutionsHighlighter(QSyntaxHighlighter):
    """Highlight tex prefix and parametric substitutions."""

    def __init__(self, *args, **kwargs):
        # TODO: initial value of subs?
        self.subs = []
        super().__init__(*args, **kwargs)

    def highlightBlock(self, txt):
        """Highlight tex prefix and matches in our substitution list.

        Args:
            txt (str): the text to be highlighted.

        TODO: use colours from the palette?
        """
        # TODO: can we set a popup: "v2 value: 'x'"
        # reset format
        self.setFormat(0, len(txt), QTextCharFormat())
        # highlight tex: at beginning
        if txt.casefold().startswith("tex:"):
            self.setFormat(0, len("tex:"), QColor("grey"))
        # highlight parametric substitutions
        for s in self.subs:
            for match in re.finditer(s, txt):
                # print(f"matched on {s} at {match.start()} to {match.end()}!")
                frmt = QTextCharFormat()
                frmt.setForeground(QColor("teal"))
                # TODO: not sure why this doesn't work?
                # frmt.setToolTip('v2 subs: "TODO"')
                self.setFormat(match.start(), match.end() - match.start(), frmt)

    def setSubs(self, subs):
        self.subs = subs
        self.rehighlight()


class WideTextEdit(QTextEdit):
    """Just like QTextEdit but with hacked sizeHint() to be wider.

    Also, hacked to ignore shift-enter.
    """

    def sizeHint(self):
        sz = super().sizeHint()
        sz.setWidth(sz.width() * 2)
        return sz

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.KeyboardModifier.ShiftModifier and (
            event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter
        ):
            # print("WideTextEdit: ignoring Shift-Enter event")
            event.ignore()
            return
        return super().keyPressEvent(event)


class AddRubricBox(QDialog):
    def __init__(
        self,
        parent,
        username,
        maxMark,
        question_number,
        question_label,
        version,
        maxver,
        com=None,
        *,
        groups=[],
        reapable=[],
        experimental=False,
        add_to_group=None,
    ):
        """Initialize a new dialog to edit/create a comment.

        Args:
            parent (QWidget): the parent window.
            username (str)
            maxMark (int)
            question_number (int)
            question_label (str)
            version (int)
            maxver (int)
            com (dict/None): if None, we're creating a new rubric.
                Otherwise, this has the current comment data.

        Keyword Args:
            annotator_size (QSize/None): size of the parent annotator
            groups (list): optional list of existing/recommended group
                names that the rubric could be added to.
            add_to_group (str/None): preselect this group in the scope
                settings when creating a new rubric.  This must be one
                of the `groups` list above.
            reapable (list): these are used to "harvest" plain 'ol text
                annotations and morph them into comments.
            experimental (bool): whether to enable experimental or advanced
                features.

        Raises:
            none expected!
        """
        super().__init__(parent)

        self.use_experimental_features = experimental
        self.question_number = question_number
        self.version = version
        self.maxver = maxver

        if com:
            self.setWindowTitle("Modify rubric")
        else:
            self.setWindowTitle("Add new rubric")

        self.reapable_CB = QComboBox()
        self.TE = WideTextEdit()
        self.hiliter = SubstitutionsHighlighter(self.TE)
        self.relative_value_SB = SignedSB(maxMark)
        self.TEtag = QLineEdit()
        self.TEmeta = WideTextEdit()
        # cannot edit these
        self.label_rubric_id = QLabel("Will be auto-assigned")
        self.Luser = QLabel()

        sizePolicy = QSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding
        )
        sizePolicy.setVerticalStretch(3)
        self.TE.setSizePolicy(sizePolicy)
        sizePolicy = QSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        sizePolicy.setVerticalStretch(1)
        self.TEmeta.setSizePolicy(sizePolicy)

        flay = QFormLayout()
        flay.addRow("Text", self.TE)
        lay = QHBoxLayout()
        lay.addItem(
            QSpacerItem(
                32, 10, QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Minimum
            )
        )
        lay.addWidget(QLabel("Choose text from page:"))
        lay.addWidget(self.reapable_CB)
        reapable_layout = lay
        flay.addRow("", lay)

        frame = QFrame()
        vlay = QVBoxLayout(frame)
        vlay.setContentsMargins(0, 0, 0, 0)
        b = QRadioButton("neutral")
        b.setToolTip("more of a comment, this rubric does not change the mark")
        b.setChecked(True)
        vlay.addWidget(b)
        self.typeRB_neutral = b
        lay = QHBoxLayout()
        b = QRadioButton("relative")
        b.setToolTip("changes the mark up or down by some number of points")
        lay.addWidget(b)
        self.typeRB_relative = b
        # lay.addWidget(self.DE)
        lay.addWidget(self.relative_value_SB)
        self.relative_value_SB.valueChanged.connect(b.click)
        # self.relative_value_SB.clicked.connect(b.click)
        lay.addItem(
            QSpacerItem(16, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        )
        lay.addItem(
            QSpacerItem(
                48, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
            )
        )
        vlay.addLayout(lay)
        hlay = QHBoxLayout()
        b = QRadioButton("absolute")
        abs_tooltip = "Indicates a score as a part of a maximum possible amount"
        b.setToolTip(abs_tooltip)
        hlay.addWidget(b)
        self.typeRB_absolute = b
        _ = QSpinBox()
        _.setRange(0, maxMark)
        _.setValue(0)
        _.valueChanged.connect(b.click)
        # _.clicked.connect(b.click)
        hlay.addWidget(_)
        self.abs_value_SB = _
        _ = QLabel("out of")
        _.setToolTip(abs_tooltip)
        # _.clicked.connect(b.click)
        hlay.addWidget(_)
        _ = QSpinBox()
        _.setRange(0, maxMark)
        _.setValue(maxMark)
        _.valueChanged.connect(b.click)
        # _.clicked.connect(b.click)
        hlay.addWidget(_)
        self.abs_out_of_SB = _
        hlay.addItem(
            QSpacerItem(
                48, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
            )
        )
        vlay.addLayout(hlay)
        flay.addRow("Marks", frame)

        # scope
        self.scopeButton = QToolButton()
        self.scopeButton.setCheckable(True)
        self.scopeButton.setChecked(False)
        self.scopeButton.setAutoRaise(True)
        self.scopeButton.setText("Scope")
        self.scopeButton.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.scopeButton.clicked.connect(self.toggle_scope_elements)
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel)
        self.scope_frame = frame
        flay.addRow(self.scopeButton, frame)
        vlay = QVBoxLayout(frame)
        cb = QCheckBox(
            f'specific to question "{question_label}" (index {question_number})'
        )
        cb.setEnabled(False)
        cb.setChecked(True)
        vlay.addWidget(cb)
        # For the future, once implemented:
        # label = QLabel("Specify a list of question indices to share this rubric.")
        # label.setWordWrap(True)
        # vlay.addWidget(label)
        vlay.addWidget(QLabel("<hr>"))
        lay = QHBoxLayout()
        cb = QCheckBox("specific to version(s)")
        cb.stateChanged.connect(self.toggle_version_specific)
        lay.addWidget(cb)
        self.version_specific_cb = cb
        le = QLineEdit()

        # Regular expression: to be kept in-sync with get_versions_list()
        #
        #   whitespace only or...
        #       ╭─┴─╮
        re = r"(^\s*$|^\s*(\d+\s*,\s*)*(\d+)\s*$)"
        #             │   ╰──┬───────╯│╰─┬─╯└ trailing whitespace
        #             │      │        │  └ final number
        #             │      │        └ can repeat
        #             │      └ number and comma
        #             └ leading whitespace
        #
        # "1, 2,3" acceptable; "1,2, " intermediate; ",2" unacceptable
        le.setValidator(QRegularExpressionValidator(QRegularExpression(re), self))
        lay.addWidget(le)
        self.version_specific_le = le
        space = QSpacerItem(
            48, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.version_specific_space = space
        lay.addItem(space)
        vlay.addLayout(lay)
        if maxver > 1:
            # TODO: coming soon notice and setEnabled(False) below
            s = "<p>By default, rubrics are shared between versions of a question.<br />"
            s += "You can also parameterize using version-specific substitutions."
            s += " &nbsp;(Experimental!)</p>"
        else:
            s = "<p>By default, rubrics are shared between versions of a question.</p>"
        vlay.addWidget(QLabel(s))
        self._param_grid = QGridLayout()  # placeholder
        vlay.addLayout(self._param_grid)
        vlay.addWidget(QLabel("<hr>"))
        hlay = QHBoxLayout()
        self.group_checkbox = QCheckBox("Associate with the group ")
        hlay.addWidget(self.group_checkbox)
        b = QComboBox()
        # b.setEditable(True)
        # b.setDuplicatesEnabled(False)
        b.addItems(groups)
        b.setMinimumContentsLength(5)
        # changing the group ticks the group checkbox
        b.activated.connect(lambda: self.group_checkbox.setChecked(True))
        hlay.addWidget(b)
        self.group_combobox = b
        b = QToolButton(text="➕")
        b.setToolTip("Add new group")
        b.setAutoRaise(True)
        b.clicked.connect(self.add_new_group)
        self.group_add_btn = b
        hlay.addWidget(b)
        # b = QToolButton(text="➖")
        # b.setToolTip("Delete currently-selected group")
        # b.setAutoRaise(True)
        # hlay.addWidget(b)
        hlay.addItem(
            QSpacerItem(
                48, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
            )
        )
        b = QToolButton(text="What are groups?")
        b.setAutoRaise(True)
        msg = """<p>Groups are intended for multi-part questions.
              For example, you could make groups &ldquo;(a)&rdquo;,
              &ldquo;(b)&rdquo; and &ldquo;(c)&rdquo;.
              Some tips:</p>
            <ul>
            <li><b>This is a new feature:</b> you may want to discuss
              with your team before using groups.</li>
            <li>Groups create automatic tabs, shared with other users.
              <b>Other users may need to click the &ldquo;sync&rdquo; button.</b>
            </li>
            <li>Making a rubric <em>exclusive</em> means it cannot be used alongside
              others from the same exclusion group.</li>
            <li>Groups will disappear automatically if there are no
              rubrics in them.</li>
            <ul>
        """
        b.clicked.connect(lambda: InfoMsg(self, msg).exec())
        hlay.addWidget(b)
        vlay.addLayout(hlay)
        hlay = QHBoxLayout()
        hlay.addItem(
            QSpacerItem(24, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        )
        # TODO: note default for absolute rubrics?  (once it is the default)
        c = QCheckBox("Exclusive in this group (at most one such rubric can be placed)")
        hlay.addWidget(c)
        self.group_excl = c
        self.group_checkbox.toggled.connect(lambda x: self.group_excl.setEnabled(x))
        self.group_checkbox.toggled.connect(lambda x: self.group_combobox.setEnabled(x))
        self.group_checkbox.toggled.connect(lambda x: self.group_add_btn.setEnabled(x))
        # TODO: connect self.typeRB_neutral etc change to check/uncheck the exclusive button
        self.group_excl.setChecked(False)
        self.group_excl.setEnabled(False)
        self.group_combobox.setEnabled(False)
        self.group_add_btn.setEnabled(False)
        self.group_checkbox.setChecked(False)
        vlay.addLayout(hlay)
        self.toggle_version_specific()
        self.toggle_scope_elements()

        # TODO: in the future?
        flay.addRow("Tags", self.TEtag)
        self.TEtag.setEnabled(False)
        flay.addRow("Meta", self.TEmeta)

        flay.addRow("Rubric ID", self.label_rubric_id)
        flay.addRow("Created by", self.Luser)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )

        vlay = QVBoxLayout()
        vlay.addLayout(flay)
        vlay.addWidget(buttons)
        self.setLayout(vlay)

        # set up widgets
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        if reapable:
            self.reapable_CB.addItem("")
            self.reapable_CB.addItems(reapable)
        else:
            for i in range(reapable_layout.count()):
                w = reapable_layout.itemAt(i).widget()
                if w:
                    w.setEnabled(False)
        # Set up TE and CB so that when CB changed, text is updated
        self.reapable_CB.currentTextChanged.connect(self.changedReapableCB)

        params = []
        # If supplied with current text/delta then set them
        if com:
            if com["text"]:
                self.TE.clear()
                self.TE.insertPlainText(com["text"])
            self.TEmeta.insertPlainText(com.get("meta", ""))
            if com["kind"]:
                if com["kind"] == "neutral":
                    self.typeRB_neutral.setChecked(True)
                elif com["kind"] == "relative":
                    self.relative_value_SB.setValue(int(com["value"]))
                    self.typeRB_relative.setChecked(True)
                elif com["kind"] == "absolute":
                    self.abs_value_SB.setValue(int(com["value"]))
                    self.abs_out_of_SB.setValue(int(com["out_of"]))
                    self.typeRB_absolute.setChecked(True)
                else:
                    raise RuntimeError(f"unexpected kind in {com}")
            if com["id"]:
                self.label_rubric_id.setText(str(com["id"]))
            self.Luser.setText(com.get("username", ""))
            if com.get("versions"):
                self.version_specific_cb.setChecked(True)
                self.version_specific_le.setText(
                    ", ".join(str(x) for x in com["versions"])
                )
            params = com.get("parameters", [])
            tags = com.get("tags", "").split()
            # TODO: Python >= 3.9: t.removeprefix("exclusive:")
            exclusive_tags = [
                t[len("exclusive:") :] for t in tags if t.startswith("exclusive:")
            ]
            group_tags = [t[len("group:") :] for t in tags if t.startswith("group:")]

            if len(group_tags) == 0:
                self.group_checkbox.setChecked(False)
            elif len(group_tags) == 1:
                self.group_checkbox.setChecked(True)
                (g,) = group_tags
                if g not in groups:
                    self.group_combobox.insertItem(-1, g)
                self.group_combobox.setCurrentText(g)
            else:
                self.group_checkbox.setCheckState(Qt.CheckState.PartiallyChecked)
                self.group_combobox.setEnabled(False)

            if len(exclusive_tags) == 0:
                self.group_excl.setChecked(False)
            elif len(exclusive_tags) == 1:
                self.group_excl.setChecked(True)
            else:
                self.group_excl.setCheckState(Qt.CheckState.PartiallyChecked)

            if not group_tags and not exclusive_tags:
                pass
            elif len(group_tags) == 1 and not exclusive_tags:
                (g,) = group_tags
                tags.remove(f"group:{g}")
            elif len(group_tags) == 1 and group_tags == exclusive_tags:
                (g,) = group_tags
                (excl,) = exclusive_tags
                tags.remove(f"exclusive:{excl}")
                tags.remove(f"group:{g}")
            else:
                # not UI representable: disable UI controls
                self.group_checkbox.setEnabled(False)
                self.group_combobox.setEnabled(False)
                self.group_excl.setEnabled(False)
                self.TEtag.setEnabled(True)
            # repack the tags
            self.TEtag.setText(" ".join(tags))

        else:
            self.TE.setPlaceholderText(
                "Your rubric must contain some text.\n\n"
                'Prepend with "tex:" to use latex.\n\n'
                "You can harvest existing text from the page.\n\n"
                'Change "Marks" below to associate a point-change.'
            )
            self.TEtag.setPlaceholderText(
                "Currently not user-editable, used for grouping."
            )
            self.TEmeta.setPlaceholderText(
                "Notes about this rubric such as hints on when to use it.\n\n"
                "Not shown to student!"
            )
            self.Luser.setText(username)
            if add_to_group:
                assert add_to_group in groups, f"{add_to_group} not in groups={groups}"
                self.group_checkbox.setChecked(True)
                self.group_combobox.setCurrentText(add_to_group)
                # show the user we did this by opening the scope panel
                self.scopeButton.animateClick()
        self.subsRemakeGridUI(params)
        self.hiliter.setSubs([x for x, _ in params])

    def subsMakeGridUI(self, params):
        maxver = self.maxver
        grid = QGridLayout()
        nr = 0
        if params:
            for v in range(maxver):
                grid.addWidget(QLabel(f"ver {v + 1}"), nr, v + 1)
            nr += 1

        def _func_factory(zelf, i):
            def f():
                zelf.subsRemoveRow(i)

            return f

        for i, (param, values) in enumerate(params):
            w = QLineEdit(param)
            # w.connect...  # TODO: redo syntax highlighting?
            grid.addWidget(w, nr, 0)
            for v in range(maxver):
                w = QLineEdit(values[v])
                w.setPlaceholderText(f"<value for ver{v + 1}>")
                grid.addWidget(w, nr, v + 1)
            b = QToolButton(text="➖")  # \N{Minus Sign}
            b.setToolTip("remove this parameter and values")
            b.setAutoRaise(True)
            f = _func_factory(self, i)
            b.pressed.connect(f)
            grid.addWidget(b, nr, maxver + 1)
            nr += 1

        if params:
            b = QToolButton(text="➕ add another")
        else:
            b = QToolButton(text="➕ add a parameterized substitution")
            # disabled for Issue #2462
            if not self.use_experimental_features:
                b.setEnabled(False)
        b.setAutoRaise(True)
        b.pressed.connect(self.subsAddRow)
        s = "Inserted at cursor point; highlighted text as initial value"
        if not self.use_experimental_features:
            s = "[disabled, experimental] " + s
        b.setToolTip(s)
        self.addParameterButton = b
        grid.addWidget(b, nr, 0)
        nr += 1
        return grid

    def subsAddRow(self):
        params = self.get_parameters()
        current_param_names = [p for p, _ in params]
        # find a new parameter name not yet used
        n = 1
        while True:
            new_param = "{param" + str(n) + "}"
            new_param_alt = f"<param{n}>"
            if (
                new_param not in current_param_names
                and new_param_alt not in current_param_names
            ):
                break
            n += 1
        if self.TE.toPlainText().casefold().startswith("tex:"):
            new_param = new_param_alt

        # we insert the new parameter at the cursor/selection
        tc = self.TE.textCursor()
        # save the selection as the new parameter value for this version
        values = ["" for _ in range(self.maxver)]
        if tc.hasSelection():
            values[self.version - 1] = tc.selectedText()
        params.append([new_param, values])
        self.hiliter.setSubs([x for x, _ in params])
        self.TE.textCursor().insertText(new_param)
        self.subsRemakeGridUI(params)

    def subsRemoveRow(self, i=0):
        params = self.get_parameters()
        params.pop(i)
        self.hiliter.setSubs([x for x, _ in params])
        self.subsRemakeGridUI(params)

    def subsRemakeGridUI(self, params):
        # discard the old grid and sub in a new one
        idx = self.scope_frame.layout().indexOf(self._param_grid)
        # print(f"discarding old grid at layout index {idx} to build new one")
        layout = self.scope_frame.layout().takeAt(idx)
        for i in reversed(range(layout.count())):
            layout.itemAt(i).widget().deleteLater()
        layout.deleteLater()
        grid = self.subsMakeGridUI(params)
        # self.scope_frame.layout().addLayout(grid)
        self.scope_frame.layout().insertLayout(idx, grid)
        self._param_grid = grid

    def get_parameters(self) -> List[Tuple[str, List[str]]]:
        """Extract the current parametric values from the UI."""
        idx = self.scope_frame.layout().indexOf(self._param_grid)
        # print(f"extracting parameters from grid at layout index {idx}")
        layout = self.scope_frame.layout().itemAt(idx)
        N = layout.rowCount()
        params = []
        for r in range(1, N - 1):
            param = layout.itemAtPosition(r, 0).widget().text()
            values = []
            for c in range(1, self.maxver + 1):
                values.append(layout.itemAtPosition(r, c).widget().text())
            params.append((param, values))
        return params

    def get_versions_list(self) -> List[int]:
        """Extract the version-specific list as a list of ints.

        If the input of the textbox is empty, or not acceptable
        just return an empty list (meaning no version restriction).

        Maintenance note: see also the RegExp validator of the
        LineEdit which must be kept in sync with this.  If they
        do not match, we risk getting ValueError from the int
        conversion here.
        """
        if not self.version_specific_cb.isChecked():
            return []
        if not self.version_specific_le.hasAcceptableInput():
            return []
        _vers = self.version_specific_le.text()
        _vers = _vers.strip("[]")
        _vers = _vers.strip()
        if _vers:
            return [int(x) for x in _vers.split(",")]
        return []

    def add_new_group(self):
        groups = []
        for n in range(self.group_combobox.count()):
            groups.append(self.group_combobox.itemText(n))
        suggested_name = next_in_longest_subsequence(groups)
        s, ok = QInputDialog.getText(
            self,
            "New group for rubric",
            "<p>New group for rubric.</p><p>(Currently no spaces allowed.)</p>",
            QLineEdit.EchoMode.Normal,
            suggested_name,
        )
        if not ok:
            return
        s = s.strip()
        if not s:
            return
        if " " in s:
            return
        n = self.group_combobox.count()
        self.group_combobox.insertItem(n, s)
        self.group_combobox.setCurrentIndex(n)

    def changedReapableCB(self):
        self.TE.clear()
        self.TE.insertPlainText(self.reapable_CB.currentText())

    def toggle_version_specific(self):
        if self.version_specific_cb.isChecked():
            self.version_specific_le.setText(str(self.version))
            self.version_specific_le.setPlaceholderText("")
            self.version_specific_le.setEnabled(True)
        else:
            self.version_specific_le.setText("")
            self.version_specific_le.setPlaceholderText(
                ", ".join(str(x + 1) for x in range(self.maxver))
            )
            self.version_specific_le.setEnabled(False)

    def toggle_scope_elements(self):
        if self.scopeButton.isChecked():
            self.scopeButton.setArrowType(Qt.ArrowType.DownArrow)
            # QFormLayout.setRowVisible but only in Qt 6.4!
            # instead we are using a QFrame
            self.scope_frame.setVisible(True)
        else:
            self.scopeButton.setArrowType(Qt.ArrowType.RightArrow)
            self.scope_frame.setVisible(False)

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.KeyboardModifier.ShiftModifier and (
            event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter
        ):
            # print("Dialog: Shift-Enter event")
            event.accept()
            self.accept()
            return
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier and (
            event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter
        ):
            # print("Dialog: Ctrl-Enter event")
            event.accept()
            txt = self.TE.toPlainText().strip()
            if not txt.casefold().startswith("tex:"):
                self.TE.setText("tex: " + self.TE.toPlainText())
            self.accept()
            return
        return super().keyPressEvent(event)

    def accept(self):
        """Make sure rubric is valid before accepting."""
        if not self.version_specific_le.hasAcceptableInput():
            WarnMsg(
                self, '"Versions" must be a comma-separated list of positive integers.'
            ).exec()
            return

        txt = self.TE.toPlainText().strip()
        if len(txt) <= 0 or txt.casefold() == "tex:":
            WarnMsg(
                self,
                "Your rubric must contain some text.",
                info="No whitespace only rubrics.",
                info_pre=False,
            ).exec()
            return
        if txt == ".":
            WarnMsg(
                self,
                f"Invalid text &ldquo;<tt>{txt}</tt>&rdquo; for rubric",
                info="""
                   <p>A single full-stop has meaning internally (as a sentinel),
                   so we cannot let you make one.  See
                   <a href="https://gitlab.com/plom/plom/-/issues/2421">Issue #2421</a>
                   for details.</p>
                """,
                info_pre=False,
            ).exec()
            return
        if not txt.casefold().startswith("tex:") and txt.count("$") >= 2:
            # Image by krzysiu, CC-PDDC, https://openclipart.org/detail/213508/crazy-paperclip
            res = resources.files(plom.client.icons) / "crazy_paperclip.svg"
            pix = QPixmap()
            pix.loadFromData(res.read_bytes())
            pix = pix.scaledToHeight(150, Qt.TransformationMode.SmoothTransformation)
            if (
                SimpleQuestion.ask(
                    self,
                    "<p>It looks like you might be writing some mathematics!</p",
                    """
                        <p>I noticed more than one dollar sign in your text:
                        do you want to render this rubric with LaTeX?</p>
                        <p>(You can avoid seeing this dialog by prepending your
                        rubric with &ldquo;<tt>tex:</tt>&rdquo;)</p>
                    """,
                    icon_pixmap=pix,
                )
                == QMessageBox.StandardButton.Yes
            ):
                self.TE.setText("tex: " + txt)
        super().accept()

    def _gimme_rubric_tags(self):
        tags = self.TEtag.text().strip()
        if not self.group_checkbox.isEnabled():
            # non-handled cases (such as multiple groups) disable these widgets
            return tags
        if self.group_checkbox.isChecked():
            group = self.group_combobox.currentText()
            if not group:
                return tags
            if " " in group:
                # quote spaces in future?
                group = '"' + group + '"'
                raise NotImplementedError("groups with spaces not implemented")
            if self.group_excl.isChecked():
                tag = f"group:{group} exclusive:{group}"
            else:
                tag = f"group:{group}"
            if tags:
                tags = tag + " " + tags
            else:
                tags = tag
        return tags

    def gimme_rubric_data(self) -> Dict[str, Any]:
        txt = self.TE.toPlainText().strip()  # we know this has non-zero length.
        tags = self._gimme_rubric_tags()

        meta = self.TEmeta.toPlainText().strip()
        if self.typeRB_neutral.isChecked():
            kind = "neutral"
            value = 0
            out_of = 0
            display_delta = "."
        elif self.typeRB_relative.isChecked():
            kind = "relative"
            value = self.relative_value_SB.value()
            out_of = 0
            display_delta = str(value) if value < 0 else f"+{value}"
        elif self.typeRB_absolute.isChecked():
            kind = "absolute"
            value = self.abs_value_SB.value()
            out_of = self.abs_out_of_SB.value()
            display_delta = f"{value} of {out_of}"
        else:
            raise RuntimeError("no radio was checked")
        username = self.Luser.text().strip()
        # only meaningful if we're modifying
        rubricID = self.label_rubric_id.text().strip()

        vers = self.get_versions_list()

        params = self.get_parameters()

        return {
            "id": rubricID,
            "kind": kind,
            "display_delta": display_delta,
            "value": value,
            "out_of": out_of,
            "text": txt,
            "tags": tags,
            "meta": meta,
            "username": username,
            "question": self.question_number,
            "versions": vers,
            "parameters": params,
        }
