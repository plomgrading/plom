# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'qtCreatorFiles/ui_chooser.ui'
#
# Created by: PyQt5 UI code generator 5.15.6
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Chooser(object):
    def setupUi(self, Chooser):
        Chooser.setObjectName("Chooser")
        Chooser.resize(540, 572)
        self.verticalLayout = QtWidgets.QVBoxLayout(Chooser)
        self.verticalLayout.setObjectName("verticalLayout")
        self.serverGBox = QtWidgets.QGroupBox(Chooser)
        self.serverGBox.setEnabled(True)
        self.serverGBox.setObjectName("serverGBox")
        self.gridLayout = QtWidgets.QGridLayout(self.serverGBox)
        self.gridLayout.setObjectName("gridLayout")
        self.infoLabel = QtWidgets.QLabel(self.serverGBox)
        self.infoLabel.setText("")
        self.infoLabel.setObjectName("infoLabel")
        self.gridLayout.addWidget(self.infoLabel, 3, 1, 1, 3)
        self.infoLabelStatic = QtWidgets.QLabel(self.serverGBox)
        self.infoLabelStatic.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.infoLabelStatic.setObjectName("infoLabelStatic")
        self.gridLayout.addWidget(self.infoLabelStatic, 3, 0, 1, 1)
        self.serverLabel = QtWidgets.QLabel(self.serverGBox)
        self.serverLabel.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.serverLabel.setObjectName("serverLabel")
        self.gridLayout.addWidget(self.serverLabel, 1, 0, 1, 1)
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_5.addItem(spacerItem)
        self.getServerInfoButton = QtWidgets.QPushButton(self.serverGBox)
        self.getServerInfoButton.setObjectName("getServerInfoButton")
        self.horizontalLayout_5.addWidget(self.getServerInfoButton)
        self.gridLayout.addLayout(self.horizontalLayout_5, 2, 2, 1, 2)
        self.mportLabel = QtWidgets.QLabel(self.serverGBox)
        self.mportLabel.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.mportLabel.setObjectName("mportLabel")
        self.gridLayout.addWidget(self.mportLabel, 2, 0, 1, 1)
        self.serverLE = QtWidgets.QLineEdit(self.serverGBox)
        self.serverLE.setObjectName("serverLE")
        self.gridLayout.addWidget(self.serverLE, 1, 1, 1, 3)
        self.mportSB = QtWidgets.QSpinBox(self.serverGBox)
        self.mportSB.setMaximum(65535)
        self.mportSB.setProperty("value", 41984)
        self.mportSB.setObjectName("mportSB")
        self.gridLayout.addWidget(self.mportSB, 2, 1, 1, 1)
        self.gridLayout.setColumnStretch(0, 1)
        self.gridLayout.setColumnStretch(1, 1)
        self.gridLayout.setColumnStretch(2, 1)
        self.gridLayout.setColumnStretch(3, 1)
        self.verticalLayout.addWidget(self.serverGBox)
        self.userGBox = QtWidgets.QGroupBox(Chooser)
        self.userGBox.setEnabled(True)
        self.userGBox.setObjectName("userGBox")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.userGBox)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.label = QtWidgets.QLabel(self.userGBox)
        self.label.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label.setObjectName("label")
        self.gridLayout_3.addWidget(self.label, 0, 0, 1, 1)
        self.userLE = QtWidgets.QLineEdit(self.userGBox)
        self.userLE.setObjectName("userLE")
        self.gridLayout_3.addWidget(self.userLE, 0, 1, 1, 1)
        self.label_2 = QtWidgets.QLabel(self.userGBox)
        self.label_2.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_2.setObjectName("label_2")
        self.gridLayout_3.addWidget(self.label_2, 1, 0, 1, 1)
        self.passwordLE = QtWidgets.QLineEdit(self.userGBox)
        self.passwordLE.setEchoMode(QtWidgets.QLineEdit.Password)
        self.passwordLE.setObjectName("passwordLE")
        self.gridLayout_3.addWidget(self.passwordLE, 1, 1, 1, 1)
        self.gridLayout_3.setColumnStretch(0, 1)
        self.gridLayout_3.setColumnStretch(1, 3)
        self.verticalLayout.addWidget(self.userGBox)
        self.markGBox = QtWidgets.QGroupBox(Chooser)
        self.markGBox.setEnabled(True)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.markGBox.sizePolicy().hasHeightForWidth())
        self.markGBox.setSizePolicy(sizePolicy)
        self.markGBox.setObjectName("markGBox")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.markGBox)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.identifyButton = QtWidgets.QPushButton(self.markGBox)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.identifyButton.sizePolicy().hasHeightForWidth())
        self.identifyButton.setSizePolicy(sizePolicy)
        self.identifyButton.setObjectName("identifyButton")
        self.gridLayout_2.addWidget(self.identifyButton, 3, 0, 1, 1)
        spacerItem1 = QtWidgets.QSpacerItem(32, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout_2.addItem(spacerItem1, 1, 6, 1, 1)
        self.pgLabel = QtWidgets.QLabel(self.markGBox)
        self.pgLabel.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.pgLabel.setObjectName("pgLabel")
        self.gridLayout_2.addWidget(self.pgLabel, 1, 2, 1, 1)
        spacerItem2 = QtWidgets.QSpacerItem(20, 4, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout_2.addItem(spacerItem2, 0, 0, 1, 1)
        self.vlabel = QtWidgets.QLabel(self.markGBox)
        self.vlabel.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.vlabel.setObjectName("vlabel")
        self.gridLayout_2.addWidget(self.vlabel, 1, 4, 1, 1)
        self.pgLayout = QtWidgets.QHBoxLayout()
        self.pgLayout.setObjectName("pgLayout")
        self.pgSB = QtWidgets.QSpinBox(self.markGBox)
        self.pgSB.setProperty("value", 1)
        self.pgSB.setObjectName("pgSB")
        self.pgLayout.addWidget(self.pgSB)
        self.pgDrop = QtWidgets.QComboBox(self.markGBox)
        self.pgDrop.setObjectName("pgDrop")
        self.pgLayout.addWidget(self.pgDrop)
        self.gridLayout_2.addLayout(self.pgLayout, 1, 3, 1, 1)
        self.vLayout = QtWidgets.QHBoxLayout()
        self.vLayout.setObjectName("vLayout")
        self.vSB = QtWidgets.QSpinBox(self.markGBox)
        self.vSB.setProperty("value", 1)
        self.vSB.setObjectName("vSB")
        self.vLayout.addWidget(self.vSB)
        self.vDrop = QtWidgets.QComboBox(self.markGBox)
        self.vDrop.setObjectName("vDrop")
        self.vLayout.addWidget(self.vDrop)
        self.gridLayout_2.addLayout(self.vLayout, 1, 5, 1, 1)
        spacerItem3 = QtWidgets.QSpacerItem(20, 5, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout_2.addItem(spacerItem3, 2, 0, 1, 1)
        spacerItem4 = QtWidgets.QSpacerItem(20, 4, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout_2.addItem(spacerItem4, 6, 0, 1, 1)
        self.markButton = QtWidgets.QPushButton(self.markGBox)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.markButton.sizePolicy().hasHeightForWidth())
        self.markButton.setSizePolicy(sizePolicy)
        self.markButton.setObjectName("markButton")
        self.gridLayout_2.addWidget(self.markButton, 1, 0, 1, 1)
        self.manageButton = QtWidgets.QPushButton(self.markGBox)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.manageButton.sizePolicy().hasHeightForWidth())
        self.manageButton.setSizePolicy(sizePolicy)
        self.manageButton.setObjectName("manageButton")
        self.gridLayout_2.addWidget(self.manageButton, 5, 0, 1, 1)
        spacerItem5 = QtWidgets.QSpacerItem(20, 5, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout_2.addItem(spacerItem5, 4, 0, 1, 1)
        spacerItem6 = QtWidgets.QSpacerItem(16, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout_2.addItem(spacerItem6, 1, 1, 1, 1)
        self.gridLayout_2.setColumnStretch(0, 3)
        self.gridLayout_2.setColumnStretch(3, 1)
        self.gridLayout_2.setColumnStretch(5, 1)
        self.gridLayout_2.setColumnStretch(6, 1)
        self.gridLayout_2.setRowStretch(0, 1)
        self.gridLayout_2.setRowStretch(1, 6)
        self.gridLayout_2.setRowStretch(2, 2)
        self.gridLayout_2.setRowStretch(3, 6)
        self.gridLayout_2.setRowStretch(4, 2)
        self.gridLayout_2.setRowStretch(5, 6)
        self.gridLayout_2.setRowStretch(6, 1)
        self.verticalLayout.addWidget(self.markGBox)
        self.settingsBox = QtWidgets.QGroupBox(Chooser)
        self.settingsBox.setObjectName("settingsBox")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.settingsBox)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.fontLabel = QtWidgets.QLabel(self.settingsBox)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.fontLabel.sizePolicy().hasHeightForWidth())
        self.fontLabel.setSizePolicy(sizePolicy)
        self.fontLabel.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.fontLabel.setObjectName("fontLabel")
        self.horizontalLayout_2.addWidget(self.fontLabel)
        self.fontSB = QtWidgets.QSpinBox(self.settingsBox)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.fontSB.sizePolicy().hasHeightForWidth())
        self.fontSB.setSizePolicy(sizePolicy)
        self.fontSB.setMinimum(4)
        self.fontSB.setMaximum(24)
        self.fontSB.setProperty("value", 10)
        self.fontSB.setObjectName("fontSB")
        self.horizontalLayout_2.addWidget(self.fontSB)
        spacerItem7 = QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem7)
        self.optionsButton = QtWidgets.QPushButton(self.settingsBox)
        self.optionsButton.setObjectName("optionsButton")
        self.horizontalLayout_2.addWidget(self.optionsButton)
        self.horizontalLayout_2.setStretch(0, 1)
        self.horizontalLayout_2.setStretch(1, 1)
        self.horizontalLayout_2.setStretch(2, 1)
        self.horizontalLayout_2.setStretch(3, 1)
        self.verticalLayout.addWidget(self.settingsBox)
        self.taskGBox = QtWidgets.QFrame(Chooser)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.taskGBox.sizePolicy().hasHeightForWidth())
        self.taskGBox.setSizePolicy(sizePolicy)
        self.taskGBox.setObjectName("taskGBox")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.taskGBox)
        self.horizontalLayout.setContentsMargins(0, 6, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.aboutButton = QtWidgets.QPushButton(self.taskGBox)
        self.aboutButton.setObjectName("aboutButton")
        self.horizontalLayout.addWidget(self.aboutButton)
        spacerItem8 = QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem8)
        self.closeButton = QtWidgets.QPushButton(self.taskGBox)
        self.closeButton.setObjectName("closeButton")
        self.horizontalLayout.addWidget(self.closeButton)
        self.verticalLayout.addWidget(self.taskGBox)

        self.retranslateUi(Chooser)
        QtCore.QMetaObject.connectSlotsByName(Chooser)
        Chooser.setTabOrder(self.serverLE, self.mportSB)
        Chooser.setTabOrder(self.mportSB, self.getServerInfoButton)
        Chooser.setTabOrder(self.getServerInfoButton, self.userLE)
        Chooser.setTabOrder(self.userLE, self.passwordLE)
        Chooser.setTabOrder(self.passwordLE, self.markButton)
        Chooser.setTabOrder(self.markButton, self.pgSB)
        Chooser.setTabOrder(self.pgSB, self.pgDrop)
        Chooser.setTabOrder(self.pgDrop, self.vSB)
        Chooser.setTabOrder(self.vSB, self.vDrop)
        Chooser.setTabOrder(self.vDrop, self.identifyButton)
        Chooser.setTabOrder(self.identifyButton, self.manageButton)
        Chooser.setTabOrder(self.manageButton, self.fontSB)
        Chooser.setTabOrder(self.fontSB, self.optionsButton)
        Chooser.setTabOrder(self.optionsButton, self.aboutButton)
        Chooser.setTabOrder(self.aboutButton, self.closeButton)

    def retranslateUi(self, Chooser):
        _translate = QtCore.QCoreApplication.translate
        Chooser.setWindowTitle(_translate("Chooser", "Plom Client"))
        self.serverGBox.setTitle(_translate("Chooser", "Server"))
        self.infoLabelStatic.setText(_translate("Chooser", "Info:"))
        self.serverLabel.setText(_translate("Chooser", "Server address:"))
        self.getServerInfoButton.setText(_translate("Chooser", "&Validate server"))
        self.mportLabel.setText(_translate("Chooser", "Port:"))
        self.serverLE.setText(_translate("Chooser", "127.0.0.1"))
        self.userGBox.setTitle(_translate("Chooser", "Credentials"))
        self.label.setText(_translate("Chooser", "Username:"))
        self.label_2.setText(_translate("Chooser", "Password:"))
        self.markGBox.setTitle(_translate("Chooser", "Choose a task"))
        self.identifyButton.setText(_translate("Chooser", "&Identify"))
        self.pgLabel.setText(_translate("Chooser", "Question:"))
        self.vlabel.setText(_translate("Chooser", "Version:"))
        self.markButton.setText(_translate("Chooser", "&Mark"))
        self.manageButton.setText(_translate("Chooser", "Manage &server"))
        self.settingsBox.setTitle(_translate("Chooser", "Settings"))
        self.fontLabel.setText(_translate("Chooser", "Font size:"))
        self.optionsButton.setText(_translate("Chooser", "&Options..."))
        self.aboutButton.setText(_translate("Chooser", "About"))
        self.closeButton.setText(_translate("Chooser", "&Close"))
