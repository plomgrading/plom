__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai", "Matt Coles"]
__license__ = "AGPLv3"

import json

from PyQt5.QtCore import Qt, QEvent, QLineF, QPointF, QRectF, pyqtSignal
from PyQt5.QtGui import (
    QBrush,
    QColor,
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
    CommandBox,
    CommandCross,
    CommandDelete,
    CommandDelta,
    CommandEllipse,
    CommandHighlight,
    CommandLine,
    CommandPen,
    CommandQMark,
    CommandText,
    CommandTick,
    TextItem,
    CommandWhiteBox,
)


class ScoreBox(QGraphicsTextItem):
    """A simple graphics item which is place on the top-left
    corner of the group-image to indicate the current total mark.
    Drawn with a rounded-rectangle border.
    """

    def __init__(self, fontsize=10):
        super(ScoreBox, self).__init__()
        self.score = 0
        self.maxScore = 0
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
mouseMove = {"box": "mouseMoveBox", "line": "mouseMoveLine", "pen": "mouseMovePen"}
mouseRelease = {
    "box": "mouseReleaseBox",
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

    # When a delta is created or deleted, need to emit a markChangedSignal
    # which will be picked up by the annotation widget to update
    markChangedSignal = pyqtSignal(int)

    def __init__(self, parent, imgName):
        super(PageScene, self).__init__(parent)
        # Grab filename of groupimage, build pixmap and graphicsitem.
        self.imageName = imgName
        self.image = QPixmap(imgName)
        self.imageItem = QGraphicsPixmapItem(self.image)
        self.imageItem.setTransformationMode(Qt.SmoothTransformation)
        # Build scene rectangle to fit the image, and place image into it.
        self.setSceneRect(0, 0, self.image.width(), self.image.height())
        self.addItem(self.imageItem)
        # initialise the undo-stack
        self.undoStack = QUndoStack()
        # Starting mode is move.
        self.mode = "move"
        # Get current font size to use as base for size of comments etc.
        self.fontSize = self.font().pointSizeF()
        # Define standard pen, highlight, fill, light-fill
        self.ink = QPen(Qt.red, 2)
        self.highlight = QPen(QColor(255, 255, 0, 64), 50)
        self.brush = QBrush(self.ink.color())
        self.lightBrush = QBrush(QColor(255, 255, 0, 16))
        # Flags to indicate if drawing an arrow (vs line),
        # highlight (vs regular pen),
        # whitebox (vs regular box) --- now ellipse vs box
        self.arrowFlag = 0
        self.highlightFlag = 0
        self.ellipseFlag = 0
        # Will need origin, current position, last position points.
        self.originPos = QPointF(0, 0)
        self.currentPos = QPointF(0, 0)
        self.lastPos = QPointF(0, 0)
        # Need a path, pathitem, boxitem, lineitem, textitem, deleteitem
        self.path = QPainterPath()
        self.pathItem = QGraphicsPathItem()
        self.boxItem = QGraphicsRectItem()
        self.ellipseItem = QGraphicsEllipseItem()
        self.lineItem = QGraphicsLineItem()
        self.blurb = TextItem(self, self.fontSize)
        self.deleteItem = None
        # Set a mark-delta, comment-text and comment-delta.
        self.markDelta = 0
        self.commentText = ""
        self.commentDelta = 0
        # Build a scorebox and set it above all our other graphicsitems
        # so that it cannot be overwritten.
        self.scoreBox = ScoreBox(self.fontSize)
        self.scoreBox.setZValue(10)
        self.addItem(self.scoreBox)

    def saveComments(self):
        comments = []
        for X in self.items():
            if type(X) is TextItem:
                comments.append(X.contents)
        # image file is <blah>.png, save comments as <blah>.json
        with open(self.imageName[:-3] + "json", "w") as commentFile:
            json.dump(comments, commentFile)

    def countComments(self):
        count = 0
        for X in self.items():
            if type(X) is TextItem:
                count += 1
        return count

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

    # Mouse press tool functions
    def mousePressBox(self, event):
        """Creates a temp box which is updated as the mouse moves
        and replaced with a boxitem when the drawing is finished.
        If left-click then a highlight box will be drawn at finish,
        else an ellipse is drawn
        """
        self.originPos = event.scenePos()
        self.currentPos = self.originPos
        # If left-click then a highlight box, else an ellipse.
        # Set a flag to tell the mouseReleaseBox function which.
        if event.button() == Qt.LeftButton:
            self.ellipseFlag = 0
            # Create a temp box item for animating the drawing as the
            # user moves the mouse.
            # Do not push command onto undoStack until drawing finished.
            self.boxItem = QGraphicsRectItem(QRectF(self.originPos, self.currentPos))
            self.boxItem.setPen(self.ink)
            self.boxItem.setBrush(self.lightBrush)
            self.addItem(self.boxItem)
        else:
            self.ellipseFlag = 1
            self.ellipseItem = QGraphicsEllipseItem(
                QRectF(self.originPos.x(), self.originPos.y(), 0, 0)
            )
            self.ellipseItem.setPen(self.ink)
            self.ellipseItem.setBrush(self.lightBrush)
            self.addItem(self.ellipseItem)

    def mousePressComment(self, event):
        """Create a marked-comment-item from whatever is the currently
        selected comment. This creates a Delta-object and then also
        a text-object. They should be side-by-side with the delta
        appearing roughly at the mouse-click.
        """
        # Find the object under the mouseclick.
        under = self.itemAt(event.scenePos(), QTransform())
        # If it is a textitem and this is not the move-tool
        # then fire up the editor.
        if isinstance(under, TextItem) and self.mode != "move":
            under.setTextInteractionFlags(Qt.TextEditorInteraction)
            self.setFocusItem(under, Qt.MouseFocusReason)
            return

        # grab the location of the mouse-click
        pt = event.scenePos()
        # a small offset to place delta/text under mouse
        offset = QPointF(0, -24)
        # needs updating for differing font sizes
        # If the mark-delta of the comment is non-zero then
        # create a delta-object with a different offset.
        # else just place the comment.
        if self.commentDelta != 0:
            # push the delta onto the undo stack.
            command = CommandDelta(self, pt, self.commentDelta, self.fontSize)
            self.undoStack.push(command)
            # digits in the delta, and a (rough) corresponding offset.
            x = len(str(abs(int(self.commentDelta))))
            offset = QPointF(26 + 15 * x, -24)
            # the above needs updating for differing font sizes
        # position of text.
        self.originPos = event.scenePos() + offset
        # create the textitem, and push onto the undo stack
        self.blurb = TextItem(self, self.fontSize)
        self.blurb.setPos(self.originPos)
        self.blurb.setPlainText(self.commentText)
        # Put in a check to see if comment starts with TEX
        # If it does then tex-ify it.
        if self.commentText[:4].upper() == "TEX:":
            self.blurb.textToPng()

        command = CommandText(self, self.blurb, self.ink)
        self.undoStack.push(command)

    def mousePressCross(self, event):
        """Create a cross/?-mark/tick object under the mouse click
        if left/middle/right mouse button.
        """
        # Grab the mouseclick location and create command.
        pt = event.scenePos()
        if event.button() == Qt.RightButton:
            command = CommandTick(self, pt)
        elif event.button() == Qt.MiddleButton:
            command = CommandQMark(self, pt)
        else:
            command = CommandCross(self, pt)
        # push onto the stack.
        self.undoStack.push(command)

    def mousePressDelete(self, event):
        """Create a delete-command acting on the object
        under the mouse UNLESS it is the underlying group-image.
        """
        self.originPos = event.scenePos()
        # grab list of items in rectangle around click
        delItems = self.items(
            QRectF(self.originPos.x() - 5, self.originPos.y() - 5, 8, 8),
            mode=Qt.IntersectsItemShape,
            deviceTransform=QTransform(),
        )
        if delItems is None:
            return
        self.deleteItem = delItems[0]  # delete first item in list.
        if self.deleteItem == self.imageItem:
            self.deleteItem = None
            return
        command = CommandDelete(self, self.deleteItem)
        self.undoStack.push(command)

    def mousePressDelta(self, event):
        """Create the mark-delta object or ?-mark or cross/tick object
        under the mouse click if left/middle/right mouse button.
        If mark-delta is positive then right-mouse makes a cross.
        If mark-delta is negative then right-mouse makes a tick.
        """
        # Grab mouse click location and create command.
        pt = event.scenePos()
        if event.button() == Qt.LeftButton:
            command = CommandDelta(self, pt, self.markDelta, self.fontSize)
        elif event.button() == Qt.MiddleButton:
            command = CommandQMark(self, pt)
        else:
            if self.markDelta > 0:
                command = CommandCross(self, pt)
            else:
                command = CommandTick(self, pt)
        # push command onto undoStack.
        self.undoStack.push(command)

    def mousePressLine(self, event):
        """Creates a temp line which is updated as the mouse moves
        and replaced with a line or arrow when the drawing is finished.
        If left-click then a line will be drawn at finish,
        else an arrow is drawn at finish.
        """
        # Set arrow flag to tell mouseReleaseLine to draw line or arrow
        if event.button() == Qt.LeftButton:
            self.arrowFlag = 0
        else:
            self.arrowFlag = 1
        # Create a temp line which is updated as mouse moves.
        # Do not push command onto undoStack until drawing finished.
        self.originPos = event.scenePos()
        self.currentPos = self.originPos
        self.lineItem = QGraphicsLineItem(QLineF(self.originPos, self.currentPos))
        self.lineItem.setPen(self.ink)
        self.addItem(self.lineItem)

    def mousePressMove(self, event):
        """The mouse press while move-tool selected changes the cursor to
        a closed hand, but otherwise does not do much.
        The actual moving of objects is handled by themselves since they
        know how to handle the ItemPositionChange signal as a move-command.
        """
        self.parent().setCursor(Qt.ClosedHandCursor)
        super(PageScene, self).mousePressEvent(event)

    def mousePressPen(self, event):
        """Start drawing either a pen-path (left-click) or
        highlight path (right-click).
        Set the path-pen accordingly.
        """
        self.originPos = event.scenePos()
        self.currentPos = self.originPos
        # create the path.
        self.path = QPainterPath()
        self.path.moveTo(self.originPos)
        self.path.lineTo(self.currentPos)
        self.pathItem = QGraphicsPathItem(self.path)
        # If left-click then setPen to the standard thin-red
        # Else set to the highlighter.
        # set highlightflag so correct object created on mouse-release
        if event.button() == Qt.LeftButton:
            self.pathItem.setPen(self.ink)
            self.highlightFlag = 0
        else:
            self.pathItem.setPen(self.highlight)
            self.highlightFlag = 1
        # Note - command not pushed onto stack until path is finished on
        # mouse-release.
        self.addItem(self.pathItem)

    def mousePressText(self, event):
        """Create a textobject under the mouse click, unless there
        is already a textobject under the click.

        """
        # Find the object under the mouseclick.
        under = self.itemAt(event.scenePos(), QTransform())
        # If it is a textitem and this is not the move-tool
        # then fire up the editor.
        if isinstance(under, TextItem) and self.mode != "move":
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

        self.originPos = event.scenePos() + QPointF(0, -12)
        # also needs updating for differing font sizes
        self.blurb = TextItem(self, self.fontSize)
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
        if event.button() == Qt.RightButton:
            command = CommandCross(self, pt)
        elif event.button() == Qt.MiddleButton:
            command = CommandQMark(self, pt)
        else:
            command = CommandTick(self, pt)
        self.undoStack.push(command)

    def mousePressZoom(self, event):
        """Mouse-click changes the view-scale on the parent
        qgraphicsview. left zooms in, right zooms out.
        """
        if event.button() == Qt.RightButton:
            self.parent().scale(0.8, 0.8)
        else:
            self.parent().scale(1.25, 1.25)
        self.parent().centerOn(event.scenePos())
        self.parent().zoomNull()

    # Mouse move tool functions.
    # Not relevant for most tools
    def mouseMoveBox(self, event):
        """Update the box as the mouse is moved. This
        animates the drawing of the box for the user.
        """
        self.currentPos = event.scenePos()
        if self.ellipseFlag:
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
        else:
            if self.boxItem is None:
                self.boxItem = QGraphicsRectItem(
                    QRectF(self.originPos, self.currentPos)
                )
            else:
                self.boxItem.setRect(QRectF(self.originPos, self.currentPos))

    def mouseMoveLine(self, event):
        """Update the line as the mouse is moved. This
        animates the drawing of the line for the user.
        """
        self.currentPos = event.scenePos()
        self.lineItem.setLine(QLineF(self.originPos, self.currentPos))

    def mouseMovePen(self, event):
        """Update the pen-path as the mouse is moved. This
        animates the drawing for the user.
        """
        self.currentPos = event.scenePos()
        self.path.lineTo(self.currentPos)
        self.pathItem.setPath(self.path)

    # Mouse release tool functions.
    # Most of these delete the temp-object (eg box / line)
    # and replaces it with the (more) permanent graphics object.
    def mouseReleaseBox(self, event):
        """Remove the temp boxitem (which was needed for animation)
        and create a command for either a highlighted box or opaque box
        depending on whether or not the ellipseflag was set.
        Push the resulting command onto the undo stack
        """
        if self.ellipseFlag == 0:
            self.removeItem(self.boxItem)
            command = CommandBox(self, QRectF(self.originPos, self.currentPos))
        else:
            self.removeItem(self.ellipseItem)
            command = CommandEllipse(self, self.ellipseItem.rect())
        self.ellipseFlag = 0
        self.undoStack.push(command)

    def mouseReleaseLine(self, event):
        """Remove the temp lineitem (which was needed for animation)
        and create a command for either a line or an arrow
        depending on whether or not the arrow flag was set.
        Push the resulting command onto the undo stack
        """
        self.removeItem(self.lineItem)
        if self.arrowFlag == 0:
            command = CommandLine(self, self.originPos, self.currentPos)
        else:
            command = CommandArrow(self, self.originPos, self.currentPos)
        self.arrowFlag = 0
        self.undoStack.push(command)

    def mouseReleaseMove(self, event):
        """Sets the cursor back to an open hand."""
        self.parent().setCursor(Qt.OpenHandCursor)
        super(PageScene, self).mouseReleaseEvent(event)

    def mouseReleasePan(self, event):
        """Update the current stored view rectangle."""
        super(PageScene, self).mouseReleaseEvent(event)
        self.parent().zoomNull()

    def mouseReleasePen(self, event):
        """Remove the temp pen-path (which was needed for animation)
        and create a command for either the pen-path or highlight
        path depending on whether or not the highlight flag was set.
        Push the resulting command onto the undo stack
        """
        self.removeItem(self.pathItem)
        if self.highlightFlag == 0:
            command = CommandPen(self, self.path)
        else:
            command = CommandHighlight(self, self.path)
        self.highlightFlag = 0
        self.undoStack.push(command)

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
            self.commentDelta = 0
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
        self.parent().setFocus(Qt.TabFocusReason)

    def latexAFragment(self, txt):
        return self.parent().latexAFragment(txt)

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
