__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai", "Matt Coles"]
__license__ = "AGPLv3"

import json

from PyQt5.QtCore import Qt, QElapsedTimer, QEvent, QLineF, QPointF, QRectF
from PyQt5.QtGui import (
    QBrush,
    QColor,
    QGuiApplication,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QTransform,
    QFont,
)
from PyQt5.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsPathItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QUndoStack,
    QGraphicsTextItem,
)

# Import all the tool commands for undo/redo stack.
from tools import (
    CommandArrow,
    CommandArrowDouble,
    CommandBox,
    CommandCross,
    CommandDelete,
    CommandDelta,
    CommandEllipse,
    CommandHighlight,
    CommandLine,
    CommandPen,
    CommandPenArrow,
    CommandQMark,
    CommandText,
    CommandTick,
    CommandGDT,
    DeltaItem,
    TextItem,
    GroupDTItem,
    GhostComment,
    GhostDelta,
    GhostText,
)


class ScoreBox(QGraphicsTextItem):
    """A simple graphics item which is place on the top-left
    corner of the group-image to indicate the current total mark.
    Drawn with a rounded-rectangle border.
    """

    def __init__(self, fontsize=10, maxScore=1, score=0):
        super(ScoreBox, self).__init__()
        self.score = score
        self.maxScore = maxScore
        self.setDefaultTextColor(Qt.red)
        self.font = QFont("Helvetica")
        self.fontSize = min(fontsize * 3.5, 36)
        self.font.setPointSizeF(self.fontSize)
        self.setFont(self.font)
        # Not editable.
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        self.setPos(4, 4)
        self.changeScore(0)

    def changeScore(self, x):
        # set the current mark.
        self.score = x
        self.setPlainText(
            "{} out of {}".format(str(x).zfill(2), str(self.maxScore).zfill(2))
        )

    def changeMax(self, x):
        # set the max-mark.
        self.maxScore = x
        self.setPlainText(
            "{} out of {}".format(str(x).zfill(2), str(self.maxScore).zfill(2))
        )

    def paint(self, painter, option, widget):
        # paint the text with a simple rounded rectangle border.
        painter.setPen(QPen(Qt.red, 2))
        painter.setBrush(QBrush(Qt.white))
        painter.drawRoundedRect(option.rect, 10, 10)
        super(ScoreBox, self).paint(painter, option, widget)


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
    "pen": "mousePressPen",
    "text": "mousePressText",
    "tick": "mousePressTick",
    "zoom": "mousePressZoom",
}
mouseMove = {
    "box": "mouseMoveBox",
    "delete": "mouseMoveDelete",
    "line": "mouseMoveLine",
    "pen": "mouseMovePen",
    "comment": "mouseMoveComment",
}
mouseRelease = {
    "box": "mouseReleaseBox",
    "delete": "mouseReleaseDelete",
    "line": "mouseReleaseLine",
    "move": "mouseReleaseMove",
    "pen": "mouseReleasePen",
    "pan": "mouseReleasePan",
}


class PageScene(QGraphicsScene):
    """Extend the graphicsscene so that it knows how to translate
    mouse-press/move/release into operations on graphicsitems and
    textitems.
    """

    def __init__(self, parent, imgName, maxMark, score, markStyle):
        super(PageScene, self).__init__(parent)
        self.parent = parent
        # Grab filename of groupimage,
        self.imageName = imgName
        self.maxMark = maxMark
        self.score = score
        self.markStyle = markStyle
        # Tool mode - initially set it to "move"
        self.mode = "move"
        # build pixmap and graphicsitem.
        self.image = QPixmap(imgName)
        self.imageItem = QGraphicsPixmapItem(self.image)
        self.imageItem.setTransformationMode(Qt.SmoothTransformation)
        # Build scene rectangle to fit the image, and place image into it.
        self.setSceneRect(0, 0, self.image.width(), self.image.height())
        self.addItem(self.imageItem)
        # Add a timer to prevent button-mashing
        self.masher = QElapsedTimer()
        self.masher.start()
        # initialise the undo-stack
        self.undoStack = QUndoStack()

        # Get current font size to use as base for size of comments etc.
        self.fontSize = self.font().pointSizeF()
        # Define standard pen, highlight, fill, light-fill
        self.ink = QPen(Qt.red, 2)
        self.highlight = QPen(QColor(255, 255, 0, 64), 50)
        self.brush = QBrush(self.ink.color())
        self.lightBrush = QBrush(QColor(255, 255, 0, 16))
        self.deleteBrush = QBrush(QColor(255, 0, 0, 16))
        # Flags to indicate if drawing an arrow (vs line),
        # highlight (vs regular pen),
        # box (vs ellipse), area-delete vs point.
        self.arrowFlag = 0
        self.penFlag = 0
        self.boxFlag = 0
        self.deleteFlag = 0
        # Will need origin, current position, last position points.
        self.originPos = QPointF(0, 0)
        self.currentPos = QPointF(0, 0)
        self.lastPos = QPointF(0, 0)
        # Need a path, pathitem, boxitem, lineitem, textitem, deleteitem
        self.path = QPainterPath()
        self.pathItem = QGraphicsPathItem()
        self.boxItem = QGraphicsRectItem()
        self.delBoxItem = QGraphicsRectItem()
        self.ellipseItem = QGraphicsEllipseItem()
        self.lineItem = QGraphicsLineItem()
        self.blurb = TextItem(self, self.fontSize)
        self.deleteItem = None
        # Add a ghost comment to scene, but make it invisible
        self.ghostItem = GhostComment("1", "blah", self.fontSize)
        self.ghostItem.setVisible(False)
        self.addItem(self.ghostItem)
        # Set a mark-delta, comment-text and comment-delta.
        self.markDelta = 0
        self.commentText = ""
        self.commentDelta = "0"
        self.legalDelta = True
        # Build a scorebox and set it above all our other graphicsitems
        # so that it cannot be overwritten.
        # set up "k out of n" where k=current score, n = max score.
        self.scoreBox = ScoreBox(self.fontSize, self.maxMark, self.score)
        self.scoreBox.setZValue(10)
        self.addItem(self.scoreBox)

    def setMode(self, mode):
        self.mode = mode
        # if current mode is not comment, make sure the ghostcomment is hidden
        if self.mode != "comment":
            self.hideGhost()
        # if mode is "pan", set the view to be able to drag about, else turn that off
        if self.mode == "pan":
            self.views()[0].setDragMode(1)
        else:
            self.views()[0].setDragMode(0)

    def getComments(self):
        comments = []
        for X in self.items():
            if isinstance(X, TextItem):
                comments.append(X.contents)
        return comments

    def countComments(self):
        count = 0
        for X in self.items():
            if type(X) is TextItem:
                count += 1
        return count

    def areThereAnnotations(self):
        # there are at least 2 items = the pageimage and the scorebox
        # there must be more than 2 items for there to be any annotations
        return len(self.items()) > 2

    def save(self):
        """ Save the annotated group-image.
        That is, overwrite the imagefile with a dump of the current
        scene and all its graphics items.
        """
        # Get the width and height of the image
        w = self.image.width()
        h = self.image.height()
        # Create an output pixmap and painter (to export it)
        oimg = QPixmap(w, h)
        exporter = QPainter(oimg)
        # Render the scene via the painter
        self.render(exporter)
        exporter.end()
        # Save the result to file.
        oimg.save(self.imageName)

    def keyPressEvent(self, event):
        # Check time since last press
        # if too short then don't do anything (unless typing text)
        if self.masher.restart() < 50 and self.mode != "text":
            print("Colin - please don't mash keys")
            return
        # The escape key removes focus from the graphicsscene.
        # Other key press events are passed on.
        if event.key() == Qt.Key_Escape:
            self.clearFocus()
        else:
            super(PageScene, self).keyPressEvent(event)

    # Mouse events call various tool functions
    # These events use the dictionaries defined above to
    # translate the current tool-mode into function calls
    def mousePressEvent(self, event):
        # Check time since last press
        # if too short then don't do anything
        if self.masher.restart() < 50:
            print("Colin - please don't mash buttons")
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
        # Similar to mouse-press but for mouse-move.
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
        """Create a marked-comment-item from whatever is the currently
        selected comment. This creates a Delta-object and then also
        a text-object. They should be side-by-side with the delta
        appearing roughly at the mouse-click.
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

        # grab the location of the mouse-click
        pt = event.scenePos()
        # build the textitem
        self.blurb = TextItem(self, self.fontSize)
        self.blurb.setPlainText(self.commentText)
        self.blurb.contents = self.commentText  # for pickling
        # move to correct point - update if only text no delta
        self.blurb.setPos(pt)
        # If the mark-delta of the comment is non-zero then
        # create a delta-object with a different offset.
        # else just place the comment.

        if self.commentDelta == "." or not self.legalDelta:
            # make sure blurb has text interaction turned off
            prevState = self.blurb.textInteractionFlags()
            self.blurb.setTextInteractionFlags(Qt.NoTextInteraction)
            # Update position of text
            self.blurb.moveBy(0, -self.blurb.boundingRect().height() / 2)
            command = CommandText(self, self.blurb, self.ink)
            self.undoStack.push(command)
            # return blurb to previous state
            self.blurb.setTextInteractionFlags(prevState)
        else:
            command = CommandGDT(self, pt, self.commentDelta, self.blurb, self.fontSize)
            # push the delta onto the undo stack.
            self.undoStack.push(command)

    def mousePressCross(self, event):
        """Create a cross/?-mark/tick object under the mouse click
        if left/middle/right mouse button.
        """
        # Grab the mouseclick location and create command.
        pt = event.scenePos()
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
        # push onto the stack.
        self.undoStack.push(command)

    def mousePressDelta(self, event):
        """Create the mark-delta object or ?-mark or cross/tick object
        under the mouse click if left/middle/right mouse button.
        If mark-delta is positive then right-mouse makes a cross.
        If mark-delta is negative then right-mouse makes a tick.
        """
        # Grab mouse click location and create command.
        pt = event.scenePos()
        if (event.button() == Qt.RightButton) or (
            QGuiApplication.queryKeyboardModifiers() == Qt.ShiftModifier
        ):
            if self.markDelta > 0:
                command = CommandCross(self, pt)
            else:
                command = CommandTick(self, pt)
        elif (event.button() == Qt.MiddleButton) or (
            QGuiApplication.queryKeyboardModifiers() == Qt.ControlModifier
        ):
            command = CommandQMark(self, pt)
        else:
            if self.legalDelta:
                command = CommandDelta(self, pt, self.markDelta, self.fontSize)
            else:
                # don't do anything
                return
        # push command onto undoStack.
        self.undoStack.push(command)

    def mousePressMove(self, event):
        """The mouse press while move-tool selected changes the cursor to
        a closed hand, but otherwise does not do much.
        The actual moving of objects is handled by themselves since they
        know how to handle the ItemPositionChange signal as a move-command.
        """
        self.views()[0].setCursor(Qt.ClosedHandCursor)
        super(PageScene, self).mousePressEvent(event)

    def mousePressText(self, event):
        """Create a textobject under the mouse click, unless there
        is already a textobject under the click.

        """
        # Find the object under the mouseclick.
        under = self.itemAt(event.scenePos(), QTransform())
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

        # Now we construct a text object, give it focus
        # (which fires up the editor on that object), and
        # then push it onto the undo-stack.

        self.originPos = event.scenePos()
        self.blurb = TextItem(self, self.fontSize)
        # move so centred under cursor
        self.originPos -= QPointF(0, self.blurb.boundingRect().height() / 2)
        self.blurb.setPos(self.originPos)
        self.blurb.setFocus()
        command = CommandText(self, self.blurb, self.ink)
        self.undoStack.push(command)

    def mousePressTick(self, event):
        """Create a tick/?-mark/cross object under the mouse click
        if left/middle/right mouse button.
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

    def mousePressZoom(self, event):
        """Mouse-click changes the view-scale on the parent
        qgraphicsview. left zooms in, right zooms out.
        """
        if (event.button() == Qt.RightButton) or (
            QGuiApplication.queryKeyboardModifiers() == Qt.ShiftModifier
        ):
            self.views()[0].scale(0.8, 0.8)
        else:
            self.views()[0].scale(1.25, 1.25)
        self.views()[0].centerOn(event.scenePos())
        # sets the view rectangle and updates zoom-dropdown.
        self.views()[0].zoomNull(True)

    # Mouse release tool functions.
    # Most of these delete the temp-object (eg box / line)
    # and replaces it with the (more) permanent graphics object.

    def mouseReleaseMove(self, event):
        """Sets the cursor back to an open hand."""
        self.views()[0].setCursor(Qt.OpenHandCursor)
        super(PageScene, self).mouseReleaseEvent(event)
        # refresh view after moving objects
        self.update()

    def mouseReleasePan(self, event):
        """Update the current stored view rectangle."""
        super(PageScene, self).mouseReleaseEvent(event)
        self.views()[0].zoomNull()

    # Handle drag / drop events
    def dragEnterEvent(self, e):
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
        e.acceptProposedAction()

    def dropEvent(self, e):
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
        return self.parent.latexAFragment(txt.strip())

    # A fix (hopefully) for misread touchpad events on mac
    def event(self, event):
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

    def printUndoStack(self):
        c = self.undoStack.count()
        for k in range(c):
            print(k, self.undoStack.text(k))

    def pickleSceneItems(self):
        lst = []
        for X in self.items():
            # don't pickle the scorebox or background image, or ghostcomment
            if any(
                isinstance(X, Y)
                for Y in [
                    ScoreBox,
                    QGraphicsPixmapItem,
                    GhostComment,
                    GhostDelta,
                    GhostText,
                ]
            ):
                continue
            # If text or delta, check if part of GroupDeltaText
            if isinstance(X, DeltaItem) or isinstance(X, TextItem):
                if X.group() is not None:  # object part of GroupDeltaText
                    continue
            if isinstance(X, QGraphicsPathItem):
                if X.group() is not None:  # object part of penarrowitem
                    continue
            lst.append(X.pickle())
        return lst

    def unpickleSceneItems(self, lst):
        # clear all items from scene.
        for X in self.items():
            if any(
                isinstance(X, Y)
                for Y in [
                    ScoreBox,
                    QGraphicsPixmapItem,
                    GhostComment,
                    GhostDelta,
                    GhostText,
                ]
            ):
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
        print("Unpickle error - What is {}".format(X))

    def unpickleCross(self, X):
        if len(X) == 2:
            self.undoStack.push(CommandCross(self, QPointF(X[0], X[1])))

    def unpickleQMark(self, X):
        if len(X) == 2:
            self.undoStack.push(CommandQMark(self, QPointF(X[0], X[1])))

    def unpickleTick(self, X):
        if len(X) == 2:
            self.undoStack.push(CommandTick(self, QPointF(X[0], X[1])))

    def unpickleArrow(self, X):
        if len(X) == 4:
            self.undoStack.push(
                CommandArrow(self, QPointF(X[0], X[1]), QPointF(X[2], X[3]))
            )

    def unpickleArrowDouble(self, X):
        if len(X) == 4:
            self.undoStack.push(
                CommandArrowDouble(self, QPointF(X[0], X[1]), QPointF(X[2], X[3]))
            )

    def unpickleLine(self, X):
        if len(X) == 4:
            self.undoStack.push(
                CommandLine(self, QPointF(X[0], X[1]), QPointF(X[2], X[3]))
            )

    def unpickleBox(self, X):
        if len(X) == 4:
            self.undoStack.push(CommandBox(self, QRectF(X[0], X[1], X[2], X[3])))

    def unpickleEllipse(self, X):
        if len(X) == 4:
            self.undoStack.push(CommandEllipse(self, QRectF(X[0], X[1], X[2], X[3])))

    def unpickleText(self, X):
        if len(X) == 3:
            self.blurb = TextItem(self, self.fontSize)
            self.blurb.setPlainText(X[0])
            self.blurb.contents = X[0]
            self.blurb.setPos(QPointF(X[1], X[2]))
            # knows to latex it if needed.
            self.undoStack.push(CommandText(self, self.blurb, self.ink))

    def unpickleDelta(self, X):
        if len(X) == 3:
            self.undoStack.push(
                CommandDelta(self, QPointF(X[1], X[2]), X[0], self.fontSize)
            )

    def unpickleGroupDeltaText(self, X):
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

    # Mouse press tool functions
    def mousePressBox(self, event):
        """Creates a temp box which is updated as the mouse moves
        and replaced with a boxitem when the drawing is finished.
        If left-click then a highlight box will be drawn at finish,
        else an ellipse is drawn
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
        """Update the box as the mouse is moved. This
        animates the drawing of the box for the user.
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
        """Remove the temp boxitem (which was needed for animation)
        and create a command for either a highlighted box or opaque box
        depending on whether or not the boxflag was set.
        Push the resulting command onto the undo stack
        """
        if self.boxFlag == 0:
            return
        elif self.boxFlag == 1:
            self.removeItem(self.boxItem)
            command = CommandBox(self, self.boxItem.rect())
        else:
            self.removeItem(self.ellipseItem)
            command = CommandEllipse(self, self.ellipseItem.rect())

        self.undoStack.push(command)
        self.boxFlag = 0

    def mousePressLine(self, event):
        """Creates a temp line which is updated as the mouse moves
        and replaced with a line or arrow when the drawing is finished.
        If left-click then a line will be drawn at finish,
        else an arrow is drawn at finish.
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
        """Update the line as the mouse is moved. This
        animates the drawing of the line for the user.
        """
        if self.arrowFlag is not 0:
            self.currentPos = event.scenePos()
            self.lineItem.setLine(QLineF(self.originPos, self.currentPos))

    def mouseReleaseLine(self, event):
        """Remove the temp lineitem (which was needed for animation)
        and create a command for either a line or an arrow
        depending on whether or not the arrow flag was set.
        Push the resulting command onto the undo stack
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
        self.undoStack.push(command)

    def mousePressPen(self, event):
        """Start drawing either a pen-path (left-click) or
        highlight path (right-click).
        Set the path-pen accordingly.
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
        """Update the pen-path as the mouse is moved. This
        animates the drawing for the user.
        """
        if self.penFlag is not 0:
            self.currentPos = event.scenePos()
            self.path.lineTo(self.currentPos)
            self.pathItem.setPath(self.path)
        # do not add to path when flag is zero.

    def mouseReleasePen(self, event):
        """Remove the temp pen-path (which was needed for animation)
        and create a command for either the pen-path or highlight
        path depending on whether or not the highlight flag was set.
        Push the resulting command onto the undo stack
        """
        if self.penFlag == 0:
            return
        elif self.penFlag == 1:
            command = CommandPen(self, self.path)
        elif self.penFlag == 2:
            command = CommandHighlight(self, self.path)
        elif self.penFlag == 4:
            command = CommandPenArrow(self, self.path)
        self.penFlag = 0
        self.removeItem(self.pathItem)
        self.undoStack.push(command)

    def mousePressDelete(self, event):
        """Start drawing a delete-box. Nothing happens until button is released.
        """
        if self.deleteFlag is not 0:
            return

        self.deleteFlag = 1
        self.originPos = event.scenePos()
        self.currentPos = self.originPos
        self.delBoxItem = QGraphicsRectItem(QRectF(self.originPos, self.currentPos))
        self.delBoxItem.setPen(self.ink)
        self.delBoxItem.setBrush(self.deleteBrush)
        self.addItem(self.delBoxItem)

    def mouseMoveDelete(self, event):
        """Update the box as the mouse is moved. This
        animates the drawing of the box for the user.
        """
        if self.deleteFlag is not 0:
            self.deleteFlag = 2  # drag started.
            self.currentPos = event.scenePos()
            if self.delBoxItem is None:
                print("EEK - should not be here")
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
        if (
            (item is self.imageItem)
            or (item is self.scoreBox)
            or (item is self.delBoxItem)
        ):
            return
        else:
            command = CommandDelete(self, item)
            self.undoStack.push(command)

    def mouseReleaseDelete(self, event):
        """Remove the temp boxitem (which was needed for animation)
        and then delete all objects that lie within the box.
        Push the resulting commands onto the undo stack
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

    def checkAllObjectsInside(self):
        for X in self.items():
            # check all items that are not the image or scorebox
            if (X is self.imageItem) or (X is self.scoreBox):
                continue
            # And be careful - there might be a GhostComment floating about
            if (
                isinstance(X, GhostComment)
                or isinstance(X, GhostDelta)
                or isinstance(X, GhostText)
            ):
                continue
            # make sure is inside image
            if not X.collidesWithItem(self.imageItem, mode=Qt.ContainsItemShape):
                return False
        return True

    def updateGhost(self, dlt, txt):
        self.ghostItem.changeComment(dlt, txt)

    def exposeGhost(self):
        self.ghostItem.setVisible(True)

    def hideGhost(self):
        self.ghostItem.setVisible(False)

    def mouseMoveComment(self, event):
        if not self.ghostItem.isVisible():
            self.ghostItem.setVisible(True)
        self.ghostItem.setPos(event.scenePos())

    def setTheMark(self, newMark):
        self.score = newMark
        self.scoreBox.changeScore(self.score)

    def changeTheMark(self, deltaMark, undo=False):
        # if is an undo then we need a minus-sign here
        # because we are undoing the delta.
        if undo:
            self.score -= deltaMark
        else:
            self.score += deltaMark
        self.scoreBox.changeScore(self.score)
        # now look ahead to see what happens if we redo this delta
        lookingAhead = self.score + deltaMark
        if lookingAhead < 0 or lookingAhead > self.maxMark:
            self.legalDelta = False
        else:
            self.legalDelta = True
        self.parent.changeMark(self.score)
        # if we are in comment mode then the comment might need updating
        self.changeTheComment(self.markDelta, self.commentText, annotatorUpdate=False)

    def changeTheDelta(self, newDelta):
        self.markDelta = newDelta
        lookingAhead = self.score + self.markDelta
        if lookingAhead < 0 or lookingAhead > self.maxMark:
            self.legalDelta = False
        else:
            self.legalDelta = True
        return self.legalDelta

    def undo(self):
        self.undoStack.undo()

    def redo(self):
        self.undoStack.redo()

    def changeTheComment(self, delta, text, annotatorUpdate=True):
        # if this update comes from the annotator, then
        # we need to store a copy of the mark-delta for future
        # and also set the mode.
        if annotatorUpdate:
            self.markDelta = delta
            self.setMode("comment")
            # unhide the ghostitem
            self.exposeGhost()
        # make sure the ghost item stays hidden unless needed
        # if self.mode != "comment":
        # self.hideGhost()
        if self.markStyle == 2:  # mark up
            # if delta is too positive, set to 0
            if delta < 0 or self.score + delta > self.maxMark:
                delta = 0
        elif self.markStyle == 3:  # mark down
            # if delta is too negative, set to 0
            if delta > 0 or self.score + delta < 0:
                delta = 0
        else:  # mark total
            # no delta is used, so set it to 0.
            delta = 0
        self.commentDelta = delta
        self.commentText = text
        self.updateGhost(delta, text)
