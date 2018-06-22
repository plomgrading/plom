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
        self.createButton = QtWidgets.QPushButton(Launcher)
        self.createButton.setObjectName("createButton")
        self.gridLayout.addWidget(self.createButton, 1, 0, 1, 1)
        self.setLocButton = QtWidgets.QPushButton(Launcher)
        self.setLocButton.setObjectName("setLocButton")
        self.gridLayout.addWidget(self.setLocButton, 0, 0, 1, 1)
        self.cancelButton = QtWidgets.QPushButton(Launcher)
        self.cancelButton.setObjectName("cancelButton")
        self.gridLayout.addWidget(self.cancelButton, 1, 2, 1, 1)
        self.directoryLE = QtWidgets.QLineEdit(Launcher)
        self.directoryLE.setObjectName("directoryLE")
        self.gridLayout.addWidget(self.directoryLE, 0, 1, 1, 2)

        self.retranslateUi(Launcher)
        QtCore.QMetaObject.connectSlotsByName(Launcher)

    def retranslateUi(self, Launcher):
        _translate = QtCore.QCoreApplication.translate
        Launcher.setWindowTitle(_translate("Launcher", "Start a new project"))
        self.createButton.setText(_translate("Launcher", "Create"))
        self.setLocButton.setText(_translate("Launcher", "Set location"))
        self.cancelButton.setText(_translate("Launcher", "Cancel"))

