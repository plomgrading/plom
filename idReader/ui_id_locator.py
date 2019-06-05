# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '../qtCreatorFiles/ui_id_locator.ui'
#
# Created by: PyQt5 UI code generator 5.12.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_idLocator(object):
    def setupUi(self, idLocator):
        idLocator.setObjectName("idLocator")
        idLocator.resize(648, 700)
        self.gridLayout = QtWidgets.QGridLayout(idLocator)
        self.gridLayout.setObjectName("gridLayout")
        self.cancelButton = QtWidgets.QPushButton(idLocator)
        self.cancelButton.setObjectName("cancelButton")
        self.gridLayout.addWidget(self.cancelButton, 2, 2, 1, 1)
        self.goButton = QtWidgets.QPushButton(idLocator)
        self.goButton.setObjectName("goButton")
        self.gridLayout.addWidget(self.goButton, 1, 2, 1, 1)
        self.imgFrame = QtWidgets.QFrame(idLocator)
        self.imgFrame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.imgFrame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.imgFrame.setObjectName("imgFrame")
        self.imgLayout = QtWidgets.QVBoxLayout(self.imgFrame)
        self.imgLayout.setObjectName("imgLayout")
        self.gridLayout.addWidget(self.imgFrame, 0, 0, 3, 2)
        self.frame = QtWidgets.QFrame(idLocator)
        self.frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame.setObjectName("frame")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.frame)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.topLayout = QtWidgets.QVBoxLayout()
        self.topLayout.setObjectName("topLayout")
        self.topSlider = QtWidgets.QSlider(self.frame)
        self.topSlider.setMinimum(0)
        self.topSlider.setMaximum(100)
        self.topSlider.setProperty("value", 10)
        self.topSlider.setSliderPosition(10)
        self.topSlider.setOrientation(QtCore.Qt.Vertical)
        self.topSlider.setInvertedAppearance(True)
        self.topSlider.setInvertedControls(True)
        self.topSlider.setTickPosition(QtWidgets.QSlider.TicksBothSides)
        self.topSlider.setTickInterval(10)
        self.topSlider.setObjectName("topSlider")
        self.topLayout.addWidget(self.topSlider)
        self.topLabel = QtWidgets.QLabel(self.frame)
        self.topLabel.setObjectName("topLabel")
        self.topLayout.addWidget(self.topLabel)
        self.horizontalLayout.addLayout(self.topLayout)
        self.bottomLayout = QtWidgets.QVBoxLayout()
        self.bottomLayout.setObjectName("bottomLayout")
        self.bottomSlider = QtWidgets.QSlider(self.frame)
        self.bottomSlider.setMaximum(100)
        self.bottomSlider.setProperty("value", 10)
        self.bottomSlider.setOrientation(QtCore.Qt.Vertical)
        self.bottomSlider.setTickPosition(QtWidgets.QSlider.TicksBothSides)
        self.bottomSlider.setTickInterval(10)
        self.bottomSlider.setObjectName("bottomSlider")
        self.bottomLayout.addWidget(self.bottomSlider)
        self.bottomLabel = QtWidgets.QLabel(self.frame)
        self.bottomLabel.setObjectName("bottomLabel")
        self.bottomLayout.addWidget(self.bottomLabel)
        self.horizontalLayout.addLayout(self.bottomLayout)
        self.gridLayout.addWidget(self.frame, 0, 2, 1, 1)

        self.retranslateUi(idLocator)
        QtCore.QMetaObject.connectSlotsByName(idLocator)

    def retranslateUi(self, idLocator):
        _translate = QtCore.QCoreApplication.translate
        idLocator.setWindowTitle(_translate("idLocator", "Form"))
        self.cancelButton.setText(_translate("idLocator", "Cancel"))
        self.goButton.setText(_translate("idLocator", "Go"))
        self.topLabel.setText(_translate("idLocator", "TextLabel"))
        self.bottomLabel.setText(_translate("idLocator", "TextLabel"))


