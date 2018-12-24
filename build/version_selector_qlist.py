__author__ = "Andrew Rechnitzer and Elvis Cai"
__copyright__ = "Copyright (C) 2018 Andrew Rechnitzer and Elvis Cai"
__credits__ = ['Andrew Rechnitzer', 'Elvis Cai']
__license__ = "GPLv3"

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QWidget, QFileDialog
# from PyQt5.QtGui import QIcon
import sys
import os
import shutil


class errorMessage(QtWidgets.QMessageBox):
    def __init__(self, text):
        super(QtWidgets.QMessageBox, self).__init__()
        self.setText(text)
        self.setStandardButtons(QtWidgets.QMessageBox.Ok)
        self.setWindowTitle("Oops")


class Ui_MainWindow(object):
    global versions
    versions = {}

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(630, 430)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout()
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.label_2 = QtWidgets.QLabel(self.centralwidget)
        self.label_2.setObjectName("label_2")
        self.verticalLayout_3.addWidget(self.label_2)
        self.listWidget = QtWidgets.QListWidget(self.centralwidget)
        self.listWidget.setObjectName("listWidget")

        for i in range(0, self.verNum):
            item = QtWidgets.QListWidgetItem()
            self.listWidget.addItem(item)

        self.verticalLayout_3.addWidget(self.listWidget)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem = QtWidgets.QSpacerItem(40, 20,
                                           QtWidgets.QSizePolicy.Expanding,
                                           QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.pushButton = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton.setObjectName("pushButton")
        self.horizontalLayout.addWidget(self.pushButton)
        self.verticalLayout_3.addLayout(self.horizontalLayout)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.pushButton_2 = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_2.setObjectName("pushButton_2")
        self.horizontalLayout_3.addWidget(self.pushButton_2)
        self.verticalLayout_3.addLayout(self.horizontalLayout_3)
        self.verticalLayout.addLayout(self.verticalLayout_3)
        self.verticalLayout_2.addLayout(self.verticalLayout)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 630, 22))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.label_2.setText(_translate("MainWindow", "select versions:"))
        __sortingEnabled = self.listWidget.isSortingEnabled()
        self.listWidget.setSortingEnabled(False)

        for r in range(0, self.verNum):
            item = self.listWidget.item(r)
            item.setText(_translate("MainWindow", "version "+str(r+1)))

        self.listWidget.setCurrentItem(self.listWidget.item(0))

        self.listWidget.setSortingEnabled(__sortingEnabled)
        self.pushButton.setText(_translate("MainWindow", "select.."))
        self.pushButton_2.setText(_translate("MainWindow", "confirm versions"))

        self.pushButton.clicked.connect(self.openFileBrowser)
        self.pushButton_2.clicked.connect(lambda: self.confirm(MainWindow))

    def openFileBrowser(self):
        myBrowser = QFileDialog()
        myBrowser.setWindowTitle("File browser")
        myBrowser.setGeometry(10, 10, 640, 480)
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fname,_ = QFileDialog.getOpenFileName(
            myBrowser, "QFileDialog.getOpenFileName()",
            "", "Pdf Files (*.pdf)", options=options)
        if fname:
            oldText = self.listWidget.currentItem().text()[0:9]
            for x in versions.values():
                if fname == x:
                    self.errorManager(1)
                    return
            versions[oldText] = fname
            print(versions)
            newText = oldText + ": " + fname
            self.listWidget.currentItem().setText(newText)

            if(self.listWidget.currentRow() < self.verNum):
                newRow = self.listWidget.currentRow()+1
                self.listWidget.setCurrentRow(newRow)

    def errorManager(self, num):
        print("in error manager")
        switcher = {
            1: "Please do not use the same file twice",
            2: "Please match all files"
        }
        errormsg = switcher.get(num, "Invalid")
        error = errorMessage(errormsg)
        error.exec_()

    def confirm(self, MainWindow):
        if len(versions) != self.verNum:
            self.errorManager(2)
        else:
            for i in range(0, self.verNum):
                item = self.listWidget.item(i)
                thisItemText = item.text()
                this_old_name_loc = thisItemText.split(' ')[2]
                # now rename the file
                newFileName = "version" + str(i+1) + ".pdf"
                newPathName = os.path.join("sourceVersions", newFileName)
                try:
                    shutil.copy2(this_old_name_loc, newPathName)
                except shutil.SameFileError:
                    pass
            MainWindow.close()


class Chooser(QWidget):
    def __init__(self):
        super(Chooser, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = Chooser()
    window.show()
    sys.exit(app.exec_())
