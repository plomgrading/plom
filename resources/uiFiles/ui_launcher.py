# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_launcher.ui'
#
# Created by: PyQt5 UI code generator 5.10.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Launcher(object):
    def setupUi(self, Launcher):
        Launcher.setObjectName("Launcher")
        Launcher.resize(400, 221)
        self.gridLayout = QtWidgets.QGridLayout(Launcher)
        self.gridLayout.setObjectName("gridLayout")
        self.directoryLE = QtWidgets.QLineEdit(Launcher)
        self.directoryLE.setObjectName("directoryLE")
        self.gridLayout.addWidget(self.directoryLE, 1, 1, 1, 2)
        self.cancelButton = QtWidgets.QPushButton(Launcher)
        self.cancelButton.setObjectName("cancelButton")
        self.gridLayout.addWidget(self.cancelButton, 2, 2, 1, 1)
        self.setLocButton = QtWidgets.QPushButton(Launcher)
        self.setLocButton.setObjectName("setLocButton")
        self.gridLayout.addWidget(self.setLocButton, 1, 0, 1, 1)
        self.createButton = QtWidgets.QPushButton(Launcher)
        self.createButton.setObjectName("createButton")
        self.gridLayout.addWidget(self.createButton, 2, 0, 1, 1)
        self.nameLabel = QtWidgets.QLabel(Launcher)
        self.nameLabel.setObjectName("nameLabel")
        self.gridLayout.addWidget(self.nameLabel, 0, 0, 1, 1)
        self.nameLE = QtWidgets.QLineEdit(Launcher)
        self.nameLE.setObjectName("nameLE")
        self.gridLayout.addWidget(self.nameLE, 0, 1, 1, 2)

        self.retranslateUi(Launcher)
        QtCore.QMetaObject.connectSlotsByName(Launcher)

    def retranslateUi(self, Launcher):
        _translate = QtCore.QCoreApplication.translate
        Launcher.setWindowTitle(_translate("Launcher", "Start a new project"))
        self.cancelButton.setText(_translate("Launcher", "Cancel"))
        self.setLocButton.setText(_translate("Launcher", "Set location"))
        self.createButton.setText(_translate("Launcher", "Create"))
        self.nameLabel.setText(_translate("Launcher", "Project name"))

