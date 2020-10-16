# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from PyQt5.QtCore import QEvent, QRectF
from PyQt5.QtGui import (
    QCursor,
    QGuiApplication,
    QPainter,
    QPixmap,
    QTransform,
)
from PyQt5.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, QUndoStack, QMessageBox

from plom import AnnFontSizePts, ScenePixelHeight

# Import all the tool commands for undo/redo stack.
from .tools import *

log = logging.getLogger("pagescene")


class ScoreBox(QGraphicsTextItem):
    """A simple graphics item which is place on the top-left
    corner of the group-image to indicate the current total mark.
    Drawn with a rounded-rectangle border.
    """

    def __init__(self, fontsize=10, maxScore=1, score=0):
        """
        Initialize a new ScoreBox.

        Args:
            fontsize (int): A non-zero, positive font value.
            maxScore (int) : A non-zero, positive maximum score.
            score (int): A non-zero, positive current score for the paper.
        """
        super(ScoreBox, self).__init__()
        self.score = score
        self.maxScore = maxScore
        self.setDefaultTextColor(Qt.red)
        self.font = QFont("Helvetica")
        self.fontSize = 1.25 * fontsize
        self.font.setPointSizeF(self.fontSize)
        self.setFont(self.font)
        # Not editable.
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        self.setPos(4, 4)
        self.changeScore(self.score)

    def changeScore(self, x):
        """
        Set the score to x.

        Args:
            x (int): A non-zero, positive new score.

        Returns:
            None
        """
        self.score = x
        self.setPlainText(
            "{} out of {}".format(str(x).zfill(2), str(self.maxScore).zfill(2))
        )

    def changeMax(self, x):
        """
        Set the max possible mark to x.

        Args:
            x (int): A non-zero, positive new maximum mark.

        Returns:
            None

        """
        # set the max-mark.
        self.maxScore = x
        self.setPlainText(
            "{} out of {}".format(str(x).zfill(2), str(self.maxScore).zfill(2))
        )

    def paint(self, painter, option, widget):
        """
        Paint a rounded rectangle border around the scorebox text.

        Args:
            painter (QPainter): Current painter object.
            option (QStyleOptionGraphicsItem): Style options.
            widget (QWidget): Associated widgets.

        Notes:
            Overrides parent method.

        Returns:
            None
        """
        painter.setPen(QPen(Qt.red, 2))
        painter.setBrush(QBrush(Qt.white))
        painter.drawRoundedRect(option.rect, 10, 10)
        super(ScoreBox, self).paint(painter, option, widget)


class UnderlyingImages(QGraphicsItemGroup):
    """
    A class for the image of the underlying pages being marked.
    """

    def __init__(self, imageNames):
        """
        Initialize a new series of underlying images.

        Args:
            imageNames(list[str]): List containing the names of the images.
        """
        super(QGraphicsItemGroup, self).__init__()
        self.imageNames = imageNames
        self.images = {}
        x = 0
        for (n, img) in enumerate(self.imageNames):
            pix = QPixmap(img)
            self.images[n] = QGraphicsPixmapItem(pix)
            self.images[n].setTransformationMode(Qt.SmoothTransformation)
            self.images[n].setPos(x, 0)
            sf = float(ScenePixelHeight) / float(pix.height())
            self.images[n].setScale(sf)
            # TODO: why not?
            # x += self.images[n].boundingRect().width()
            # help prevent hairline: subtract one pixel before converting
            x += sf * (pix.width() - 1.0)
            # TODO: don't floor here if units of scene are large!
            x = int(x)
            self.addToGroup(self.images[n])


# Dictionaries to translate tool-modes into functions
# for mouse press, move and release
mousePress = {
    "box": "mousePressBox",
    "comment": "mousePressComment",
    "cross": "mousePressCross",
    "delete": "mousePressDelete",
    "delta": "mousePressDelta",
    "line": "mousePressLine",
    "move": "mousePressMove",
    "pan": "mousePressPan",
    "pen": "mousePressPen",
    "text": "mousePressText",
    "tick": "mousePressTick",
    "zoom": "mousePressZoom",
    "image": "mousePressImage",
}
mouseMove = {
    "box": "mouseMoveBox",
    "delete": "mouseMoveDelete",
    "line": "mouseMoveLine",
    "pen": "mouseMovePen",
    "comment": "mouseMoveComment",
    "delta": "mouseMoveDelta",
    "zoom": "mouseMoveZoom",
}
mouseRelease = {
    "box": "mouseReleaseBox",
    "delete": "mouseReleaseDelete",
    "line": "mouseReleaseLine",
    "move": "mouseReleaseMove",
    "pen": "mouseReleasePen",
    "pan": "mouseReleasePan",
    "zoom": "mouseReleaseZoom",
}


class PageScene(QGraphicsScene):
    """Extend the graphics scene so that it knows how to translate
    mouse-press/move/release into operations on QGraphicsItems and
    QTextItems.
    """

    def __init__(self, parent, imgNames, saveName, maxMark, score, markStyle):
        """
        Initialize a new PageScene.

        Args:
            parent (SceneParent): the parent of the scene.
            imgNames (list[str]): list containing the names of the paper
                images.
            saveName (str): Name of the annotated image files.
            maxMark(int): maximum possible mark.
            score (int): current score
            markStyle (int): marking style.
                    1 = mark total = user clicks the total-mark (will be
                    deprecated in future.)
                    2 = mark-up = mark starts at 0 and user increments it
                    3 = mark-down = mark starts at max and user decrements it
        """
        super(PageScene, self).__init__(parent)
        self.parent = parent
        # Grab filename of groupimage
        self.imageNames = imgNames
        self.saveName = saveName
        self.maxMark = maxMark
        self.score = score
        self.markStyle = markStyle
        # Tool mode - initially set it to "move"
        self.mode = "move"
        # build pixmap and graphicsitemgroup.
        self.underImage = UnderlyingImages(self.imageNames)
        self.addItem(self.underImage)

        # Build scene rectangle to fit the image, and place image into it.
        self.setSceneRect(self.underImage.boundingRect())
        # initialise the undo-stack
        self.undoStack = QUndoStack()

        # we don't want current font size from UI; use fixed physical size
        # self.fontSize = self.font().pointSizeF()
        self.fontSize = AnnFontSizePts

        # Define standard pen, highlight, fill, light-fill
        self.ink = QPen(Qt.red, 2)
        self.highlight = QPen(QColor(255, 255, 0, 64), 50)
        self.brush = QBrush(self.ink.color())
        self.lightBrush = QBrush(QColor(255, 255, 0, 16))
        self.deleteBrush = QBrush(QColor(255, 0, 0, 16))
        self.zoomBrush = QBrush(QColor(0, 0, 255, 16))
        # Flags to indicate if drawing an arrow (vs line), highlight (vs
        # regular pen), box (vs ellipse), area-delete vs point.
        self.arrowFlag = 0
        self.penFlag = 0
        self.boxFlag = 0
        self.deleteFlag = 0
        self.zoomFlag = 0

        # Will need origin, current position, last position points.
        self.originPos = QPointF(0, 0)
        self.currentPos = QPointF(0, 0)
        self.lastPos = QPointF(0, 0)

        # Builds path for different tool items.
        self.path = QPainterPath()
        self.pathItem = QGraphicsPathItem()
        self.boxItem = QGraphicsRectItem()
        self.delBoxItem = QGraphicsRectItem()
        self.zoomBoxItem = QGraphicsRectItem()
        self.ellipseItem = QGraphicsEllipseItem()
        self.lineItem = QGraphicsLineItem()
        self.imageItem = QGraphicsPixmapItem
        self.blurb = TextItem(self, self.fontSize)
        self.deleteItem = None

        # Add a ghost comment to scene, but make it invisible
        self.ghostItem = GhostComment("1", "blah", self.fontSize)
        self.ghostItem.setVisible(False)
        self.addItem(self.ghostItem)

        # Set a mark-delta, comment-text and comment-delta.
        self.markDelta = "0"
        self.commentText = ""
        self.commentDelta = "0"

        # Build a scorebox and set it above all our other graphicsitems
        # so that it cannot be overwritten.
        # set up "k out of n" where k=current score, n = max score.
        self.scoreBox = ScoreBox(self.fontSize, self.maxMark, self.score)
        self.scoreBox.setZValue(10)
        self.addItem(self.scoreBox)

        # make a box around the scorebox where mouse-press-event won't work.
        self.avoidBox = self.scoreBox.boundingRect().adjusted(0, 0, 24, 24)
        # holds the path images uploaded from annotator
        self.tempImagePath = None

    # def patchImagesTogether(self, imageList):
    #     x = 0
    #     n = 0
    #     for img in imageList:
    #         self.images[n] = QGraphicsPixmapItem(QPixmap(img))
    #         self.images[n].setTransformationMode(Qt.SmoothTransformation)
    #         self.images[n].setPos(x, 0)
    #         self.addItem(self.images[n])
    #         x += self.images[n].boundingRect().width()
    #         self.underImage.addToGroup(self.images[n])
    #         n += 1
    #
    #     self.addItem(self.underImage)

    def how_many_underlying_images_wide(self):
        """How many images wide is the bottom layer?

        Currently this is just the number of images (because we layout
        in one long row) but future revisions might support alternate
        layouts.
        """
        return len(self.imageNames)

    def how_many_underlying_images_high(self):
        """How many images high is the bottom layer?

        Currently this is always 1 because we align the images in a
        single row but future revisions might support alternate layouts.
        """
        return 1

    def setToolMode(self, mode):
        """
        Sets the current toolMode.

        Args:
            mode (str): One of "comment", "delta", "pan", "move" etc..

        Returns:
            None
        """
        # set focus so that shift/control change cursor
        self.views()[0].setFocus(Qt.TabFocusReason)

        self.mode = mode
        # if current mode is not comment or delta, make sure the
        # ghostcomment is hidden
        if self.mode == "delta":
            # make sure the ghost is updated - fixes #307
            self.updateGhost(self.markDelta, "")
        elif self.mode == "comment":
            pass
        else:
            self.hideGhost()
        # if mode is "pan", allow the view to drag about, else turn it off
        if self.mode == "pan":
            self.views()[0].setDragMode(1)
        else:
            self.views()[0].setDragMode(0)

    def getComments(self):
        """
        Get the current text items and comments associated with this paper.

        Returns:
            (list): a list containing all comments.

        """
        comments = []
        for X in self.items():
            if isinstance(X, TextItem):
                comments.append(X.contents)
        return comments

    def countComments(self):
        """
        Counts current text items and comments associated with the paper.

        Returns:
            (int): total number of comments associated with this paper.
        """
        count = 0
        for X in self.items():
            if type(X) is TextItem:
                count += 1
        return count

    def areThereAnnotations(self):
        """
        Checks for pickleable annotations.

        Returns
            (bool): True if page scene has any pickle-able annotations,
                False otherwise.
        """
        for X in self.items():
            if hasattr(X, "saveable"):
                return True
        # no pickle-able items means no annotations.
        return False

    def save(self):
        """
        Save the annotated group-image.

        Notes:
        This overwrites the imagefile with a dump of the current
        scene and all its graphics items.
        """
        # Make sure the ghostComment is hidden
        self.ghostItem.hide()
        # Get the width and height of the image
        br = self.sceneRect()
        w = br.width()
        h = br.height()
        MINWIDTH = 1024  # subject to maxheight
        MAXWIDTH = 16000  # 16383 but for older imagemagick
        MAXHEIGHT = 8191
        MAX_PER_PAGE_WIDTH = 2000
        msg = []
        num_pages = self.how_many_underlying_images_wide()
        if w < MINWIDTH:
            r = (1.0 * w) / (1.0 * h)
            w = MINWIDTH
            h = w / r
            msg.append("Increasing png width because of minimum width constraint")
            if h > MAXHEIGHT:
                h = MAXHEIGHT
                w = h * r
                msg.append("Constraining png height by min width constraint")
        if w > num_pages * MAX_PER_PAGE_WIDTH:
            r = (1.0 * w) / (1.0 * h)
            w = num_pages * MAX_PER_PAGE_WIDTH
            h = w / r
            msg.append("Constraining png width by maximum per page width")
        if w > MAXWIDTH:
            r = (1.0 * w) / (1.0 * h)
            w = MAXWIDTH
            h = w / r
            msg.append("Constraining png width by overall maximum width")
        w = round(w)
        h = round(h)
        if msg:
            log.warning("{}: {}x{}".format(". ".join(msg), w, h))

        # Create an output pixmap and painter (to export it)
        oimg = QPixmap(w, h)
        exporter = QPainter(oimg)
        # Render the scene via the painter
        self.render(exporter)
        exporter.end()
        # Save the result to file.
        oimg.save(self.saveName)

    def keyPressEvent(self, event):
        """
        Changes the focus or cursor based on key presses.

        Notes:
            Overrides parent method.
            Escape key removes focus from the scene.
            Changes the cursor in accordance with each tool's mousePress
            documentation.

        Args:
            event (QKeyEvent): The Key press event.

        Returns:
            None

        """

        deltaShift = self.parent.cursorCross
        if self.mode == "delta":
            if not int(self.markDelta) > 0:
                deltaShift = self.parent.cursorTick

        variableCursors = {
            "cross": [self.parent.cursorTick, self.parent.cursorQMark],
            "line": [self.parent.cursorArrow, self.parent.cursorDoubleArrow],
            "delta": [deltaShift, self.parent.cursorQMark],
            "tick": [self.parent.cursorCross, self.parent.cursorQMark],
            "box": [self.parent.cursorEllipse, self.parent.cursorBox],
            "pen": [self.parent.cursorHighlight, self.parent.cursorDoubleArrow],
        }

        if self.mode in variableCursors:
            if event.key() == Qt.Key_Shift:
                self.views()[0].setCursor(variableCursors.get(self.mode)[0])
            elif event.key() == Qt.Key_Control:
                self.views()[0].setCursor(variableCursors.get(self.mode)[1])
            else:
                pass

        if event.key() == Qt.Key_Escape:
            self.clearFocus()
        else:
            super(PageScene, self).keyPressEvent(event)

    def keyReleaseEvent(self, event):
        """
        Changes cursors back to their standard cursor when keys are released.

        Args:
            event (QKeyEvent): the key release.

        Returns:
            None

        """
        variableCursorRelease = {
            "cross": self.parent.cursorCross,
            "line": self.parent.cursorLine,
            "delta": Qt.ArrowCursor,
            "tick": self.parent.cursorTick,
            "box": self.parent.cursorBox,
            "pen": self.parent.cursorPen,
        }
        if self.mode in variableCursorRelease:
            if self.views()[0].cursor() == variableCursorRelease.get(self.mode):
                pass
            else:
                self.views()[0].setCursor(variableCursorRelease.get(self.mode))
        else:
            pass

    def mousePressEvent(self, event):
        """
        Call various tool functions depending on the mouse press' location.

        Args:
            event (QMouseEvent): The mouse press event.

        Returns:
            None

        """
        # check if mouseclick inside the avoidBox
        if self.avoidBox.contains(event.scenePos()):
            return

        # Get the function name from the dictionary based on current mode.
        functionName = mousePress.get(self.mode, None)
        if functionName:
            # If you found a function, then call it.
            return getattr(self, functionName, None)(event)
        else:
            # otherwise call the usual qgraphicsscene function.
            return super(PageScene, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """
        Call various tool functions depending on the mouse's location.

        Args:
            event (QMouseEvent): The mouse move event.

        Returns:
            None

        """
        functionName = mouseMove.get(self.mode, None)
        if functionName:
            return getattr(self, functionName, None)(event)
        else:
            return super(PageScene, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        # Similar to mouse-press but for mouse-release.
        functionName = mouseRelease.get(self.mode, None)
        if functionName:
            return getattr(self, functionName, None)(event)
        else:
            return super(PageScene, self).mouseReleaseEvent(event)

    ###########
    # Tool functions for press, move and release.
    # Depending on the tool different functions are called
    # Many (eg tick) just create a graphics item, others (eg line)
    # create a temp object (on press) which is changes (as mouse-moves)
    # and then destroyed (on release) and replaced with the
    # more permanent graphics item.
    ###########

    def mousePressComment(self, event):
        """
        Handle when mouse is pressed on a given comment.

        Notes:
            Create a marked-comment-item from whatever is the currently
            selected comment. This creates a Delta-object and then also
            a text-object. They should be side-by-side with the delta
            appearing roughly at the mouse-click.

        Args:
            event (QMouseEvent): the given mouse click.

        Returns:
            None, adds clicked comment to the page.

        """
        # Find the object under the mouseclick.
        under = self.itemAt(event.scenePos(), QTransform())
        # If it is a Delta or Text or GDT then do nothing.
        if (
            isinstance(under, DeltaItem)
            or isinstance(under, TextItem)
            or isinstance(under, GroupDTItem)
        ):
            return

        pt = event.scenePos()  # grab the location of the mouse-click

        self.blurb = TextItem(self, self.fontSize)  # build the textitem
        self.blurb.setPlainText(self.commentText)
        self.blurb.contents = self.commentText  # for pickling
        # move to correct point - update if only text no delta

        self.blurb.setPos(pt)
        # If the mark-delta of comment is non-zero then create a
        # delta-object with a different offset, else just place the comment.

        if self.commentDelta == "." or not self.isLegalDelta(self.commentDelta):
            # make sure blurb has text interaction turned off
            prevState = self.blurb.textInteractionFlags()
            self.blurb.setTextInteractionFlags(Qt.NoTextInteraction)
            # Update position of text - the ghostitem has it right
            self.blurb.moveBy(0, self.ghostItem.blurb.pos().y())
            command = CommandText(self, self.blurb, self.ink)
            self.undoStack.push(command)
            # return blurb to previous state
            self.blurb.setTextInteractionFlags(prevState)
        else:
            command = CommandGDT(self, pt, self.commentDelta, self.blurb, self.fontSize)
            self.undoStack.push(command)  # push the delta onto the undo stack.

    def mousePressCross(self, event):
        """
        Selects the proper cross/?-mark/tick based on which mouse button or
        mouse/key combination was pressed.

        Notes:
            tick = right-click or shift+click.
            question mark = middle-click or control+click.
            cross = left-click or any combination other than the above.

        Args:
            event (QMouseEvent): the mouse press.

        Returns:
            None.

        """
        pt = event.scenePos()  # Grab the click's location and create command.
        if (event.button() == Qt.RightButton) or (
            QGuiApplication.queryKeyboardModifiers() == Qt.ShiftModifier
        ):
            command = CommandTick(self, pt)
        elif (event.button() == Qt.MiddleButton) or (
            QGuiApplication.queryKeyboardModifiers() == Qt.ControlModifier
        ):
            command = CommandQMark(self, pt)
        else:
            command = CommandCross(self, pt)
        self.undoStack.push(command)  # push onto the stack.

    def mousePressDelta(self, event):
        """
        Creates the mark-delta, ?-mark/tick/cross based on which mouse
        button or mouse/key combination was pressed.

        Notes:
            cross = right-click or shift+click if current mark-delta > 0.
            tick = right-click or shift+click if current mark-delta <= 0.
            question mark = middle-click or control+click.
            mark-delta = left-click or any other combination, assigns with
                the selected mark-delta value.


        Args:
            event (QMouseEvent): Mouse press.

        Returns:
            None

        """
        pt = event.scenePos()  # Grab click's location and create command.
        if (event.button() == Qt.RightButton) or (
            QGuiApplication.queryKeyboardModifiers() == Qt.ShiftModifier
        ):
            if int(self.markDelta) > 0:
                command = CommandCross(self, pt)
            else:
                command = CommandTick(self, pt)
        elif (event.button() == Qt.MiddleButton) or (
            QGuiApplication.queryKeyboardModifiers() == Qt.ControlModifier
        ):
            command = CommandQMark(self, pt)
        else:
            if self.isLegalDelta(self.markDelta):
                command = CommandDelta(self, pt, self.markDelta, self.fontSize)
            else:
                return
        self.undoStack.push(command)  # push command onto undoStack.

    def mousePressMove(self, event):
        """
        Create closed hand cursor when move-tool is selected, otherwise does
            nothing.
        Notes:
            The actual moving of objects is handled by themselves since they
            know how to handle the ItemPositionChange signal as a move-command.

        Args:
            event (QMouseEvent): the mouse press.

        Returns:
            None

        """
        self.views()[0].setCursor(Qt.ClosedHandCursor)
        super(PageScene, self).mousePressEvent(event)

    def mousePressPan(self, event):
        """
        While pan-tool selected changes the cursor to a closed hand,
        otherwise does not do much.

        Notes:
            Do not pass on event to superclass since we want to avoid
            selecting an object and moving that (fixes #834)

        Args:
            event (QMouseEvent): the mouse press.

        Returns:
            None

        """
        self.views()[0].setCursor(Qt.ClosedHandCursor)
        return

    def mousePressText(self, event):
        """
        Create a textObject at the click's location, unless there is already a
            textobject there.

        Args:
            event (QMouseEvent): the given mouse click.

        Returns:
            None

        """
        # Find the object under the click.
        under = self.itemAt(event.scenePos(), QTransform())
        # If something is there... (fixes bug reported by MattC)
        if under is not None:
            # If it is part of groupDTitem then do nothing
            if isinstance(under.group(), GroupDTItem):
                return
            # If it is a textitem then fire up the editor.
            if isinstance(under, TextItem):
                under.setTextInteractionFlags(Qt.TextEditorInteraction)
                self.setFocusItem(under, Qt.MouseFocusReason)
                super(PageScene, self).mousePressEvent(event)
                return
            # check if a textitem currently has focus and clear it.
            under = self.focusItem()
            if isinstance(under, TextItem):
                under.clearFocus()

        # Now we construct a text object, give it focus (which fires up the
        # editor on that object), and then push it onto the undo-stack.
        self.originPos = event.scenePos()
        self.blurb = TextItem(self, self.fontSize)
        # move so centred under cursor
        self.originPos -= QPointF(0, self.blurb.boundingRect().height() / 2)
        self.blurb.setPos(self.originPos)
        self.blurb.setFocus()
        command = CommandText(self, self.blurb, self.ink)
        self.undoStack.push(command)

    def mousePressTick(self, event):
        """
        Create a tick/?-mark/cross object under the click based on which
            mouse button (left/middle/right) was pressed.

        Args:
            event (QMouseEvent): Given mouse press.

        Returns:
            None

        """
        # See mouse press cross function.
        pt = event.scenePos()
        if (event.button() == Qt.RightButton) or (
            QGuiApplication.queryKeyboardModifiers() == Qt.ShiftModifier
        ):
            command = CommandCross(self, pt)
        elif (event.button() == Qt.MiddleButton) or (
            QGuiApplication.queryKeyboardModifiers() == Qt.ControlModifier
        ):
            command = CommandQMark(self, pt)
        else:
            command = CommandTick(self, pt)
        self.undoStack.push(command)

    def mouseReleaseMove(self, event):
        """
        Handles mouse releases for move tool by setting cursor to an open hand.

        Args:
            event (QMouseEvent): given mouse release.

        Returns:
            None.

        """
        self.views()[0].setCursor(Qt.OpenHandCursor)
        super(PageScene, self).mouseReleaseEvent(event)
        # refresh view after moving objects
        self.update()

    def mouseReleasePan(self, event):
        """
        Handles mouse releases for pan tool by setting cursor to an open hand.

        Args:
            event (QMouseEvent): given mouse release.

        Returns:
            None.

        """
        self.views()[0].setCursor(Qt.OpenHandCursor)
        super(PageScene, self).mouseReleaseEvent(event)
        self.views()[0].setZoomSelector()

    def mousePressImage(self, event):
        """
        Adds the selected image at the location the mouse is pressed and
        shows a message box with instructions.

        Args:
            event (QMouseEvent): given mouse click.

        Returns:
            None

        """
        if self.tempImagePath is not None:
            imageFilePath = self.tempImagePath
            command = CommandImage(self, event.scenePos(), QImage(imageFilePath))
            self.undoStack.push(command)
            self.tempImagePath = None
            # set the mode back to move
            self.parent.moveMode()

            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Image Information")
            msg.setText(
                "You can double-click on an Image to modify its scale and border."
            )
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()

    def dragEnterEvent(self, e):
        """ Handles drag/drop events. """
        if e.mimeData().hasFormat("text/plain"):
            # User has dragged in plain text from somewhere
            e.acceptProposedAction()
        elif e.mimeData().hasFormat(
            "application/x-qabstractitemmodeldatalist"
        ) or e.mimeData().hasFormat("application/x-qstandarditemmodeldatalist"):
            # User has dragged in a comment from the comment-list.
            e.setDropAction(Qt.CopyAction)
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        """ Handles drag and move events."""
        e.acceptProposedAction()

    def dropEvent(self, e):
        """ Handles drop events."""
        if e.mimeData().hasFormat("text/plain"):
            # Simulate a comment click.
            self.commentText = e.mimeData().text()
            self.commentDelta = "0"
            self.mousePressComment(e)

        elif e.mimeData().hasFormat(
            "application/x-qabstractitemmodeldatalist"
        ) or e.mimeData().hasFormat("application/x-qstandarditemmodeldatalist"):
            # Simulate a comment click.
            self.mousePressComment(e)
            # User has dragged in a comment from the comment-list.
            pass
        else:
            pass
        # After the drop event make sure pageview has the focus.
        self.views()[0].setFocus(Qt.TabFocusReason)

    def latexAFragment(self, txt):
        """
        Latex a fragment of text.

        Args:
            txt (str): text to be latexed.

        Returns:
            (png): a file containing the Latexed text.

        """
        return self.parent.latexAFragment(txt.strip())

    def event(self, event):
        """
        A fix for misread touchpad events on mac.

        Args:
            event (QEvent): A mouse event.

        Returns:
            (bool) True if the event is accepted, False otherwise.

        """
        if event.type() in [
            QEvent.TouchBegin,
            QEvent.TouchEnd,
            QEvent.TouchUpdate,
            QEvent.TouchCancel,
        ]:
            # ignore the event
            event.accept()
            return True
        else:
            return super(PageScene, self).event(event)

    def _debug_printUndoStack(self):
        """ A helper method for debugging the undoStack."""
        c = self.undoStack.count()
        for k in range(c):
            print(k, self.undoStack.text(k))

    def pickleSceneItems(self):
        """
        Pickles the saveable annotation items in the scene.

        Returns:
            (list[str]): a list containing all pickled elements.

        """
        lst = []
        for X in self.items():
            # check if object has "saveable" attribute and it is set to true.
            if getattr(X, "saveable", False):
                lst.append(X.pickle())
        return lst

    def unpickleSceneItems(self, lst):
        """
        Unpickles all items from the scene.

        Args:
            lst (list[list[str]]): a list containing lists of scene items'
                pickled information.

        Notes:
            Each pickled item type in lst is in a different format. Look in
            tools for more information.

        Returns:
            None, adds pickled items to the scene.

        """
        # clear all items from scene.
        for X in self.items():
            if any(
                isinstance(X, Y)
                for Y in [
                    ScoreBox,
                    QGraphicsPixmapItem,
                    UnderlyingImages,
                    GhostComment,
                    GhostDelta,
                    GhostText,
                ]
            ) and X is not isinstance(X, ImageItem):
                # as ImageItem is a subclass of QGraphicsPixmapItem, we have
                # to make sure ImageItems aren't skipped!
                continue
            else:
                command = CommandDelete(self, X)
                self.undoStack.push(command)
        # now load up the new items
        for X in lst:
            functionName = "unpickle{}".format(X[0])
            getattr(self, functionName, self.unpickleError)(X[1:])
        # now make sure focus is cleared from every item
        for X in self.items():
            X.setFocus(False)

    def unpickleError(self, X):
        """
        Log an error if an item of unknown format is attempted to be unpickled.

        Args:
            X: the unknown item.

        Returns:
            None, logs the error.

        """
        log.error("Unpickle error - What is {}".format(X))

    def unpickleCross(self, X):
        """ Unpickle a CrossItemObject and add it to scene. """
        if len(X) == 2:
            self.undoStack.push(CommandCross(self, QPointF(X[0], X[1])))

    def unpickleQMark(self, X):
        """ Unpickle a QMarkItemObject(question mark) and add it to scene. """
        if len(X) == 2:
            self.undoStack.push(CommandQMark(self, QPointF(X[0], X[1])))

    def unpickleTick(self, X):
        """ Unpickle a TickItemObject and add it to scene. """
        if len(X) == 2:
            self.undoStack.push(CommandTick(self, QPointF(X[0], X[1])))

    def unpickleArrow(self, X):
        """ Unpickle an ArrowItemObject and add it to scene. """
        if len(X) == 4:
            self.undoStack.push(
                CommandArrow(self, QPointF(X[0], X[1]), QPointF(X[2], X[3]))
            )

    def unpickleArrowDouble(self, X):
        """ Unpickle an ArrowDoubleItemObject and add it to scene. """
        if len(X) == 4:
            self.undoStack.push(
                CommandArrowDouble(self, QPointF(X[0], X[1]), QPointF(X[2], X[3]))
            )

    def unpickleLine(self, X):
        """ Unpickle a LineItemObject and add it to scene. """
        if len(X) == 4:
            self.undoStack.push(
                CommandLine(self, QPointF(X[0], X[1]), QPointF(X[2], X[3]))
            )

    def unpickleBox(self, X):
        """ Unpickle a BoxItemObject and add it to scene. """
        if len(X) == 4:
            self.undoStack.push(CommandBox(self, QRectF(X[0], X[1], X[2], X[3])))

    def unpickleEllipse(self, X):
        """ Unpickle a EllipseItemObject and add it to scene. """
        if len(X) == 4:
            self.undoStack.push(CommandEllipse(self, QRectF(X[0], X[1], X[2], X[3])))

    def unpickleText(self, X):
        """ Unpickle a TextItemObject and add it to scene. """
        if len(X) == 3:
            self.blurb = TextItem(self, self.fontSize)
            self.blurb.setPlainText(X[0])
            self.blurb.contents = X[0]
            self.blurb.setPos(QPointF(X[1], X[2]))
            self.blurb.setTextInteractionFlags(Qt.NoTextInteraction)
            # knows to latex it if needed.
            self.undoStack.push(CommandText(self, self.blurb, self.ink))

    def unpickleDelta(self, X):
        """ Unpickle a DeltaItemObject and add it to scene. """
        if len(X) == 3:
            self.undoStack.push(
                CommandDelta(self, QPointF(X[1], X[2]), X[0], self.fontSize)
            )

    def unpickleGroupDeltaText(self, X):
        """ Unpickle an GroupDTItemObject and add it to scene. """
        if len(X) == 4:
            self.blurb = TextItem(self, self.fontSize)
            self.blurb.setPlainText(X[3])
            self.blurb.contents = X[3]
            self.blurb.setPos(QPointF(X[0], X[1]))
            # knows to latex it if needed.
            self.undoStack.push(
                CommandGDT(self, QPointF(X[0], X[1]), X[2], self.blurb, self.fontSize)
            )

    def unpicklePen(self, X):
        """ Unpickle a PenItemObject and add it to scene. """
        if len(X) == 1:
            # Format is X = [ [['m',x,y], ['l',x,y], ['l',x,y],....] ]
            # Just assume (for moment) the above format - ie no format checks.
            pth = QPainterPath()
            # ['m',x,y]
            pth.moveTo(QPointF(X[0][0][1], X[0][0][2]))
            for Y in X[0][1:]:
                # ['l',x,y]
                pth.lineTo(QPointF(Y[1], Y[2]))
            self.undoStack.push(CommandPen(self, pth))

    def unpicklePenArrow(self, X):
        """ Unpickle an PenArrowItemObject and add it to scene. """
        if len(X) == 1:
            # Format is X = [ [['m',x,y], ['l',x,y], ['l',x,y],....] ]
            # Just assume (for moment) the above format - ie no format checks.
            pth = QPainterPath()
            # ['m',x,y]
            pth.moveTo(QPointF(X[0][0][1], X[0][0][2]))
            for Y in X[0][1:]:
                # ['l',x,y]
                pth.lineTo(QPointF(Y[1], Y[2]))
            self.undoStack.push(CommandPenArrow(self, pth))

    def unpickleHighlight(self, X):
        """ Unpickle a HighlightObjectItem and add it to scene. """
        if len(X) == 1:
            # Format is X = [ [['m',x,y], ['l',x,y], ['l',x,y],....] ]
            # Just assume (for moment) the above format.
            pth = QPainterPath()
            # ['m',x,y]
            pth.moveTo(QPointF(X[0][0][1], X[0][0][2]))
            for Y in X[0][1:]:
                # ['l',x,y]
                pth.lineTo(QPointF(Y[1], Y[2]))
            self.undoStack.push(CommandHighlight(self, pth))

    def unpickleImage(self, X):
        """ Unpickle an ImageItemObject and add it to scene. """
        if len(X) == 5:
            # extract data from encoding
            data = QByteArray().fromBase64(
                bytes(X[2][2 : len(X[2]) - 2], encoding="utf-8")
            )
            img = QImage()
            if img.loadFromData(data):
                img.loadFromData(data)
            else:
                log.error("Encountered a problem loading image.")
            self.undoStack.push(
                CommandImage(self, QPointF(X[0], X[1]), img, X[3], X[4], X[2])
            )

    def mousePressBox(self, event):
        """
        Handle mouse presses when box tool is selected.

        Notes:
            Creates a temp box which is updated as the mouse moves
            and replaced with a boxitem when the drawing is finished.
            If left-click then a highlight box will be drawn at finish,
            else if right-click or click+shift, an ellipse is drawn.

        Args:
            event (QMouseEvent): the mouse press event.

        Returns:
            None
        """
        if self.boxFlag != 0:
            # in middle of drawing a box, so ignore the new press
            return

        self.originPos = event.scenePos()
        self.currentPos = self.originPos
        # If left-click then a highlight box, else an ellipse.
        # Set a flag to tell the mouseReleaseBox function which.
        if (event.button() == Qt.RightButton) or (
            QGuiApplication.queryKeyboardModifiers() == Qt.ShiftModifier
        ):
            self.boxFlag = 2
            self.ellipseItem = QGraphicsEllipseItem(
                QRectF(self.originPos.x(), self.originPos.y(), 0, 0)
            )
            self.ellipseItem.setPen(self.ink)
            self.ellipseItem.setBrush(self.lightBrush)
            self.addItem(self.ellipseItem)
        else:
            self.boxFlag = 1
            # Create a temp box item for animating the drawing as the
            # user moves the mouse.
            # Do not push command onto undoStack until drawing finished.
            self.boxItem = QGraphicsRectItem(QRectF(self.originPos, self.currentPos))
            self.boxItem.setPen(self.ink)
            self.boxItem.setBrush(self.lightBrush)
            self.addItem(self.boxItem)

    def mouseMoveBox(self, event):
        """
        Update the size of the box as the mouse is moved.

        Notes:
            This animates the drawing of the box for the user.

        Args (QMouseEvent): the event of the mouse moving.

        Returns:
            None
        """
        self.currentPos = event.scenePos()
        if self.boxFlag == 2:
            if self.ellipseItem is None:

                self.ellipseItem = QGraphicsEllipseItem(
                    QRectF(self.originPos.x(), self.originPos.y(), 0, 0)
                )
            else:
                rx = abs(self.originPos.x() - self.currentPos.x())
                ry = abs(self.originPos.y() - self.currentPos.y())
                self.ellipseItem.setRect(
                    QRectF(
                        self.originPos.x() - rx, self.originPos.y() - ry, 2 * rx, 2 * ry
                    )
                )
        elif self.boxFlag == 1:
            if self.boxItem is None:
                self.boxItem = QGraphicsRectItem(
                    QRectF(self.originPos, self.currentPos)
                )
            else:
                self.boxItem.setRect(QRectF(self.originPos, self.currentPos))
        else:
            return

    def mouseReleaseBox(self, event):
        """
        Handle when the mouse is released after drawing a new box.

        Notes:
            Remove the temp boxitem (which was needed for animation)
            and create a command for either a highlighted box or opaque box
            depending on whether or not the boxflag was set.
            Push the resulting command onto the undo stack.

        Args:
            event (QMouseEvent): the given mouse release.

        Returns:
            None

        """
        if self.boxFlag == 0:
            return
        elif self.boxFlag == 1:
            self.removeItem(self.boxItem)
            # check if rect has some perimeter (allow long/thin) - need abs - see #977
            if (
                abs(self.boxItem.rect().width()) + abs(self.boxItem.rect().height())
                > 24
            ):
                command = CommandBox(self, self.boxItem.rect())
                self.undoStack.push(command)
        else:
            self.removeItem(self.ellipseItem)
            # check if ellipse has some area (don't allow long/thin)
            if (
                self.ellipseItem.rect().width() > 16
                and self.ellipseItem.rect().height() > 16
            ):
                command = CommandEllipse(self, self.ellipseItem.rect())
                self.undoStack.push(command)

        self.boxFlag = 0

    def mousePressLine(self, event):
        """
        Handle the mouse press when using the line tool to draw a line.

        Notes:
            Creates a temp line which is updated as the mouse moves
            and replaced with a line or arrow when the drawing is finished.
            Single arrowhead = right click or click+shift
            Double arrowhead = middle click or click+control
            No Arrows = left click or any other combination.

        Args:
            event (QMouseEvent): the given mouse press.

        Returns:
            None
        """
        # Set arrow flag to tell mouseReleaseLine to draw line or arrow
        if self.arrowFlag != 0:
            # mid line draw so ignore press
            return
        if (event.button() == Qt.RightButton) or (
            QGuiApplication.queryKeyboardModifiers() == Qt.ShiftModifier
        ):
            self.arrowFlag = 2
        elif (event.button() == Qt.MiddleButton) or (
            QGuiApplication.queryKeyboardModifiers() == Qt.ControlModifier
        ):
            self.arrowFlag = 4
        else:
            self.arrowFlag = 1
        # Create a temp line which is updated as mouse moves.
        # Do not push command onto undoStack until drawing finished.
        self.originPos = event.scenePos()
        self.currentPos = self.originPos
        self.lineItem = QGraphicsLineItem(QLineF(self.originPos, self.currentPos))
        self.lineItem.setPen(self.ink)
        self.addItem(self.lineItem)

    def mouseMoveLine(self, event):
        """
        Update the length of the box as the mouse is moved.

        Notes:
            This animates the drawing of the line for the user.

        Args:
            event (QMouseEvent): the event of the mouse moving.

        Returns:
            None
        """
        if self.arrowFlag:
            self.currentPos = event.scenePos()
            self.lineItem.setLine(QLineF(self.originPos, self.currentPos))

    def mouseReleaseLine(self, event):
        """
        Handle when the mouse is released after drawing a new line.

        Notes:
            Remove the temp lineitem (which was needed for animation)
            and create a command for either a line, arrow or double arrow
            depending on whether or not the arrow flag was set.
            Push the resulting command onto the undo stack.

        Args:
            event (QMouseEvent): the given mouse release.

        Returns:
            None
        """
        if self.arrowFlag == 0:
            return
        elif self.arrowFlag == 1:
            command = CommandLine(self, self.originPos, self.currentPos)
        elif self.arrowFlag == 2:
            command = CommandArrow(self, self.originPos, self.currentPos)
        elif self.arrowFlag == 4:
            command = CommandArrowDouble(self, self.originPos, self.currentPos)
        self.arrowFlag = 0
        self.removeItem(self.lineItem)
        # don't add if too short
        if (self.originPos - self.currentPos).manhattanLength() > 24:
            self.undoStack.push(command)

    def mousePressPen(self, event):
        """
        Handle the mouse press when using the pen tool to draw.

        Notes:
            normal pen = left click.
            highlight pen = right click or click+shift.
            pen with double-arrowhead = middle click or click+control.

        Args:
            event (QMouseEvent): the associated mouse press.

        Returns:
            None

        """
        if self.penFlag != 0:
            # in middle of drawing a path, so ignore
            return

        self.originPos = event.scenePos()
        self.currentPos = self.originPos
        # create the path.
        self.path = QPainterPath()
        self.path.moveTo(self.originPos)
        self.path.lineTo(self.currentPos)
        self.pathItem = QGraphicsPathItem(self.path)
        # If left-click then setPen to the standard thin-red
        # Else set to the highlighter or pen with arrows.
        # set penFlag so correct object created on mouse-release
        # non-zero value so we don't add to path after mouse-release
        if (event.button() == Qt.RightButton) or (
            QGuiApplication.queryKeyboardModifiers() == Qt.ShiftModifier
        ):
            self.pathItem.setPen(self.highlight)
            self.penFlag = 2
        elif (event.button() == Qt.MiddleButton) or (
            QGuiApplication.queryKeyboardModifiers() == Qt.ControlModifier
        ):
            # middle button is pen-path with arrows at both ends
            self.pathItem.setPen(self.ink)
            self.penFlag = 4
        else:
            self.pathItem.setPen(self.ink)
            self.penFlag = 1
        # Note - command not pushed onto stack until path is finished on
        # mouse-release.
        self.addItem(self.pathItem)

    def mouseMovePen(self, event):
        """
        Update the pen-path as the mouse is moved.

        Notes:
            This animates the drawing for the user.

        Args (QMouseEvent): the event of the mouse moving.

        Returns:
            None
        """
        if self.penFlag:
            self.currentPos = event.scenePos()
            self.path.lineTo(self.currentPos)
            self.pathItem.setPath(self.path)
        # do not add to path when flag is zero.

    def mouseReleasePen(self, event):
        """
        Handle when the mouse is released after drawing.

        Notes:
            Remove the temp pen-path (which was needed for animation)
            and create a command for either the pen-path or highlight
            path depending on whether or not the highlight flag was set.
            Push the resulting command onto the undo stack

        Args:
            event (QMouseEvent): the given mouse release.

        Returns:
            None
        """
        if self.penFlag == 0:
            return
        elif self.penFlag == 1:
            if self.path.length() <= 1:  # path is very short, so add a little blob.
                self.path.lineTo(event.scenePos() + QPointF(2, 0))
                self.path.lineTo(event.scenePos() + QPointF(2, 2))
                self.path.lineTo(event.scenePos() + QPointF(0, 2))
                self.path.lineTo(event.scenePos())
            command = CommandPen(self, self.path)
        elif self.penFlag == 2:
            if self.path.length() <= 1:  # path is very short, so add a blob.
                self.path.lineTo(event.scenePos() + QPointF(4, 0))
                self.path.lineTo(event.scenePos() + QPointF(4, 4))
                self.path.lineTo(event.scenePos() + QPointF(0, 4))
                self.path.lineTo(event.scenePos())
            command = CommandHighlight(self, self.path)
        elif self.penFlag == 4:
            command = CommandPenArrow(self, self.path)
        self.penFlag = 0
        self.removeItem(self.pathItem)
        self.undoStack.push(command)
        # don't add if too short - check by boundingRect
        # TODO: decide threshold for pen annotation size
        # if (
        #     self.pathItem.boundingRect().height() + self.pathItem.boundingRect().width()
        #     > 8
        # ):
        #     self.undoStack.push(command)

    def mousePressZoom(self, event):
        """
        Handle the mouse press when drawing a zoom box.

        Notes:
            If right-click (or shift) then zoom-out, else - don't do much
            until release.

        Args:
            event (QMouseEvent): given mouse press.

        Returns:
            None

        """
        if self.zoomFlag:
            return

        if (event.button() == Qt.RightButton) or (
            QGuiApplication.queryKeyboardModifiers() == Qt.ShiftModifier
        ):
            # sets the view rectangle and updates zoom-dropdown.
            self.views()[0].scale(0.8, 0.8)
            self.views()[0].centerOn(event.scenePos())
            self.views()[0].setZoomSelector(True)
            self.zoomFlag = 0
            return
        else:
            self.zoomFlag = 1

        self.originPos = event.scenePos()
        self.currentPos = self.originPos
        self.zoomBoxItem = QGraphicsRectItem(QRectF(self.originPos, self.currentPos))
        self.zoomBoxItem.setPen(Qt.blue)
        self.zoomBoxItem.setBrush(self.zoomBrush)
        self.addItem(self.zoomBoxItem)

    def mouseMoveZoom(self, event):
        """
        Update the size of the zoom box as the mouse is moved.

        Notes:
            This animates the drawing of the box for the user.

        Args (QMouseEvent): the event of the mouse moving.

        Returns:
            None
        """
        if self.zoomFlag:
            self.zoomFlag = 2  # drag started.
            self.currentPos = event.scenePos()
            if self.zoomBoxItem is None:
                log.error("EEK - should not be here")
                # somehow missed the mouse-press
                self.zoomBoxItem = QGraphicsRectItem(
                    QRectF(self.originPos, self.currentPos)
                )
                self.zoomBoxItem.setPen(self.ink)
                self.zoomBoxItem.setBrush(self.zoomBrush)
                self.addItem(self.zoomBoxItem)
            else:
                self.zoomBoxItem.setRect(QRectF(self.originPos, self.currentPos))

    def mouseReleaseZoom(self, event):
        """
        Handle when the mouse is released after drawing a new zoom box.

        Notes: Either zoom-in a little (if zoombox small), else fit the
            zoombox in view. Delete the zoombox afterwards and set the zoomflag
            back to 0.

        Args:
            event (QMouseEvent): the given mouse release.

        Returns:
            None

        """
        if self.zoomFlag == 0:
            return
        # check to see if box is quite small (since very hard
        # to click button without moving a little)
        # if small then set flag to 1 and treat like a click
        if self.zoomBoxItem.rect().height() < 8 and self.zoomBoxItem.rect().width() < 8:
            self.zoomFlag = 1

        if self.zoomFlag == 1:
            self.views()[0].scale(1.25, 1.25)
            self.views()[0].centerOn(event.scenePos())

        elif self.zoomFlag == 2:
            self.views()[0].fitInView(self.zoomBoxItem, Qt.KeepAspectRatio)

        # sets the view rectangle and updates zoom-dropdown.
        self.views()[0].setZoomSelector(True)
        # remove the box and put flag back.
        self.removeItem(self.zoomBoxItem)
        self.zoomFlag = 0

    def mousePressDelete(self, event):
        """
        Handle the mouse press when drawing a delete box.

        Notes:
            Nothing happens until button is released.

        Args:
            event (QMouseEvent): given mouse press.

        Returns:
            None

        """
        if self.deleteFlag:
            return

        self.deleteFlag = 1
        self.originPos = event.scenePos()
        self.currentPos = self.originPos
        self.delBoxItem = QGraphicsRectItem(QRectF(self.originPos, self.currentPos))
        self.delBoxItem.setPen(self.ink)
        self.delBoxItem.setBrush(self.deleteBrush)
        self.addItem(self.delBoxItem)

    def mouseMoveDelete(self, event):
        """
        Update the size of the delete box as the mouse is moved.

        Notes:
            This animates the drawing of the box for the user.

        Args (QMouseEvent): the event of the mouse moving.

        Returns:
            None
        """
        if self.deleteFlag:
            self.deleteFlag = 2  # drag started.
            self.currentPos = event.scenePos()
            if self.delBoxItem is None:
                log.error("EEK - should not be here")
                # somehow missed the mouse-press
                self.delBoxItem = QGraphicsRectItem(
                    QRectF(self.originPos, self.currentPos)
                )
                self.delBoxItem.setPen(self.ink)
                self.delBoxItem.setBrush(self.deleteBrush)
                self.addItem(self.delBoxItem)
            else:
                self.delBoxItem.setRect(QRectF(self.originPos, self.currentPos))

    def deleteIfLegal(self, item):
        """
        Deletes the item if it is a legal action.

        Notes:
            Can't delete the pageimage, scorebox, delete-box, ghostitem and
                its constituents.

        Args:
            item (QGraphicsItem): the item to be deleted.

        Returns:
            None

        """
        if item in [
            self.underImage,
            self.scoreBox,
            self.delBoxItem,
            self.ghostItem,
            self.ghostItem.di,
            self.ghostItem.blurb,
        ]:
            return
        else:
            command = CommandDelete(self, item)
            self.undoStack.push(command)

    def mouseReleaseDelete(self, event):
        """
        Handle when the mouse is released after drawing a new delete box.

        Notes:
             Remove the temp boxitem (which was needed for animation)
            and then delete all objects that lie within the box.
            Push the resulting commands onto the undo stack

        Args:
            event (QMouseEvent): the given mouse release.

        Returns:
            None

        """
        if self.deleteFlag == 0:
            return
        # check to see if box is quite small (since very hard
        # to click button without moving a little)
        # if small then set flag to 1 and treat like a click
        if self.delBoxItem.rect().height() < 8 and self.delBoxItem.rect().width() < 8:
            self.deleteFlag = 1

        if self.deleteFlag == 1:
            self.originPos = event.scenePos()
            # grab list of items in rectangle around click
            nearby = self.items(
                QRectF(self.originPos.x() - 5, self.originPos.y() - 5, 8, 8),
                mode=Qt.IntersectsItemShape,
                deviceTransform=QTransform(),
            )
            if len(nearby) == 0:
                return
            else:
                # delete the zeroth element of the list
                if nearby[0].group() is not None:  # object part of GroupDeltaText
                    self.deleteIfLegal(nearby[0].group())  # delete the group
                else:
                    self.deleteIfLegal(nearby[0])
        elif self.deleteFlag == 2:
            # check all items against the delete-box - this is a little clumsy, but works and there are not so many items typically.
            for X in self.items():
                # make sure is not background image or the scorebox, or the delbox itself.
                if X.collidesWithItem(self.delBoxItem, mode=Qt.ContainsItemShape):
                    if X.group() is None:
                        self.deleteIfLegal(X)
                    else:
                        pass  # is part of a group

        self.removeItem(self.delBoxItem)
        self.deleteFlag = 0  # put flag back.

    def hasAnyCrosses(self):
        """ Returns True if scene has any crosses, False otherwise. """
        for X in self.items():
            if isinstance(X, CrossItem):
                return True
        return False

    def hasOnlyCrosses(self):
        """ Returns True if scene has only crosses, False otherwise. """
        for X in self.items():
            if getattr(X, "saveable", None):
                if not isinstance(X, CrossItem):
                    return False
        return True

    def hasAnyComments(self):
        """
        Returns True if scene has any comments or text items,
        False otherwise.
        """
        for X in self.items():
            if isinstance(X, (TextItem, GroupDTItem)):
                return True
        return False

    def hasAnyTicks(self):
        """ Returns True if scene has any ticks. False otherwise. """
        for X in self.items():
            if isinstance(X, TickItem):
                return True
        return False

    def hasOnlyTicks(self):
        """ Returns True if scene has only ticks, False otherwise. """
        for X in self.items():
            if getattr(X, "saveable", None):
                if not isinstance(X, TickItem):
                    return False
        return True

    def hasOnlyTicksCrossesDeltas(self):
        """
        Checks if the image only has crosses, ticks or deltas.

        Returns:
             True if scene only has ticks/crosses/deltas, False otherwise.
        """
        for x in self.items():
            if getattr(x, "saveable", None):
                if not isinstance(x, (TickItem, CrossItem, DeltaItem)):
                    return False
        return True

    def checkAllObjectsInside(self):
        """
        Checks that all objects are within the boundary of the page.

        Returns:
            True if all objects are within the page's bounds, false otherwise.
        """
        for X in self.items():
            # check all items that are not the image or scorebox
            if (X is self.underImage) or (X is self.scoreBox):
                continue
            # make sure that it is not one of the images inside the underlying image.
            if X.parentItem() is self.underImage:
                continue
            # And be careful - there might be a GhostComment floating about
            if (
                isinstance(X, GhostComment)
                or isinstance(X, GhostDelta)
                or isinstance(X, GhostText)
            ):
                continue
            # make sure is inside image
            if not X.collidesWithItem(self.underImage, mode=Qt.ContainsItemShape):
                return False
        return True

    def updateGhost(self, dlt, txt):
        """
        Updates the ghost object based on the delta and text.

        Args:
            dlt (int): given mark-delta.
            txt (str): the given text.

        Returns:
            None

        """
        self.ghostItem.changeComment(dlt, txt)

    def exposeGhost(self):
        """ Exposes the ghost object."""
        self.ghostItem.setVisible(True)

    def hideGhost(self):
        """ Hides the ghost object."""
        self.ghostItem.setVisible(False)

    def mouseMoveComment(self, event):
        """
        Handles mouse moving with a comment.

        Args:
            event (QMouseEvent): the event of the mouse moving.

        Returns:
            None
        """
        if not self.ghostItem.isVisible():
            self.ghostItem.setVisible(True)
        self.ghostItem.setPos(event.scenePos())

    def mouseMoveDelta(self, event):
        """
        Handles mouse moving with a delta.

        Args:
            event (QMouseEvent): the event of the mouse moving.

        Returns:
            None
        """
        if not self.ghostItem.isVisible():
            self.ghostItem.setVisible(True)
        self.ghostItem.setPos(event.scenePos())

    def setTheMark(self, newMark):
        """
        Sets the new mark/score for the paper.

        Args:
            newMark(int): the new mark/score for the paper.

        Returns:
            None
        """
        self.score = newMark
        self.scoreBox.changeScore(self.score)

    def changeTheMark(self, deltaMarkString, undo=False):
        """
        Changes the new mark/score for the paper based on the delta.

        Args:
            deltaMarkString(str): a string containing the delta integer.
            undo (bool): True if delta is being undone or removed,
                False otherwise.

        Returns:
            None

        """
        # if is an undo then we need a minus-sign here
        # because we are undoing the delta.
        # note that this command is passed a string
        deltaMark = int(deltaMarkString)
        if undo:
            self.score -= deltaMark
        else:
            self.score += deltaMark
        self.scoreBox.changeScore(self.score)
        self.parent.changeMark(self.score)
        # if we are in comment mode then the comment might need updating
        if self.mode == "comment":
            self.changeTheComment(
                self.markDelta, self.commentText, annotatorUpdate=False
            )

    def changeTheDelta(self, newDelta, annotatorUpdate=False):
        """
        Changes the new mark/score for the paper based on the delta.

        Args:
            newDelta (str): a string containing the delta integer.
            annotatorUpdate (bool): true if annotator should be updated,
                false otherwise.

        Returns:
            True if the delta is legal, false otherwise.

        """
        legalDelta = self.isLegalDelta(newDelta)
        self.markDelta = newDelta

        if annotatorUpdate:
            gpt = QCursor.pos()  # global mouse pos
            vpt = self.views()[0].mapFromGlobal(gpt)  # mouse pos in view
            spt = self.views()[0].mapToScene(vpt)  # mouse pos in scene
            self.ghostItem.setPos(spt)

        self.commentDelta = self.markDelta
        self.commentText = ""
        self.updateGhost(self.commentDelta, self.commentText)
        self.exposeGhost()

        return legalDelta

    def undo(self):
        """ Undoes a given action."""
        self.undoStack.undo()

    def redo(self):
        """ Redoes a given action."""
        self.undoStack.redo()

    def isLegalDelta(self, n):
        """
        Verifies if a delta is legal.

        Notes:
            A legal delta is one that would not push the paper's score below 0
                or above maxMark.

        Args:
            n (str): a string containing the delta integer.

        Returns:
            True if the delta is legal, false otherwise.

        """
        # TODO: try, return True if not int?
        n = int(n)
        lookingAhead = self.score + n
        if lookingAhead < 0 or lookingAhead > self.maxMark:
            return False
        return True

    def changeTheComment(self, delta, text, annotatorUpdate=True):
        """
        Changes the new comment for the paper based on the delta and text.

        Args:
            delta (str): a string containing the delta integer.
            text (str): the text in the comment.
            annotatorUpdate (bool): true if annotator should be updated,
                false otherwise.

        Returns:
            None

        """
        # if this update comes from the annotator, then we need to store a
        # copy of the mark-delta for future and also set the mode.
        if annotatorUpdate:
            gpt = QCursor.pos()  # global mouse pos
            vpt = self.views()[0].mapFromGlobal(gpt)  # mouse pos in view
            spt = self.views()[0].mapToScene(vpt)  # mouse pos in scene
            self.ghostItem.setPos(spt)
            self.markDelta = delta
            self.setToolMode("comment")
            self.exposeGhost()  # unhide the ghostitem
        # if we have passed ".", then we don't need to do any
        # delta calcs, the ghost item knows how to handle it.
        if delta != ".":
            id = int(delta)

            # we pass the actual comment-delta to this (though it might be
            # suppressed in the commentlistwidget).. so we have to check the
            # the delta is legal for the marking style. if delta<0 when mark
            # up OR delta>0 when mark down OR mark-total then pass delta="."
            if (
                (id < 0 and self.markStyle == 2)
                or (id > 0 and self.markStyle == 3)
                or self.markStyle == 1
            ):
                delta = "."
        self.commentDelta = delta
        self.commentText = text
        self.updateGhost(delta, text)

    def noAnswer(self, delta):
        """
        Handles annotating the page if there is little or no answer written.

        Args:
            delta (int): the mark to be assigned to the page.

        Returns:
            None

        """
        br = self.sceneRect()
        # put lines through the page
        w = br.right()
        h = br.bottom()
        command = CommandLine(
            self, QPointF(w * 0.1, h * 0.1), QPointF(w * 0.9, h * 0.9)
        )
        self.undoStack.push(command)
        command = CommandLine(
            self, QPointF(w * 0.9, h * 0.1), QPointF(w * 0.1, h * 0.9)
        )
        self.undoStack.push(command)

        # build a delta-comment
        self.blurb = TextItem(self, self.fontSize)
        self.blurb.setPlainText("NO ANSWER GIVEN")
        command = CommandGDT(
            self, br.center() + br.topRight() / 8, delta, self.blurb, self.fontSize
        )
        self.undoStack.push(command)
