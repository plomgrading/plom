__author__ = "Andrew Rechnitzer and Elvis Cai"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer and Elvis Cai"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai"]
__license__ = "AGPLv3"

import sys
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QMessageBox,
    QSpinBox,
    QTableWidgetItem,
    QWidget,
)
from PyQt5 import QtWidgets
from version_selector_qlist import Ui_MainWindow
from ui_builder import Ui_SpecBuilder

# the following allows us to import from ../resources
sys.path.append("..")
from resources.testspecification import TestSpecification


global spec
spec = TestSpecification()


class errorMessage(QMessageBox):
    def __init__(self, text):
        super(QMessageBox, self).__init__()
        self.setText(text)
        self.setStandardButtons(QMessageBox.Ok)
        self.setWindowTitle("Oops")


class SpecBuilder(QWidget):
    def __init__(self):
        super(SpecBuilder, self).__init__()
        self.ui = Ui_SpecBuilder()
        self.ui.setupUi(self)
        self.setupTable()

        self.ui.confirmButton.clicked.connect(self.basicSetup)
        self.ui.addRowButton.clicked.connect(self.addRow)
        self.ui.deleteRowButton.clicked.connect(self.deleteRow)
        self.ui.buildButton.clicked.connect(self.buildSpec)

    def setupTable(self):
        # set up the table
        self.ui.pgTable.setColumnCount(4)
        self.ui.pgTable.setRowCount(1)
        self.ui.pgTable.setHorizontalHeaderLabels(
            ["page from", "page to", "selection style", "marked out of"]
        )
        self.ui.pgTable.resizeColumnsToContents()
        self.ui.pgTable.itemChanged.connect(self.setTotal)

    def basicSetup(self):
        global numVersions
        numVersions = self.ui.versionSB.value()
        numPages = self.ui.pageSB.value()
        nameTest = self.ui.testNameLE.text()

        if numVersions == 0 or numPages == 0:
            self.errorManager(6)
        elif nameTest.isalnum() is False:
            self.errorManager(11)
        else:
            spec.setNumberOfPages(numPages)
            spec.setNumberOfVersions(numVersions)
            spec.Name = nameTest
            self.openUpVersionSelector(numVersions)
            self.ui.nameVersionGB.setEnabled(False)
            self.ui.pageGroupGB.setEnabled(True)
            self.ui.numberGB.setEnabled(True)
            self.addFirstRow()

    def openUpVersionSelector(self, numVersions):
        self.window = QtWidgets.QMainWindow()
        self.newui = Ui_MainWindow()
        self.newui.verNum = numVersions
        self.newui.setupUi(self.window)
        self.window.show()

    def addFirstRow(self):
        self.ui.pgTable.setVerticalHeaderItem(0, QTableWidgetItem("ID page(s)"))
        self.ui.pgTable.setItem(0, 0, QTableWidgetItem("1"))
        newSpin = QSpinBox(parent=self.ui.pgTable)
        newSpin.setRange(1, self.ui.pageSB.value())
        self.ui.pgTable.setCellWidget(0, 1, newSpin)
        self.ui.pgTable.setItem(0, 2, QTableWidgetItem("not applicable"))
        self.ui.pgTable.setItem(0, 3, QTableWidgetItem("0"))
        self.ui.pgTable.item(0, 0).setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.ui.pgTable.item(0, 2).setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.ui.pgTable.item(0, 3).setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

    def setTotal(self, itm):
        if itm.column() is not 3:
            return
        tot = 0
        for r in range(0, itm.row() + 1):
            v = self.ui.pgTable.item(r, 3).text()
            if v.isnumeric():
                tot += int(v)
        self.ui.totalLabel.setText("Total = {}".format(tot))

    def addRow(self):
        if self.validate():
            rows = self.increaseRowCount()
            self.disableChanges(rows)
            self.fillNewRow(rows)

    def deleteRow(self):
        rows = self.ui.pgTable.rowCount()
        if rows == 1:
            self.errorManager(7)
            return

        rows = rows - 1
        self.ui.pgTable.setRowCount(rows)
        # enable changes from previous row
        self.ui.pgTable.cellWidget(rows - 1, 1).setEnabled(True)
        self.ui.pgTable.item(rows - 1, 3).setFlags(
            Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled
        )

        if self.ui.pgTable.cellWidget(rows - 1, 2) is not None:
            self.ui.pgTable.cellWidget(rows - 1, 2).setEnabled(True)
        self.setTotal()

    def buildSpec(self):
        rows = self.ui.pgTable.rowCount()
        # check if versions and pages are all set up
        if self.ui.nameVersionGB.isEnabled():
            self.errorManager(1)
        elif not (
            self.ui.pgTable.item(rows - 1, 0).text().isnumeric()
            and self.ui.pgTable.item(rows - 1, 3).text().isnumeric()
        ):
            self.errorManager(3)
        elif (
            int(self.ui.pgTable.cellWidget(rows - 1, 1).value())
            < self.ui.pageSB.value()
        ):
            self.errorManager(8)
        elif (
            int(self.ui.pgTable.cellWidget(rows - 1, 1).value())
            > self.ui.pageSB.value()
        ):
            self.errorManager(5)
        else:
            self.setId()
            self.setPage()
            self.setTest()
            spec.writeSpec()
            spec.printSpec()
            self.errorManager(10)
            self.close()

    def validate(self):
        rows = self.ui.pgTable.rowCount()
        bO = False
        # check if versions and pages are all set up
        if self.ui.nameVersionGB.isEnabled():
            self.errorManager(1)
        # checking for errors:
        elif (
            self.ui.pgTable.item(rows - 1, 0) is None
            or self.ui.pgTable.cellWidget(rows - 1, 1) is None
            or self.ui.pgTable.item(rows - 1, 3) is None
        ):
            self.errorManager(2)
        # Type Check: first two has to be integers and the last,
        elif not (
            self.ui.pgTable.item(rows - 1, 0).text().isdigit()
            and self.ui.pgTable.item(rows - 1, 3).text().isdigit()
        ):
            self.errorManager(3)
        # "To" must be larger than "From"
        elif int(self.ui.pgTable.item(rows - 1, 0).text()) > int(
            self.ui.pgTable.cellWidget(rows - 1, 1).value()
        ):
            self.errorManager(4)
        # the last "page to" has to be smaller than the number of pages
        elif (
            int(self.ui.pgTable.cellWidget(rows - 1, 1).value())
            >= self.ui.pageSB.value()
        ):
            self.errorManager(5)
        else:
            bO = True
        return bO

    def increaseRowCount(self):
        rows = self.ui.pgTable.rowCount()
        self.ui.pgTable.setRowCount(rows + 1)
        self.ui.pgTable.setVerticalHeaderItem(
            rows, QTableWidgetItem("page group " + str(rows))
        )
        self.rotation = QComboBox()
        self.rotation.setObjectName("rotation")
        self.rotation.addItem("fixed")
        self.rotation.addItem("cycled")
        self.rotation.addItem("random")
        self.ui.pgTable.setCellWidget(rows, 2, self.rotation)
        return rows

    def disableChanges(self, rows):
        self.ui.pgTable.item(rows - 1, 0).setFlags(
            Qt.ItemIsSelectable | Qt.ItemIsEnabled
        )
        self.ui.pgTable.cellWidget(rows - 1, 1).setEnabled(False)
        self.ui.pgTable.item(rows - 1, 3).setFlags(
            Qt.ItemIsSelectable | Qt.ItemIsEnabled
        )
        if self.ui.pgTable.cellWidget(rows - 1, 2) is not None:
            self.ui.pgTable.cellWidget(rows - 1, 2).setEnabled(False)

    def fillNewRow(self, rows):
        previousTo = self.ui.pgTable.cellWidget(rows - 1, 1).value()
        thisFrom = previousTo + 1
        thisTo = thisFrom
        thisFrom = str(thisFrom)
        thisFrom = QTableWidgetItem(thisFrom)
        thisFrom.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.ui.pgTable.setItem(rows, 0, thisFrom)
        thisToWid = QSpinBox()
        thisToWid.setRange(thisTo, self.ui.pageSB.value())
        self.ui.pgTable.setCellWidget(rows, 1, thisToWid)
        self.ui.pgTable.setItem(rows, 3, QTableWidgetItem("."))

    def setId(self):
        i1 = int(self.ui.pgTable.item(0, 0).text())
        i2 = self.ui.pgTable.cellWidget(0, 1).value()
        spec.setIDPages(list(range(i1, i2 + 1)))

    def setPage(self):
        rows = self.ui.pgTable.rowCount()
        for x in range(1, rows):
            d0 = int(self.ui.pgTable.item(x, 0).text())
            d1 = self.ui.pgTable.cellWidget(x, 1).value()
            d3 = int(self.ui.pgTable.item(x, 3).text())
            d2_value = self.ui.pgTable.cellWidget(x, 2).currentText()
            if d2_value == "cycled":
                d2 = "c"
            elif d2_value == "random":
                d2 = "r"
            else:
                d2 = "f"
            spec.addToSpec(d2, list(range(d0, d1 + 1)), d3)

    def setTest(self):
        numTests = self.ui.numberOfTestSB.value()
        if numTests <= 0:
            self.errorManager(9)
        else:
            spec.setNumberOfTests(numTests)

    def errorManager(self, num):
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
            10: "Congrats! You have done setting up",
            11: "Name has to be alphanumeric and there is at least one character, and no space",
        }
        errormsg = switcher.get(num, "Invalid")
        error = errorMessage(errormsg)
        error.exec_()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    builder = SpecBuilder()
    builder.show()
    sys.exit(app.exec_())
