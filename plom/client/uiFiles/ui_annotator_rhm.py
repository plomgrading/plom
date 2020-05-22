# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'qtCreatorFiles/ui_annotator_rhm.ui'
#
# Created by: PyQt5 UI code generator 5.13.2
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_annotator_rhm(object):
    def setupUi(self, annotator_rhm):
        annotator_rhm.setObjectName("annotator_rhm")
        annotator_rhm.setWindowModality(QtCore.Qt.WindowModal)
        annotator_rhm.resize(862, 670)

        self.horizontalLayout = QtWidgets.QHBoxLayout(annotator_rhm)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.hideableBox = QtWidgets.QFrame(annotator_rhm)
        self.hideableBox.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.hideableBox.setFrameShadow(QtWidgets.QFrame.Raised)
        self.hideableBox.setObjectName("hideableBox")

        self.verticalLayout = QtWidgets.QVBoxLayout(self.hideableBox)
        self.verticalLayout.setObjectName("verticalLayout")

        self.frame_1 = QtWidgets.QFrame(self.hideableBox)
        self.frame_1.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.frame_1.setFrameShadow(QtWidgets.QFrame.Plain)
        self.frame_1.setObjectName("frame_1")

        self.modeLayout = QtWidgets.QHBoxLayout(self.frame_1)
        self.modeLayout.setContentsMargins(0, 0, 0, 0)
        self.modeLayout.setObjectName("modeLayout")

        self.hamMenuButton = QtWidgets.QPushButton(self.frame_1)
        self.hamMenuButton.setMaximumSize(QtCore.QSize(42, 16777215))

        self.hamMenuButton.setObjectName("hamMenuButton")
        self.modeLayout.addWidget(self.hamMenuButton)

        self.keyHelpButton = QtWidgets.QPushButton(self.frame_1)
        self.keyHelpButton.setObjectName("keyHelpButton")

        self.modeLayout.addWidget(self.keyHelpButton)
        self.viewButton = QtWidgets.QPushButton(self.frame_1)
        self.viewButton.setObjectName("viewButton")
        self.modeLayout.addWidget(self.viewButton)
        self.finishedButton = QtWidgets.QPushButton(self.frame_1)
        self.finishedButton.setWhatsThis("")
        self.finishedButton.setObjectName("finishedButton")
        self.modeLayout.addWidget(self.finishedButton)
        self.finishNoRelaunchButton = QtWidgets.QPushButton(self.frame_1)
        self.finishNoRelaunchButton.setObjectName("finishNoRelaunchButton")
        self.modeLayout.addWidget(self.finishNoRelaunchButton)
        self.cancelButton = QtWidgets.QPushButton(self.frame_1)
        self.cancelButton.setObjectName("cancelButton")
        self.modeLayout.addWidget(self.cancelButton)
        self.verticalLayout.addWidget(self.frame_1)
        self.frame_2 = QtWidgets.QFrame(self.hideableBox)
        self.frame_2.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.frame_2.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_2.setObjectName("frame_2")
        self.buttonsLayout = QtWidgets.QHBoxLayout(self.frame_2)
        self.buttonsLayout.setContentsMargins(0, 0, 0, 0)
        self.buttonsLayout.setSpacing(3)
        self.buttonsLayout.setObjectName("buttonsLayout")
        self.markLabel = QtWidgets.QLabel(self.frame_2)
        self.markLabel.setObjectName("markLabel")
        self.buttonsLayout.addWidget(self.markLabel)
        self.zoomCB = QtWidgets.QComboBox(self.frame_2)
        self.zoomCB.setObjectName("zoomCB")
        self.buttonsLayout.addWidget(self.zoomCB)
        self.verticalLayout.addWidget(self.frame_2)
        self.frameTools = QtWidgets.QFrame(self.hideableBox)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.frameTools.sizePolicy().hasHeightForWidth())
        self.frameTools.setSizePolicy(sizePolicy)
        self.frameTools.setObjectName("frameTools")

        self.toolLayout = QtWidgets.QGridLayout(self.frameTools)
        self.toolLayout.setContentsMargins(0, 0, 0, 0)
        self.toolLayout.setSpacing(3)
        self.toolLayout.setObjectName("toolLayout")

        #configurate all buttons:

        self.penButton = QtWidgets.QToolButton(self.frameTools)
        self.textButton = QtWidgets.QToolButton(self.frameTools)
        self.panButton = QtWidgets.QToolButton(self.frameTools)
        self.lineButton = QtWidgets.QToolButton(self.frameTools)
        self.tickButton = QtWidgets.QToolButton(self.frameTools)
        self.moveButton = QtWidgets.QToolButton(self.frameTools)
        self.zoomButton = QtWidgets.QToolButton(self.frameTools)
        self.deleteButton = QtWidgets.QToolButton(self.frameTools)
        self.commentButton = QtWidgets.QToolButton(self.frameTools)
        self.crossButton = QtWidgets.QToolButton(self.frameTools)
        self.boxButton = QtWidgets.QToolButton(self.frameTools)

        buttons = [[self.penButton, "penButton", False],
                   [self.textButton, "textButton", False],
                   [self.panButton, "panButton", False],
                   [self.lineButton, "lineButton", False],
                   [self.tickButton, "tickButton", True],
                   [self.moveButton, "moveButton", False],
                   [self.zoomButton, "zoomButton", False],
                   [self.deleteButton, "deleteButton", False],
                   [self.commentButton, "commentButton", True],
                   [self.crossButton, "crossButton", False],
                   [self.boxButton, "boxButton", False]]

        def configButton(button, name, w, h, setTipNeg1):
            """
            Configures inputted button standard checkable, auto exclusive button.
            Modifies: button
            :param button: button to be configured
            :param name: string name of the button
            :param w: width (typically 45)
            :param h: height (typically 0)
            :param setTipNeg1: True if Tool Tip Duration should be set to -1, False otherwise.
            """
            button.setMinimumSize(QtCore.QSize(w, h))
            if setTipNeg1:
                button.setToolTipDuration(-1)
            button.setCheckable(True)
            button.setAutoExclusive(True)
            button.setObjectName(name)

        for button in buttons:
            configButton(button[0], button[1], 45, 0, button[2])

        self.toolLayout.addWidget(self.penButton, 0, 4, 1, 1)
        self.toolLayout.addWidget(self.textButton, 1, 4, 1, 1)

        self.commentDownButton = QtWidgets.QToolButton(self.frameTools)
        self.commentDownButton.setMinimumSize(QtCore.QSize(45, 0))
        self.commentDownButton.setToolTipDuration(-1)
        self.commentDownButton.setObjectName("commentDownButton")
        self.toolLayout.addWidget(self.commentDownButton, 2, 3, 1, 1)

        self.commentUpButton = QtWidgets.QToolButton(self.frameTools)
        self.commentUpButton.setMinimumSize(QtCore.QSize(45, 0))
        self.commentUpButton.setToolTipDuration(-1)
        self.commentUpButton.setObjectName("commentUpButton")
        self.toolLayout.addWidget(self.commentUpButton, 0, 3, 1, 1)

        self.toolLayout.addWidget(self.panButton, 0, 0, 1, 1)
        self.toolLayout.addWidget(self.lineButton, 2, 4, 1, 1)
        self.toolLayout.addWidget(self.tickButton, 1, 2, 1, 1)
        self.toolLayout.addWidget(self.moveButton, 2, 0, 1, 1)

        self.redoButton = QtWidgets.QToolButton(self.frameTools)
        self.redoButton.setMinimumSize(QtCore.QSize(45, 0))
        self.redoButton.setObjectName("redoButton")
        self.toolLayout.addWidget(self.redoButton, 0, 1, 1, 1)

        self.toolLayout.addWidget(self.zoomButton, 1, 0, 1, 1)
        self.toolLayout.addWidget(self.deleteButton, 2, 1, 1, 1)
        self.toolLayout.addWidget(self.commentButton, 1, 3, 1, 1)

        self.undoButton = QtWidgets.QToolButton(self.frameTools)
        self.undoButton.setMinimumSize(QtCore.QSize(45, 0))
        self.undoButton.setObjectName("undoButton")

        self.toolLayout.addWidget(self.undoButton, 1, 1, 1, 1)
        self.toolLayout.addWidget(self.crossButton, 0, 2, 1, 1)
        self.toolLayout.addWidget(self.boxButton, 2, 2, 1, 1)

        self.verticalLayout.addWidget(self.frameTools, 0, QtCore.Qt.AlignHCenter)
        self.frame_4 = QtWidgets.QFrame(self.hideableBox)
        self.frame_4.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.frame_4.setFrameShadow(QtWidgets.QFrame.Plain)
        self.frame_4.setObjectName("frame_4")
        self.ebLayout = QtWidgets.QHBoxLayout(self.frame_4)
        self.ebLayout.setContentsMargins(0, 0, 0, 0)
        self.ebLayout.setSpacing(3)
        self.ebLayout.setObjectName("ebLayout")
        self.modeLabel = QtWidgets.QLabel(self.frame_4)
        self.modeLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.modeLabel.setObjectName("modeLabel")
        self.ebLayout.addWidget(self.modeLabel)
        self.verticalLayout.addWidget(self.frame_4)
        self.markBox = QtWidgets.QFrame(self.hideableBox)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.markBox.sizePolicy().hasHeightForWidth())
        self.markBox.setSizePolicy(sizePolicy)
        self.markBox.setObjectName("markBox")
        self.markGrid = QtWidgets.QGridLayout(self.markBox)
        self.markGrid.setContentsMargins(0, 0, 0, 0)
        self.markGrid.setSpacing(3)
        self.markGrid.setObjectName("markGrid")
        self.verticalLayout.addWidget(self.markBox)
        self.frame_5 = QtWidgets.QFrame(self.hideableBox)
        self.frame_5.setObjectName("frame_5")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.frame_5)
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_2.setSpacing(6)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem)
        self.noAnswerButton = QtWidgets.QPushButton(self.frame_5)
        self.noAnswerButton.setObjectName("noAnswerButton")
        self.horizontalLayout_2.addWidget(self.noAnswerButton)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem1)
        self.verticalLayout.addWidget(self.frame_5)
        self.frame_3 = QtWidgets.QFrame(self.hideableBox)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(2)
        sizePolicy.setHeightForWidth(self.frame_3.sizePolicy().hasHeightForWidth())
        self.frame_3.setSizePolicy(sizePolicy)
        self.frame_3.setObjectName("frame_3")
        self.commentGrid = QtWidgets.QGridLayout(self.frame_3)
        self.commentGrid.setContentsMargins(0, 0, 0, 0)
        self.commentGrid.setSpacing(3)
        self.commentGrid.setObjectName("commentGrid")
        self.verticalLayout.addWidget(self.frame_3)
        self.horizontalLayout.addWidget(self.hideableBox)
        self.revealBox0 = QtWidgets.QFrame(annotator_rhm)
        self.revealBox0.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.revealBox0.setFrameShadow(QtWidgets.QFrame.Raised)
        self.revealBox0.setObjectName("revealBox0")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.revealBox0)
        self.verticalLayout_2.setSpacing(2)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.revealBox1 = QtWidgets.QFrame(self.revealBox0)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.revealBox1.sizePolicy().hasHeightForWidth())
        self.revealBox1.setSizePolicy(sizePolicy)
        self.revealBox1.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.revealBox1.setFrameShadow(QtWidgets.QFrame.Raised)
        self.revealBox1.setObjectName("revealBox1")
        self.revealLayout = QtWidgets.QGridLayout(self.revealBox1)
        self.revealLayout.setContentsMargins(0, 0, 0, 0)
        self.revealLayout.setSpacing(3)
        self.revealLayout.setObjectName("revealLayout")
        self.deltaButton = QtWidgets.QToolButton(self.revealBox1)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.deltaButton.sizePolicy().hasHeightForWidth())
        self.deltaButton.setSizePolicy(sizePolicy)
        self.deltaButton.setMinimumSize(QtCore.QSize(45, 0))
        self.deltaButton.setCheckable(True)
        self.deltaButton.setAutoExclusive(True)
        self.deltaButton.setObjectName("deltaButton")
        self.revealLayout.addWidget(self.deltaButton, 1, 0, 1, 1)
        self.verticalLayout_2.addWidget(self.revealBox1, 0, QtCore.Qt.AlignTop)
        self.revealBox2 = QtWidgets.QFrame(self.revealBox0)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.revealBox2.sizePolicy().hasHeightForWidth())
        self.revealBox2.setSizePolicy(sizePolicy)
        self.revealBox2.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.revealBox2.setFrameShadow(QtWidgets.QFrame.Raised)
        self.revealBox2.setObjectName("revealBox2")
        self.revealLayout2 = QtWidgets.QVBoxLayout(self.revealBox2)
        self.revealLayout2.setContentsMargins(3, 3, 3, 3)
        self.revealLayout2.setSpacing(3)
        self.revealLayout2.setObjectName("revealLayout2")
        self.verticalLayout_2.addWidget(self.revealBox2, 0, QtCore.Qt.AlignHCenter | QtCore.Qt.AlignBottom)
        self.horizontalLayout.addWidget(self.revealBox0)
        self.pageFrame = QtWidgets.QFrame(annotator_rhm)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(2)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pageFrame.sizePolicy().hasHeightForWidth())
        self.pageFrame.setSizePolicy(sizePolicy)
        self.pageFrame.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.pageFrame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.pageFrame.setObjectName("pageFrame")
        self.pageFrameGrid = QtWidgets.QGridLayout(self.pageFrame)
        self.pageFrameGrid.setContentsMargins(0, 0, 0, 0)
        self.pageFrameGrid.setObjectName("pageFrameGrid")
        self.horizontalLayout.addWidget(self.pageFrame)

        self.retranslateUi(annotator_rhm)
        QtCore.QMetaObject.connectSlotsByName(annotator_rhm)

    def retranslateUi(self, annotator_rhm):
        _translate = QtCore.QCoreApplication.translate
        annotator_rhm.setWindowTitle(_translate("annotator_rhm", "Annotate paper"))
        self.hamMenuButton.setText(_translate("annotator_rhm", "☰"))
        self.keyHelpButton.setToolTip(_translate("annotator_rhm", "List shortcut keys"))
        self.keyHelpButton.setText(_translate("annotator_rhm", "Key help"))
        self.viewButton.setToolTip(_translate("annotator_rhm", "Show entire paper in new window"))
        self.viewButton.setText(_translate("annotator_rhm", "View all"))
        self.finishedButton.setToolTip(_translate("annotator_rhm", "Save and move to the next paper"))
        self.finishedButton.setText(_translate("annotator_rhm", "Next"))
        self.finishNoRelaunchButton.setToolTip(_translate("annotator_rhm", "Save and return to marker window"))
        self.finishNoRelaunchButton.setText(_translate("annotator_rhm", "Done"))
        self.cancelButton.setToolTip(
            _translate("annotator_rhm", "Cancel the current annotations and return to marker window"))
        self.cancelButton.setText(_translate("annotator_rhm", "&Cancel"))
        self.markLabel.setText(_translate("annotator_rhm", "kk out of nn"))
        self.penButton.setToolTip(_translate("annotator_rhm", "press t"))
        self.penButton.setText(_translate("annotator_rhm", "..."))
        self.textButton.setToolTip(_translate("annotator_rhm", "press g"))
        self.textButton.setText(_translate("annotator_rhm", "..."))
        self.commentDownButton.setToolTip(_translate("annotator_rhm", "press v"))
        self.commentDownButton.setText(_translate("annotator_rhm", "..."))
        self.commentUpButton.setToolTip(_translate("annotator_rhm", "press r"))
        self.commentUpButton.setText(_translate("annotator_rhm", "..."))
        self.panButton.setToolTip(_translate("annotator_rhm", "press q"))
        self.panButton.setText(_translate("annotator_rhm", "..."))
        self.lineButton.setToolTip(_translate("annotator_rhm", "press b"))
        self.lineButton.setText(_translate("annotator_rhm", "..."))
        self.tickButton.setToolTip(_translate("annotator_rhm", "press d"))
        self.tickButton.setText(_translate("annotator_rhm", "..."))
        self.moveButton.setToolTip(_translate("annotator_rhm", "press z"))
        self.moveButton.setText(_translate("annotator_rhm", "..."))
        self.redoButton.setToolTip(_translate("annotator_rhm", "press w"))
        self.redoButton.setText(_translate("annotator_rhm", "..."))
        self.zoomButton.setToolTip(_translate("annotator_rhm", "press a"))
        self.zoomButton.setText(_translate("annotator_rhm", "..."))
        self.deleteButton.setToolTip(_translate("annotator_rhm", "press x"))
        self.deleteButton.setText(_translate("annotator_rhm", "..."))
        self.commentButton.setToolTip(_translate("annotator_rhm", "press f"))
        self.commentButton.setText(_translate("annotator_rhm", "..."))
        self.undoButton.setToolTip(_translate("annotator_rhm", "press s"))
        self.undoButton.setText(_translate("annotator_rhm", "..."))
        self.crossButton.setToolTip(_translate("annotator_rhm", "press e"))
        self.crossButton.setText(_translate("annotator_rhm", "..."))
        self.boxButton.setToolTip(_translate("annotator_rhm", "press c"))
        self.boxButton.setText(_translate("annotator_rhm", "..."))
        self.modeLabel.setText(_translate("annotator_rhm", "mode: comment"))
        self.noAnswerButton.setText(_translate("annotator_rhm", "No answer given"))
        self.deltaButton.setText(_translate("annotator_rhm", "..."))
