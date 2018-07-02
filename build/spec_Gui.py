# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Third_GUI.ui'
#
# Created by: PyQt5 UI code generator 5.10.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets
import sys
from PyQt5.QtWidgets import *

sys.path.append('..') #this allows us to import from ../resources
from resources.testspecification import TestSpecification

global spec
spec = TestSpecification()

class errorMessage(QtWidgets.QMessageBox):
    def __init__(self, text):
        super(QtWidgets.QMessageBox, self).__init__()
        self.setText(text)
        self.setStandardButtons(QtWidgets.QMessageBox.Ok)
        self.setWindowTitle("Oops")

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(704, 454)
        self.gridLayout_2 = QtWidgets.QGridLayout(Dialog)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label_3 = QtWidgets.QLabel(Dialog)
        self.label_3.setObjectName("label_3")
        self.horizontalLayout.addWidget(self.label_3)
        self.spinBox_3 = QtWidgets.QSpinBox(Dialog)
        self.spinBox_3.setObjectName("spinBox_3")
        self.horizontalLayout.addWidget(self.spinBox_3)
        self.pushButton_2 = QtWidgets.QPushButton(Dialog)
        self.pushButton_2.setObjectName("pushButton_2")
        self.horizontalLayout.addWidget(self.pushButton_2)
        self.gridLayout_2.addLayout(self.horizontalLayout, 2, 0, 1, 2)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.table = QtWidgets.QTableWidget(Dialog)
        self.table.setObjectName("table")
        self.table.setColumnCount(0)
        self.table.setRowCount(0)
        self.verticalLayout_2.addWidget(self.table)
        self.gridLayout_2.addLayout(self.verticalLayout_2, 1, 0, 1, 1)
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.add_btn = QtWidgets.QPushButton(Dialog)
        self.add_btn.setObjectName("add_btn")
        self.verticalLayout.addWidget(self.add_btn)
        self.remove_btn = QtWidgets.QPushButton(Dialog)
        self.remove_btn.setObjectName("remove_btn")
        self.verticalLayout.addWidget(self.remove_btn)
        self.gridLayout_2.addLayout(self.verticalLayout, 1, 1, 1, 1)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.label = QtWidgets.QLabel(Dialog)
        self.label.setObjectName("label")
        self.horizontalLayout_3.addWidget(self.label)
        self.version = QtWidgets.QSpinBox(Dialog)
        self.version.setObjectName("version")
        self.horizontalLayout_3.addWidget(self.version)
        self.label_2 = QtWidgets.QLabel(Dialog)
        self.label_2.setObjectName("label_2")
        self.horizontalLayout_3.addWidget(self.label_2)
        self.page = QtWidgets.QSpinBox(Dialog)
        self.page.setObjectName("page")
        self.horizontalLayout_3.addWidget(self.page)

        self.nameTest = QtWidgets.QLabel(Dialog)
        self.nameTest.setObjectName("Test name")
        self.horizontalLayout_3.addWidget(self.nameTest)

        self.labelTestName = QtWidgets.QLabel(Dialog)
        self.testName = QtWidgets.QLineEdit(Dialog)
        self.horizontalLayout_3.addWidget(self.labelTestName)
        self.horizontalLayout_3.addWidget(self.testName)

        self.pushButton = QtWidgets.QPushButton(Dialog)
        self.pushButton.setObjectName("pushButton")
        self.horizontalLayout_3.addWidget(self.pushButton)
        self.gridLayout_2.addLayout(self.horizontalLayout_3, 0, 0, 1, 2)
        self.spinBox_3.setMaximum(10000)




        # set up the table
        self.table.setColumnCount(4)
        self.table.setRowCount(1)

        # set up horizontal headers
        colH1 = QtWidgets.QTableWidgetItem('page from')
        colH2 = QtWidgets.QTableWidgetItem('page to')
        colH3 = QtWidgets.QTableWidgetItem('rotation style')
        colH4 = QtWidgets.QTableWidgetItem('worth mark')
        self.table.setHorizontalHeaderItem(0, colH1)
        self.table.setHorizontalHeaderItem(1, colH2)
        self.table.setHorizontalHeaderItem(2, colH3)
        self.table.setHorizontalHeaderItem(3, colH4)

        # set up vertical headers
        self.table.setVerticalHeaderItem(0, QtWidgets.QTableWidgetItem('id page'))
        self.table.setItem(0,0, QtWidgets.QTableWidgetItem('1'))
        newSpin = QtWidgets.QSpinBox(Dialog)
        newSpin.setMinimum(1)
        self.table.setCellWidget(0,1, newSpin)

        # add info for id pages, and flag rotation style (or marks) as noneditable
        rotaForId = QtWidgets.QTableWidgetItem('not applicable')
        rotaForId.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        markForId = QtWidgets.QTableWidgetItem('0')
        markForId.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)

        self.table.setItem(0,2, rotaForId)
        self.table.setItem(0,3, markForId)

        # end for set up

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Dialog"))
        self.label_3.setText(_translate("Dialog", "numTests"))
        self.pushButton_2.setText(_translate("Dialog", "Run"))
        self.add_btn.setText(_translate("Dialog", "add row"))
        self.remove_btn.setText(_translate("Dialog", "remove row"))
        self.label.setText(_translate("Dialog", "numVersions"))
        self.label_2.setText(_translate("Dialog", "numPages"))
        self.pushButton.setText(_translate("Dialog", "confirm"))
        self.nameTest.setText(_translate("Dialog", "Test Name"))

        # functionalities
        self.add_btn.clicked.connect(self.addR)
        self.pushButton.clicked.connect(self.basicSetup)
        self.remove_btn.clicked.connect(self.removeRow)
        self.pushButton_2.clicked.connect(self.run)


    def validate(self):

        rows  = self.table.rowCount()
        bO = False
        # check if versions and pages are all set up
        if (self.pushButton.isEnabled()):
            self.errorManager(1)
        # checking for errors:
        elif (self.table.item(rows-1,0) == None or self.table.cellWidget(rows-1, 1) == None or self.table.item(rows-1,3) == None):
            self.errorManager(2)

        # Type Check: first two has to be integers and the last,
        elif not (self.table.item(rows-1,0).text().isdigit() and self.table.item(rows-1,3).text().isdigit()):
            self.errorManager(3)

        # "To" must be larger than "From"
        elif  (int(self.table.item(rows-1,0).text()) > int(self.table.cellWidget(rows-1,1).value())):
            self.errorManager(4)

        # the last "page to" has to be smaller than the number of pages
        elif (int(self.table.cellWidget(rows-1,1).value()) >= self.page.value()):
            self.errorManager(5)

        else:
            bO = True
            return bO



    def addR(self):
        boo = self.validate()
        print(boo)
        if(boo == True):
            rows = self.increaseRowCount()
            self.disableChanges(rows)
            self.fillNewRow(rows)


    def increaseRowCount(self):
        rows  = self.table.rowCount()
        self.table.setRowCount(rows+1)
        headerIndex = 'page group '+str(rows)
        self.table.setVerticalHeaderItem(rows, QtWidgets.QTableWidgetItem(headerIndex))
        self.rotation = QtWidgets.QComboBox(Dialog)
        self.rotation.setObjectName("rotation")
        self.rotation.addItem("random")
        self.rotation.addItem("cycled")
        self.rotation.addItem("fixed")
        self.table.setCellWidget(rows,2, self.rotation)
        return rows


    def disableChanges(self,rows):
        self.table.item(rows-1,0).setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        self.table.cellWidget(rows-1,1).setEnabled(False)
        self.table.item(rows-1,3).setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        if(self.table.cellWidget(rows-1,2) != None):
            self.table.cellWidget(rows-1,2).setEnabled(False)


    def fillNewRow(self,rows):
        previousTo = self.table.cellWidget(rows-1,1).value()
        thisFrom = previousTo+1
        thisTo = thisFrom
        thisFrom = str(thisFrom)
        thisFrom = QtWidgets.QTableWidgetItem(thisFrom)
        thisFrom.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        self.table.setItem(rows,0, thisFrom)
        thisToWid = QtWidgets.QSpinBox(Dialog)
        thisToWid.setMinimum(thisTo)
        self.table.setCellWidget(rows,1, thisToWid)



    def removeRow(self):
        rows = self.table.rowCount()
        if rows == 1:
            self.errorManager(7)
        else:

            rows = rows-1
            self.table.setRowCount(rows)
            #enable changes from previous row
            self.table.cellWidget(rows-1,1).setEnabled(True)
            self.table.item(rows-1,3).setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled)

            if(self.table.cellWidget(rows-1,2) != None):
                    self.table.cellWidget(rows-1,2).setEnabled(True)



    def basicSetup(self):
        numVersions = self.version.value()
        numPages = self.page.value()
        nameTest = self.testName.text()

        print(numPages)
        print("now in basicSetup")
        print(nameTest)

        if numVersions == 0 or numPages == 0:
            self.errorManager(6)
        elif nameTest.isalnum() == False:
            self.errorManager(11)
        else:
            spec.setNumberOfPages(numPages)
            spec.setNumberOfVersions(numVersions)
            spec.Name = "nameTest"

            # set everything disabled
            self.pushButton.setEnabled(False)
            self.version.setEnabled(False)
            self.page.setEnabled(False)
            self.testName.setEnabled(False)


    def run(self):

        rows  = self.table.rowCount()

        # check if versions and pages are all set up
        if (self.pushButton.isEnabled()):
            self.errorManager(1)
        elif not (self.table.item(rows-1,0).text().isdigit() and self.table.item(rows-1,3).text().isdigit()):
            self.errorManager(3)

        elif(int(self.table.cellWidget(rows-1,1).value()) < self.page.value()):
            self.errorManager(8)
        elif(int(self.table.cellWidget(rows-1,1).value()) > self.page.value()):
            self.errorManager(5)

        else:
            self.setId()
            self.setPage()
            self.setTest()
            spec.writeSpec()
            spec.printSpec()
            self.errorManager(10)
            sys.exit(app.exec_())



    def setId(self):
        i1 = int(self.table.item(0,0).text())
        i2 = self.table.cellWidget(0,1).value()
        spec.setIDPages(list(range(i1,i2+1)))

    def setPage(self):
        rows = self.table.rowCount()
        for x in range(1, rows):
            d0 = int(self.table.item(x,0).text())
            d1 = self.table.cellWidget(x,1).value()
            d3 = int(self.table.item(x,3).text())

            d2_value = self.table.cellWidget(x,2).currentText()

            if d2_value == "cycled":
                d2 = 'c'
            elif d2_value == "random":
                d2 = 'r'
            else:
                d2 = 'f'

            spec.addToSpec(d2, list(range(d0,d1+1)),d3)

    def setTest(self):
        numTests = self.spinBox_3.value()
        if numTests == 0:
            self.errorManager(9)
        else:
            spec.setNumberOfTests(numTests)



    def errorManager(self,num):
        print("here")
        switcher = {
        1: "Please fill up the number of pages and the number of versions and click confirm before continue",
        2: "Please fill up the current row before continue",
        3: "Marks have to be positive integers",
        4: "'page to' must be greater or equal to 'page from'",
        5: "you have exceeded the maximum number of pages you set",
        6: "Number of versions and number of pages cannot be zero",
        7: "Cannot remove ID pages",
        8: "Please make sure every page is assigned to a pageGroup",
        9: "Please print something",
        10:"Congrats! You have done setting up",
        11:"Name has to be alphanumeric and there is at least one character, and no space"
        }
        errormsg = switcher.get(num, "Invalid")
        error = errorMessage(errormsg)
        error.exec_()


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Dialog = QtWidgets.QDialog()
    ui = Ui_Dialog()
    ui.setupUi(Dialog)
    Dialog.show()
    sys.exit(app.exec_())
