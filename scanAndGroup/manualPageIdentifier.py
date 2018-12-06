import glob
import json
import os
import shutil
import sys
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPixmap
from PyQt5.QtWidgets import QApplication, QAbstractItemView, QDialog, \
    QErrorMessage, QGraphicsPixmapItem, QGraphicsScene, QGraphicsView, \
    QGridLayout, QLabel, QLineEdit, QPushButton, QSpinBox, QTableWidget, \
    QTableWidgetItem, QWidget
# this allows us to import from ../resources
sys.path.append('..')
from resources.testspecification import TestSpecification

# Read the test specification
spec = TestSpecification()

# make dicts for the exams produced and scanned
examsProduced = {}
examsScanned = {}


def readExamsProduced():
    """Read the exams that were produced during build"""
    global examsProduced
    with open('../resources/examsProduced.json') as data_file:
        examsProduced = json.load(data_file)


def readExamsScanned():
    """Read the list of test/page/versions that have been scanned"""
    global examsScanned
    if os.path.exists("../resources/examsScanned.json"):
        with open('../resources/examsScanned.json') as data_file:
            examsScanned = json.load(data_file)


def writeExamsScanned():
    """Update the list of test/page/versions that have been scanned"""
    es = open("../resources/examsScanned.json", 'w')
    es.write(json.dumps(examsScanned, indent=2, sort_keys=True))
    es.close()


class PageView(QGraphicsView):
    """We extend the standard graphicsview to include
    left-click zoom-in and right-click zoom out.
    """

    def __init__(self, fname):
        """Init with filename to display"""
        QGraphicsView.__init__(self)
        self.initUI(fname)

    def initUI(self, fname):
        """Init the interface. Load and display the filename."""
        # create a graphicsscene
        self.scene = QGraphicsScene()
        # create image from the filename and imageitem from that
        self.image = QPixmap(fname)
        self.imageItem = QGraphicsPixmapItem(self.image)
        # scale nicely
        self.imageItem.setTransformationMode(Qt.SmoothTransformation)
        # make sure scene includes all of image.
        self.scene.setSceneRect(0, 0, max(1000, self.image.width()),
                                max(1000, self.image.height()))
        # put image into scene
        self.scene.addItem(self.imageItem)
        # assign scene to the view
        self.setScene(self.scene)
        # fit all of the image into the current view
        self.fitInView(self.imageItem, Qt.KeepAspectRatio)

    def updateImage(self, fname):
        """Load image from filename and reset the view"""
        self.image = QPixmap(fname)
        self.imageItem.setPixmap(self.image)
        self.scene.setSceneRect(0, 0, self.image.width(), self.image.height())
        self.fitInView(self.imageItem, Qt.KeepAspectRatio)

    def mouseReleaseEvent(self, event):
        """On release of mouse zoom in or out by scaling the view"""
        if event.button() == Qt.RightButton:
            self.scale(0.8, 0.8)
        else:
            self.scale(1.25, 1.25)
        self.centerOn(event.pos())

    def resetView(self):
        """Reset the view to include all of the image"""
        self.fitInView(self.imageItem, Qt.KeepAspectRatio)

    def keyPressEvent(self, event):
        """If return or enter keys pressed then fire up
        the page identifier popup
        """
        key = event.key()
        if(key == Qt.Key_Return or key == Qt.Key_Enter):
            self.parent().parent().identifyIt()
        else:
            super(PageView, self).keyPressEvent(event)


class PageViewWindow(QWidget):
    """A simple window widget to display a pageimage
    User can left-click to zoom in, right-click to zoom out.
    """
    def __init__(self, fname=None):
        QWidget.__init__(self)
        self.initUI(fname)

    def initUI(self, fname):
        """Initialise the pageview window"""
        # init the specialised pageview that zooms.
        self.view = PageView(fname)
        self.view.setRenderHint(QPainter.HighQualityAntialiasing)
        # a reset-view button and link to the resetView command
        # in our specialised pageview.
        self.resetB = QPushButton('reset view')
        self.resetB.clicked.connect(lambda: self.view.resetView())
        # Layout the widgets - the image-view and the reset button
        grid = QGridLayout()
        grid.addWidget(self.view, 1, 1, 10, 4)
        grid.addWidget(self.resetB, 20, 1)
        self.setLayout(grid)
        self.show()

    def updateImage(self, fname):
        """Update the image with the given filename"""
        self.view.updateImage(fname)


class ImageTable(QTableWidget):
    """A simple table with the images we need to ID,
    their filenames, and the TPV codes once id'd
    Also records if they are 'extra' pages
    """
    def __init__(self):
        """Set a min width,
        selection mode is single row at a time,
        and user cannot directly edit entries,
        build a list of images we need to id
        and populate it.
        """
        super(ImageTable, self).__init__()
        self.setMinimumWidth(300)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.imageList = []
        self.reloadImageList()

    def keyPressEvent(self, event):
        """If return or enter keys pressed then fire up
        the page identifier popup (which belongs to the
        parent widget)
        """
        key = event.key()
        if key == Qt.Key_Return or key == Qt.Key_Enter:
            self.parent().identifyIt()
        else:
            super(ImageTable, self).keyPressEvent(event)

    def reloadImageList(self):
        """Reload the list of images from the problemimage directory"""
        self.imageList = []
        for fname in glob.glob("pageImages/problemImages/*.png"):
            self.imageList.append(fname)

    def populateTable(self):
        """Clear the table and populate with the filelist and
        make sure all cells suitably blank"""

        self.clear()
        self.setRowCount(len(self.imageList))
        self.setColumnCount(5)
        # Columns are filename, testnumber, pagenumber, version, and
        # a name field which will be 'valid' if the testname matches
        # the one in the spec, or 'extra' if it is an extra page
        self.setHorizontalHeaderLabels(['file', 't', 'p', 'v', 'name'])
        for r in range(len(self.imageList)):
            fItem = QTableWidgetItem(os.path.basename(self.imageList[r]))
            tItem = QTableWidgetItem(".")
            pItem = QTableWidgetItem(".")
            vItem = QTableWidgetItem(".")
            nItem = QTableWidgetItem("?")
            self.setItem(r, 0, fItem)
            self.setItem(r, 1, tItem)
            self.setItem(r, 2, pItem)
            self.setItem(r, 3, vItem)
            self.setItem(r, 4, nItem)
        # resize the columns and select the first row.
        self.resizeColumnsToContents()
        self.selectRow(0)

    def setTPV(self, t, p, v):
        """Given user input data of tpv, it fills the currently selected
        entry and fills in the data. It assigns name to 'valid'
        """
        r = self.currentRow()
        self.item(r, 1).setText(t)
        self.item(r, 2).setText(p)
        self.item(r, 3).setText(v)
        self.item(r, 4).setText("Valid")
        self.resizeColumnsToContents()

    def setTGExtra(self, t, g):
        """Given user input data of test and page-group, it fills
        the currently selected entry.
        The version number is grabbed from the exams-produced file
        and the name is set to 'extra'
        """
        r = self.currentRow()
        self.item(r, 1).setText(t)
        self.item(r, 2).setText(g)
        # Determine version from test number and group number
        # v = examsProduced[t][p]  but p=page, not group
        # set p to be the spec.PageGroups[g][0] (ie first page of that group)
        p = str(spec.PageGroups[int(g)][0])
        v = str(examsProduced[t][p])
        self.item(r, 3).setText(v)
        self.item(r, 4).setText("Extra")
        self.resizeColumnsToContents()

    def rotateCurrent(self):
        """If the current page is not in right orientation, then this uses
        imagemagick to rotate it
        """
        r = self.currentRow()
        if r is not None:
            # turn 90 in case in landscape.
            os.system("mogrify -rotate 90 -compress lossless "
                      "pageImages/problemImages/{}"
                      .format(self.item(r, 0).text()))
        return(r)

    def saveValid(self):
        """Go through the list of successfully id'd page images
        (which are marked as 'valid') and update the examsscanned
        dictionary, and copy the file into the correct place.
        """
        for r in range(self.rowCount()):
            if self.item(r, 4).text() == 'Valid':
                # grab the tpv data and the filename
                t = self.item(r, 1).text()
                p = self.item(r, 2).text()
                v = int(self.item(r, 3).text())
                fname = self.item(r, 0).text()
                # do this to get rid of extra 0's and turn back into strings
                tsi = str(int(t))
                psi = str(int(p))
                # if not seen this test before add it.
                if tsi not in examsScanned.keys():
                    examsScanned.update({tsi: {}})
                # if not seen this test/page before then
                # add it, the version and the filename
                if psi not in examsScanned[tsi].keys():
                    examsScanned[tsi].update({psi: [v, fname]})
                else:
                    # set the version and filename
                    examsScanned[tsi][psi] = [v, fname]
                print("Assigning file {} to t{}p{}v{}".format(fname, t, p, v))
                # copy the file into place and move the original
                # into alreadyProcessed
                shutil.copy("pageImages/problemImages/{}".format(fname),
                            "./decodedPages/page_{}/version_{}/t{}p{}v{}.png"
                            .format(str(p).zfill(2), str(v), str(t).zfill(4),
                                    str(p).zfill(2), str(v)))
                shutil.move("pageImages/problemImages/{}".format(fname),
                            "./pageImages/alreadyProcessed/")

    def saveExtras(self):
        """Go through the list of identified extra pages
        (which are marked as 'extra') and copy the file
         into the extras directory.
        """
        for r in range(self.rowCount()):
            if self.item(r, 4).text() == 'Extra':
                t = self.item(r, 1).text()
                g = self.item(r, 2).text()
                v = self.item(r, 3).text()
                # set this counter for multiple extra pages for some question
                n = 0
                fname = self.item(r, 0).text()
                # There may be more than 1 extra page for the same pagegroup
                ename = "extraPages/xt{}g{}v{}n{}.png".\
                    format(str(t).zfill(4), str(g).zfill(2), v, n)
                while os.path.exists(ename):
                    n = n+1  # file exists, add 1 to counter.
                    ename = "extraPages/xt{}g{}v{}n{}.png".\
                        format(str(t).zfill(4), str(g).zfill(2), v, n)
                # copy file into place, and move original to alreadyProcessed
                shutil.copy("pageImages/problemImages/{}".format(fname),
                            "./{}".format(ename))
                shutil.move("pageImages/problemImages/{}".format(fname),
                            "./pageImages/alreadyProcessed")


class PageIDDialog(QDialog):
    """Popup dialog for user to enter TPV code and
    to verify the testname is valid
    The tpv is compared against the one recorded
    during build.
    """
    def __init__(self):
        super(PageIDDialog, self).__init__()
        self.setWindowTitle("Manual check")
        grid = QGridLayout()
        # set name label + line edit
        # auto-populate with correct test-name.
        self.nameL = QLabel("Name:")
        self.nameLE = QLineEdit("{}".format(spec.Name))
        grid.addWidget(self.nameL, 1, 1)
        grid.addWidget(self.nameLE, 1, 2)
        # set test label + spinbox
        self.testL = QLabel("Test number")
        self.testSB = QSpinBox()
        self.testSB.setRange(0, spec.Tests)
        self.testSB.setValue(1)
        grid.addWidget(self.testL, 2, 1)
        grid.addWidget(self.testSB, 2, 2)
        # set page label + spinbox
        self.pageL = QLabel("Page number")
        self.pageSB = QSpinBox()
        self.pageSB.setRange(0, spec.Length)
        self.pageSB.setValue(1)
        grid.addWidget(self.pageL, 3, 1)
        grid.addWidget(self.pageSB, 3, 2)
        # set version label + spinbox
        self.versionL = QLabel("Version number")
        self.versionSB = QSpinBox()
        self.versionSB.setRange(0, spec.Versions)
        self.versionSB.setValue(1)
        grid.addWidget(self.versionL, 4, 1)
        grid.addWidget(self.versionSB, 4, 2)
        # add a validate button and connect to command
        self.validateB = QPushButton("Validate")
        grid.addWidget(self.validateB, 5, 1)
        self.validateB.clicked.connect(self.validate)
        # Fix the layout and unset modal.
        self.setLayout(grid)
        self.setModal(False)

    def checkIsValid(self):
        """Check that the entered values match the TPV
        recorded during build. Also check that the testname
        is what we think it should be.
        """
        # Grab the TPV
        t = str(self.testSB.value())
        p = str(self.pageSB.value())
        v = self.versionSB.value()
        # If this does not match the one on file pop-up an error.
        if examsProduced[t][p] != v:
            msg = QErrorMessage(self)
            msg.showMessage("TPV should be ({},{},{})"
                            .format(t, p, examsProduced[t][p]))
            msg.exec_()
            # reset the version spinbox to 0.
            self.versionSB.setValue(0)
            return False
        # If testname wrong then pop-up error.
        if self.nameLE.text() != spec.Name:
            msg = QErrorMessage(self)
            msg.showMessage("Name should be \"{}\"".format(spec.Name))
            msg.exec_()
            return False
        # If TPV is valid, but already scanned then pop-up an error
        if t in examsScanned:
            if p in examsScanned[t]:
                msg = QErrorMessage(self)
                msg.showMessage(
                    "TPV=({},{},{}) has already been scanned as file {}"
                    .format(t, p, examsScanned[t][p][0],
                            examsScanned[t][p][1]))
                msg.exec_()
                self.versionSB.setValue(0)
                return False
        # otherwise it is valid!
        return True

    def validate(self):
        """Check if the currently entered data is valid. If so accept."""
        if self.checkIsValid():
            self.accept()
        else:
            self.reject()


class PageExtraDialog(QDialog):
    """Popup dialog for user to enter test/group code
    for extra pages.
    """
    def __init__(self):
        super(PageExtraDialog, self).__init__()
        self.setWindowTitle("Extra page")
        grid = QGridLayout()
        # Test number and its spinbox
        self.testL = QLabel("Test number")
        self.testSB = QSpinBox()
        self.testSB.setRange(0, spec.Tests)
        self.testSB.setValue(1)
        grid.addWidget(self.testL, 1, 1)
        grid.addWidget(self.testSB, 1, 2)
        # pagegroup number and its spinbox
        self.groupL = QLabel("Pagegroup number")
        self.groupSB = QSpinBox()
        self.groupSB.setRange(1, spec.getNumberOfGroups())
        self.groupSB.setValue(1)
        grid.addWidget(self.groupL, 2, 1)
        grid.addWidget(self.groupSB, 2, 2)
        # accept button and connect to validate command.
        self.validateB = QPushButton("Accept")
        grid.addWidget(self.validateB, 3, 1)
        self.validateB.clicked.connect(self.validate)
        # fix the layout
        self.setLayout(grid)
        self.setModal(False)

    def validate(self):
        """Validate entry - at present alway valid"""
        if self.checkIsValid():
            self.accept()
        else:
            self.reject()

    def checkIsValid(self):
        """At present there is no validity checking.
        There should be something - eg checking that anything
        from this test has been scanned?
        """
        # t = str(self.testSB.value())
        # g = str(self.groupSB.value())
        return True


class PageIdentifier(QWidget):
    """Widget to put everything together - the table and the viewer and
    connect them with the pop-ups etc etc.
    """
    def __init__(self):
        super(PageIdentifier, self).__init__()
        self.initUI()

    def initUI(self):
        """Set up the interface, the table and the image-view"""
        grid = QGridLayout()
        # The list of pageimages to identify
        self.imageT = ImageTable()
        grid.addWidget(self.imageT, 1, 1, 4, 3)
        # connect it's selection-chnaged to the image-viewer
        # so a change to one triggers and update in the other.
        self.imageT.selectionModel().selectionChanged.connect(self.selChanged)
        # set up the page-view window
        self.pageImg = PageViewWindow()
        grid.addWidget(self.pageImg, 1, 4, 10, 10)
        # populate the table with the list of image-files
        self.imageT.populateTable()
        if self.imageT.imageList:
            self.pageImg.updateImage(self.imageT.imageList[0])
        # create a button to trigger a "This is an extra page"-popup.
        self.extraB = QPushButton("Extra page")
        # connect it to the extraPage command.
        self.extraB.clicked.connect(self.extraPage)
        grid.addWidget(self.extraB, 5, 1)
        # Add a "turn this image" button since pageimage might
        # not be in correct orientation
        self.rotateitB = QPushButton("Rotate image")
        self.rotateitB.clicked.connect(self.rotateCurrent)
        grid.addWidget(self.rotateitB, 6, 1)
        # Save all entered data and close
        self.closeB = QPushButton("Save && Close")
        self.closeB.clicked.connect(self.saveValid)
        grid.addWidget(self.closeB, 8, 1, 2, 2)
        # Close without saving anything.
        self.closeB = QPushButton("Close w/o save")
        self.closeB.clicked.connect(self.close)
        grid.addWidget(self.closeB, 100, 1)
        # Fix layout.
        self.setLayout(grid)
        self.setWindowTitle('Identify Page Images')
        self.show()

    def selChanged(self, selnew, selold):
        """When current selection changes in the table
        tell the image to update itself.
        """
        self.pageImg.updateImage(
            self.imageT.imageList[selnew.indexes()[0].row()])

    def saveValid(self):
        """Save the validated tpv and extras.
        Write the results to files and close."""
        self.imageT.saveValid()
        self.imageT.saveExtras()
        writeExamsScanned()
        self.close()

    def extraPage(self):
        """Fire up the extrapage pop-up"""
        pexd = PageExtraDialog()
        if pexd.exec_() == QDialog.Accepted:
            t = str(pexd.testSB.value())
            g = str(pexd.groupSB.value())
            self.imageT.setTGExtra(t, g)
            self.imageT.setFocus()

    def rotateCurrent(self):
        """Rotate the current image by 90 and trigger image update."""
        r = self.imageT.rotateCurrent()
        if r is not None:
            self.pageImg.updateImage(self.imageT.imageList[r])

    def identifyIt(self):
        """Fire up the identify tpv pop-up"""
        pidd = PageIDDialog()
        if pidd.exec_() == QDialog.Accepted:
            t = str(pidd.testSB.value()).zfill(4)
            p = str(pidd.pageSB.value()).zfill(2)
            v = str(pidd.versionSB.value())
            self.imageT.setTPV(t, p, v)
            self.imageT.setFocus()


def main():
    spec.readSpec()
    readExamsProduced()
    readExamsScanned()
    app = QApplication(sys.argv)
    PI = PageIdentifier()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
