# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file './qtCreatorFiles/ui_identify.ui'
#
# Created by: PyQt5 UI code generator 5.15.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_IdentifyWindow(object):
    def setupUi(self, IdentifyWindow):
        IdentifyWindow.setObjectName("IdentifyWindow")
        IdentifyWindow.setWindowModality(QtCore.Qt.ApplicationModal)
        IdentifyWindow.resize(1000, 600)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(IdentifyWindow.sizePolicy().hasHeightForWidth())
        IdentifyWindow.setSizePolicy(sizePolicy)
        IdentifyWindow.setBaseSize(QtCore.QSize(0, 0))
        self.gridLayout_5 = QtWidgets.QGridLayout(IdentifyWindow)
        self.gridLayout_5.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.gridLayout_5.setObjectName("gridLayout_5")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.closeButton = QtWidgets.QPushButton(IdentifyWindow)
        self.closeButton.setObjectName("closeButton")
        self.horizontalLayout.addWidget(self.closeButton)
        self.gridLayout_5.addLayout(self.horizontalLayout, 4, 0, 1, 1)
        self.widget_2 = QtWidgets.QWidget(IdentifyWindow)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(5)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget_2.sizePolicy().hasHeightForWidth())
        self.widget_2.setSizePolicy(sizePolicy)
        self.widget_2.setObjectName("widget_2")
        self.gridLayout_4 = QtWidgets.QGridLayout(self.widget_2)
        self.gridLayout_4.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.paperBox = QtWidgets.QGroupBox(self.widget_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(4)
        sizePolicy.setHeightForWidth(self.paperBox.sizePolicy().hasHeightForWidth())
        self.paperBox.setSizePolicy(sizePolicy)
        self.paperBox.setObjectName("paperBox")
        self.gridLayout_7 = QtWidgets.QGridLayout(self.paperBox)
        self.gridLayout_7.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.gridLayout_7.setObjectName("gridLayout_7")
        self.gridLayout_4.addWidget(self.paperBox, 1, 0, 1, 1)
        self.predictionBox = QtWidgets.QGroupBox(self.widget_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.predictionBox.sizePolicy().hasHeightForWidth())
        self.predictionBox.setSizePolicy(sizePolicy)
        self.predictionBox.setObjectName("predictionBox")
        self.gridLayout_6 = QtWidgets.QGridLayout(self.predictionBox)
        self.gridLayout_6.setObjectName("gridLayout_6")
        self.pSIDLabel = QtWidgets.QLabel(self.predictionBox)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(4)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pSIDLabel.sizePolicy().hasHeightForWidth())
        self.pSIDLabel.setSizePolicy(sizePolicy)
        self.pSIDLabel.setObjectName("pSIDLabel")
        self.gridLayout_6.addWidget(self.pSIDLabel, 0, 0, 1, 1)
        self.pNameLabel = QtWidgets.QLabel(self.predictionBox)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(4)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pNameLabel.sizePolicy().hasHeightForWidth())
        self.pNameLabel.setSizePolicy(sizePolicy)
        self.pNameLabel.setObjectName("pNameLabel")
        self.gridLayout_6.addWidget(self.pNameLabel, 1, 0, 1, 1)
        self.predButton = QtWidgets.QPushButton(self.predictionBox)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.predButton.sizePolicy().hasHeightForWidth())
        self.predButton.setSizePolicy(sizePolicy)
        self.predButton.setObjectName("predButton")
        self.gridLayout_6.addWidget(self.predButton, 0, 1, 2, 1)
        self.gridLayout_4.addWidget(self.predictionBox, 0, 0, 1, 1)
        self.gridLayout_5.addWidget(self.widget_2, 0, 1, 5, 1)
        self.widget = QtWidgets.QWidget(IdentifyWindow)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(2)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget.sizePolicy().hasHeightForWidth())
        self.widget.setSizePolicy(sizePolicy)
        self.widget.setObjectName("widget")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.widget)
        self.gridLayout_3.setSizeConstraint(QtWidgets.QLayout.SetNoConstraint)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.nextButton = QtWidgets.QPushButton(self.widget)
        self.nextButton.setObjectName("nextButton")
        self.gridLayout_3.addWidget(self.nextButton, 3, 0, 1, 1)
        self.userBox = QtWidgets.QGroupBox(self.widget)
        self.userBox.setObjectName("userBox")
        self.gridLayout = QtWidgets.QGridLayout(self.userBox)
        self.gridLayout.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.gridLayout.setObjectName("gridLayout")
        self.userLabel = QtWidgets.QLabel(self.userBox)
        self.userLabel.setObjectName("userLabel")
        self.gridLayout.addWidget(self.userLabel, 0, 0, 1, 1)
        self.gridLayout_3.addWidget(self.userBox, 0, 0, 1, 1)
        self.tableBox = QtWidgets.QGroupBox(self.widget)
        self.tableBox.setObjectName("tableBox")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.tableBox)
        self.gridLayout_2.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.tableView = QtWidgets.QTableView(self.tableBox)
        self.tableView.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tableView.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tableView.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tableView.setObjectName("tableView")
        self.tableView.horizontalHeader().setStretchLastSection(True)
        self.gridLayout_2.addWidget(self.tableView, 0, 0, 1, 1)
        self.gridLayout_3.addWidget(self.tableBox, 5, 0, 1, 1)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.blankButton = QtWidgets.QPushButton(self.widget)
        self.blankButton.setObjectName("blankButton")
        self.horizontalLayout_2.addWidget(self.blankButton)
        self.viewButton = QtWidgets.QPushButton(self.widget)
        self.viewButton.setObjectName("viewButton")
        self.horizontalLayout_2.addWidget(self.viewButton)
        self.gridLayout_3.addLayout(self.horizontalLayout_2, 4, 0, 1, 1)
        self.studentBox = QtWidgets.QGroupBox(self.widget)
        self.studentBox.setObjectName("studentBox")
        self.formLayout = QtWidgets.QFormLayout(self.studentBox)
        self.formLayout.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.formLayout.setObjectName("formLayout")
        self.idEdit = QtWidgets.QLineEdit(self.studentBox)
        self.idEdit.setObjectName("idEdit")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.SpanningRole, self.idEdit)
        self.gridLayout_3.addWidget(self.studentBox, 2, 0, 1, 1)
        self.gridLayout_5.addWidget(self.widget, 0, 0, 1, 1)
        self.progressGroupBox = QtWidgets.QGroupBox(IdentifyWindow)
        self.progressGroupBox.setObjectName("progressGroupBox")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.progressGroupBox)
        self.verticalLayout.setObjectName("verticalLayout")
        self.idProgressBar = QtWidgets.QProgressBar(self.progressGroupBox)
        self.idProgressBar.setMaximum(1)
        self.idProgressBar.setProperty("value", 0)
        self.idProgressBar.setObjectName("idProgressBar")
        self.verticalLayout.addWidget(self.idProgressBar)
        self.gridLayout_5.addWidget(self.progressGroupBox, 1, 0, 1, 1)

        self.retranslateUi(IdentifyWindow)
        QtCore.QMetaObject.connectSlotsByName(IdentifyWindow)
        IdentifyWindow.setTabOrder(self.nextButton, self.tableView)
        IdentifyWindow.setTabOrder(self.tableView, self.closeButton)

    def retranslateUi(self, IdentifyWindow):
        _translate = QtCore.QCoreApplication.translate
        IdentifyWindow.setWindowTitle(_translate("IdentifyWindow", "Identify papers"))
        self.closeButton.setText(_translate("IdentifyWindow", "&Close"))
        self.paperBox.setTitle(_translate("IdentifyWindow", "Current paper"))
        self.predictionBox.setTitle(_translate("IdentifyWindow", "Machine prediction"))
        self.pSIDLabel.setText(_translate("IdentifyWindow", "Predicted Student ID"))
        self.pNameLabel.setText(_translate("IdentifyWindow", "Predicted Student Name"))
        self.predButton.setText(_translate("IdentifyWindow", "Accept\n"
" machine\n"
" prediction"))
        self.nextButton.setText(_translate("IdentifyWindow", "Skip (for now) and &get next"))
        self.userBox.setTitle(_translate("IdentifyWindow", "User"))
        self.userLabel.setText(_translate("IdentifyWindow", "Username"))
        self.tableBox.setTitle(_translate("IdentifyWindow", "Table of papers"))
        self.blankButton.setText(_translate("IdentifyWindow", "&Blank page"))
        self.viewButton.setText(_translate("IdentifyWindow", "&View whole"))
        self.studentBox.setTitle(_translate("IdentifyWindow", "Search classlist by student ID or name"))
        self.progressGroupBox.setTitle(_translate("IdentifyWindow", "Progress"))
        self.idProgressBar.setFormat(_translate("IdentifyWindow", "%v of %m"))
