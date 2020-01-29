# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '../qtCreatorFiles/ui_test_view.ui'
#
# Created by: PyQt5 UI code generator 5.12.3
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_TestView(object):
    def setupUi(self, TestView):
        TestView.setObjectName("TestView")
        TestView.resize(714, 603)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(TestView)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.frame_2 = QtWidgets.QFrame(TestView)
        self.frame_2.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame_2.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_2.setObjectName("frame_2")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.frame_2)
        self.verticalLayout.setObjectName("verticalLayout")
        self.groupViewTabWidget = QtWidgets.QTabWidget(self.frame_2)
        self.groupViewTabWidget.setObjectName("groupViewTabWidget")
        self.verticalLayout.addWidget(self.groupViewTabWidget)
        self.verticalLayout_2.addWidget(self.frame_2)
        self.frame = QtWidgets.QFrame(TestView)
        self.frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame.setObjectName("frame")
        self.gridLayout = QtWidgets.QGridLayout(self.frame)
        self.gridLayout.setObjectName("gridLayout")
        self.prevGroupButton = QtWidgets.QPushButton(self.frame)
        self.prevGroupButton.setObjectName("prevGroupButton")
        self.gridLayout.addWidget(self.prevGroupButton, 0, 0, 1, 1)
        self.nextGroupButton = QtWidgets.QPushButton(self.frame)
        self.nextGroupButton.setObjectName("nextGroupButton")
        self.gridLayout.addWidget(self.nextGroupButton, 0, 1, 1, 1)
        self.closeButton = QtWidgets.QPushButton(self.frame)
        self.closeButton.setObjectName("closeButton")
        self.gridLayout.addWidget(self.closeButton, 1, 3, 1, 1)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem, 1, 2, 1, 1)
        self.maxNormButton = QtWidgets.QPushButton(self.frame)
        self.maxNormButton.setObjectName("maxNormButton")
        self.gridLayout.addWidget(self.maxNormButton, 1, 1, 1, 1)
        self.verticalLayout_2.addWidget(self.frame)

        self.retranslateUi(TestView)
        self.groupViewTabWidget.setCurrentIndex(-1)
        QtCore.QMetaObject.connectSlotsByName(TestView)

    def retranslateUi(self, TestView):
        _translate = QtCore.QCoreApplication.translate
        TestView.setWindowTitle(_translate("TestView", "View test pages"))
        self.prevGroupButton.setText(_translate("TestView", "Previous Page"))
        self.nextGroupButton.setText(_translate("TestView", "Next Page"))
        self.closeButton.setText(_translate("TestView", "Close"))
        self.maxNormButton.setText(_translate("TestView", "Toggle Maximise"))
