# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '../qtCreatorFiles/ui_builder.ui'
#
# Created by: PyQt5 UI code generator 5.10.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_SpecBuilder(object):
    def setupUi(self, SpecBuilder):
        SpecBuilder.setObjectName("SpecBuilder")
        SpecBuilder.resize(685, 749)
        self.verticalLayout = QtWidgets.QVBoxLayout(SpecBuilder)
        self.verticalLayout.setObjectName("verticalLayout")
        self.nameVersionGB = QtWidgets.QGroupBox(SpecBuilder)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred
        )
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.nameVersionGB.sizePolicy().hasHeightForWidth()
        )
        self.nameVersionGB.setSizePolicy(sizePolicy)
        self.nameVersionGB.setObjectName("nameVersionGB")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.nameVersionGB)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.testNameLabel = QtWidgets.QLabel(self.nameVersionGB)
        self.testNameLabel.setObjectName("testNameLabel")
        self.gridLayout_2.addWidget(self.testNameLabel, 0, 0, 1, 1)
        self.testNameLE = QtWidgets.QLineEdit(self.nameVersionGB)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.testNameLE.sizePolicy().hasHeightForWidth())
        self.testNameLE.setSizePolicy(sizePolicy)
        self.testNameLE.setObjectName("testNameLE")
        self.gridLayout_2.addWidget(self.testNameLE, 0, 1, 1, 3)
        self.versionLabel = QtWidgets.QLabel(self.nameVersionGB)
        self.versionLabel.setObjectName("versionLabel")
        self.gridLayout_2.addWidget(self.versionLabel, 1, 0, 1, 1)
        self.versionSB = QtWidgets.QSpinBox(self.nameVersionGB)
        self.versionSB.setObjectName("versionSB")
        self.gridLayout_2.addWidget(self.versionSB, 1, 1, 1, 1)
        self.pagesLabel = QtWidgets.QLabel(self.nameVersionGB)
        self.pagesLabel.setObjectName("pagesLabel")
        self.gridLayout_2.addWidget(self.pagesLabel, 2, 0, 1, 1)
        self.pageSB = QtWidgets.QSpinBox(self.nameVersionGB)
        self.pageSB.setObjectName("pageSB")
        self.gridLayout_2.addWidget(self.pageSB, 2, 1, 1, 1)
        spacerItem = QtWidgets.QSpacerItem(
            189, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        self.gridLayout_2.addItem(spacerItem, 2, 2, 1, 1)
        self.confirmButton = QtWidgets.QPushButton(self.nameVersionGB)
        self.confirmButton.setObjectName("confirmButton")
        self.gridLayout_2.addWidget(self.confirmButton, 2, 3, 1, 1)
        self.verticalLayout.addWidget(self.nameVersionGB)
        self.pageGroupGB = QtWidgets.QGroupBox(SpecBuilder)
        self.pageGroupGB.setEnabled(False)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.pageGroupGB.sizePolicy().hasHeightForWidth())
        self.pageGroupGB.setSizePolicy(sizePolicy)
        self.pageGroupGB.setObjectName("pageGroupGB")
        self.gridLayout = QtWidgets.QGridLayout(self.pageGroupGB)
        self.gridLayout.setObjectName("gridLayout")
        self.pgTable = QtWidgets.QTableWidget(self.pageGroupGB)
        self.pgTable.setObjectName("pgTable")
        self.pgTable.setColumnCount(0)
        self.pgTable.setRowCount(0)
        self.gridLayout.addWidget(self.pgTable, 0, 0, 8, 1)
        self.addRowButton = QtWidgets.QPushButton(self.pageGroupGB)
        self.addRowButton.setObjectName("addRowButton")
        self.gridLayout.addWidget(self.addRowButton, 0, 3, 1, 1)
        spacerItem1 = QtWidgets.QSpacerItem(
            20, 173, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
        )
        self.gridLayout.addItem(spacerItem1, 1, 3, 1, 1)
        spacerItem2 = QtWidgets.QSpacerItem(
            20, 172, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
        )
        self.gridLayout.addItem(spacerItem2, 3, 3, 1, 1)
        self.totalLabel = QtWidgets.QLabel(self.pageGroupGB)
        self.totalLabel.setObjectName("totalLabel")
        self.gridLayout.addWidget(self.totalLabel, 5, 3, 1, 1)
        self.deleteRowButton = QtWidgets.QPushButton(self.pageGroupGB)
        self.deleteRowButton.setObjectName("deleteRowButton")
        self.gridLayout.addWidget(self.deleteRowButton, 2, 3, 1, 1)
        self.verticalLayout.addWidget(self.pageGroupGB)
        self.numberGB = QtWidgets.QGroupBox(SpecBuilder)
        self.numberGB.setEnabled(False)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.numberGB.sizePolicy().hasHeightForWidth())
        self.numberGB.setSizePolicy(sizePolicy)
        self.numberGB.setObjectName("numberGB")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.numberGB)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.numberTestLabel = QtWidgets.QLabel(self.numberGB)
        self.numberTestLabel.setObjectName("numberTestLabel")
        self.horizontalLayout_2.addWidget(self.numberTestLabel)
        self.numberOfTestSB = QtWidgets.QSpinBox(self.numberGB)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.numberOfTestSB.sizePolicy().hasHeightForWidth()
        )
        self.numberOfTestSB.setSizePolicy(sizePolicy)
        self.numberOfTestSB.setMaximum(9999)
        self.numberOfTestSB.setObjectName("numberOfTestSB")
        self.horizontalLayout_2.addWidget(self.numberOfTestSB)
        spacerItem3 = QtWidgets.QSpacerItem(
            320, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        self.horizontalLayout_2.addItem(spacerItem3)
        self.buildButton = QtWidgets.QPushButton(self.numberGB)
        self.buildButton.setObjectName("buildButton")
        self.horizontalLayout_2.addWidget(self.buildButton)
        self.verticalLayout.addWidget(self.numberGB)

        self.retranslateUi(SpecBuilder)
        QtCore.QMetaObject.connectSlotsByName(SpecBuilder)

    def retranslateUi(self, SpecBuilder):
        _translate = QtCore.QCoreApplication.translate
        SpecBuilder.setWindowTitle(
            _translate("SpecBuilder", "Build a test specification")
        )
        self.nameVersionGB.setTitle(_translate("SpecBuilder", "Name and versions"))
        self.testNameLabel.setText(_translate("SpecBuilder", "Test Name"))
        self.versionLabel.setText(_translate("SpecBuilder", "# versions"))
        self.pagesLabel.setText(_translate("SpecBuilder", "# pages"))
        self.confirmButton.setText(_translate("SpecBuilder", "Confrm"))
        self.pageGroupGB.setTitle(_translate("SpecBuilder", "Page groups"))
        self.addRowButton.setText(_translate("SpecBuilder", "Add row"))
        self.totalLabel.setText(_translate("SpecBuilder", "Total mark = 0"))
        self.deleteRowButton.setText(_translate("SpecBuilder", "Delete row"))
        self.numberGB.setTitle(_translate("SpecBuilder", "Number of tests to build"))
        self.numberTestLabel.setText(_translate("SpecBuilder", "Number of tests"))
        self.buildButton.setText(_translate("SpecBuilder", "Build Specification"))
