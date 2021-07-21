<!--
__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-9 Andrew Rechnitzer"
__license__ = "GFDL"
 -->

# Marking papers
## The two windows
* The software for marking consists of two windows
  * Listing window
  * Annotation window

## Listing window
* A couple of moments after clicking "start" on the launch page, a window should pop up that looks like this:
![](figs/client2.png)
* In the top-left there is basic information about the user, the page-group, version and the maximum mark for that page-group.
* The list of papers shows the code of the page-groups you are marking (and have marked). You can click on one to select it.

* The next four buttons are perhaps the most important
  * *Get next* - requests another page-image from the server. As you annotate the software should automatically get the next image for you, but you can also click this.
  * *Revert* - takes a marked page-image and wipes it clean - reverting it to its unmarked state. Handy if you make a mistake.
  * *Defer* - this marks the entry to be deferred for you to look at later. Handy when you are not sure how to mark this paper and don't want the system to keep coming back to it.
  * *Annotate & mark* - this fires up the annotation window (more on this shortly).
* Marking styles - These change the behaviour of marking in the annotation window. I recommend using either *mark up* or *mark down*.
  * *Mark up* - the system assumes that the page-image starts with a mark of zero and then you can incrementally assign non-negative marks (0,+1,+2,+3,+4,+5) to the page. So, for example, if the page has two parts, each out of 3 and the student gets marks of 1 and 3 (respectively), then you can stamp "+1" next to the first, and "+3" to the second, and the system will total the marks for you.
  * *Mark down* - the system assumes that the page-image starts with the maximum possible mark and then you decrement marks (-1,-2,-3,-4,-5) as you find mistakes. So, for example, if the page has two parts, each out of 3 and the student gets marks of 1 and 3 (respectively), then you can stamp "-2" next to the first, and leave the second part alone (though maybe you'll put a tick there).
  * *Total* - you don't assign part-marks, instead you click on the total mark.

* In an attempt to make annotation as efficient as possible, I have tried to set things up so that you can keep one hand on the keyboard (to choose annotation tools), and one hand on the mouse.
  * The keyboard shortcuts mean that you can keep the mouse-pointer over the page-image as much as possible, and not have to move back and forth to the tools. This is supposed to make the annotation window closer to the experience of using a pen hovering over a page.
  * Of course, this requires you to become more fluent with the (one-handed) keyboard short-cuts, but we'll get to that when we get to the annotation window.
* The image of the current page-group is displayed on the right.
  * You can left-click to zoom in and right-click to zoom out.
  * The *reset view* button returns to the original (fit me to the window) view.
  * The *flip pages* button allows you to fix the orientation of the page images. The software does a pretty good job of ensuring that each page image is the right way up, but errors do happen. This button fires up a new window to allow you to flip pages 180-degrees. You shouldn't need this.

### Please close the window
* Again - we recommend that you close the window when you leave your computer for more than a few minutes. This makes that any unmarked papers you have locally are released back to the server, and so other people can mark them.
* The close button closes does this.
* When you fire up the launch window again it will remember the data you entered previously and you should only have to enter your password.

## Annotation window.
* Here is the right-hand mouse version with *mark down* selected:
![](figs/client3r.png)
* And here is the left-hand mouse version with *mark up* selected:
![](figs/client3l.png)
* In both cases there is 5x3 bank of tool buttons (more on those in a moment), some marking buttons, a bank of standard comments and "finished" and "cancel" buttons.
* *End & next* accepts your annotations and marks and automatically loads the next paper and fires up the annotation window.
* *End & return* accepts your annotations and marks but bounces you back to the paper-listing window. That window should automatically load a new page-image for you. You can then just type "enter" again to fire up the annotation window.
* *Cancel* bounces you back to the paper-listing window without recording either your annotations or marks.
* Note that the "+" and "\" keys will maximise (un-maximise) the annotation window.

### Tools
* You can get a listing of all the key-codes by typing a question-mark.
* In both layouts the tools are arranged so that the most common tools (based on my experience) are arranged in the middle row. The keyboard shortcuts correspond to the keys along the "home-row" of a qwerty keyboard.
  * In the right-hand mouse version A, S, D, F and G  correspond to zoom, undo, tick, comment and text (respectively).
  * In the left-hand mouse version h,j,k,l and semi-colon correspond to text, comment, tick, undo and zoom (respectively).
  * The top row of tools correspond to the keys above the home-row. ie, qwert and yuiop.
  * The bottom row of tools correspond to the keys below the home-row. ie, zxcvb and n m comma period slash.

* The tools are (I hope) pretty obvious, but with a few idiosyncrasies

  * *Pan* - clicking and dragging moves the page image.

  * *Zoom* - left-click to zoom in and right-click to zoom out.

  * *Move* - allows you to move your annotations around

  * *Undo / redo* - the annotation window has a full (or very full) undo/redo stack

  * *Delete* - delete the annotation you click on

  * *Cross / Tick (Question mark)* - places a cross or tick on the page. Notice that if you have the tick tool selected, then the left mouse-button will create a tick, while the right mouse-button will create a cross. If you have the cross tool the reverse happens. In both cases the middle button pastes a question-mark.
corded
  * *Box (Ellipse)* - click and drag with the left mouse-button will create a high-light box. Click and drag with the right mouse-button will create an ellipse centred at your initial click.

  * *Pen* - dragging with left mouse-button creates a free-hand red path, while the right mouse-button creates a thick yellow highlight-path.

  * *Line* - dragging with left mouse-button creates a straight-line, while the right mouse-button creates a similar arrow.

  * *Comments* - Lets come back to these shortly once we have covered "assigning marks"

  * *Text* - a simple text tool. To exit the text tool you press escape or shift-return. Double-clicking will start a new text object under your click. You can also go back an edit previous text by clicking on it.
    * Basic LaTeX is supported. Press control-enter to end the comment (command-enter on a mac), and the text will be replaced by its latex'd equivalent. You can go back and edit it by simply clicking again with the text-tool
    * Coming-soon, latex will also be supported by starting your comment with the 3 letters "TEX". When you end the comment (with shift-enter) then it will be automatically latex'd.


### Assigning marks
![](figs/client3r1.png?)
* Perhaps the easiest way to assign marks is to use either the *mark up* or *mark down* methods.
* In mark-up you can assign 0,+1,+2,+3,+4 or +5 marks. Clicking on the appropriate button or pressing 0,1,2,3,4 or 5 (and also the single-quote key to get 0), and then left-clicking on the page will stamp that onto the page (with a little box around it).
* In mark-down you assign -1,-2,-3,-4 or -5 marks. Again the button or pressing 1,2,3,4 or 5 and then left-clicking on the page stamps the page.
* To all the left-handers out there - sorry I am not sure which keys I should assign these to. I am very happy to get feedback and I'll get it into the system.
* In both cases the mark (stamped in the top-left of the page) is updated. These also work correctly with the undo/redo and delete tools.
* In mark-total, the user simply clicks the appropriate button for the total-mark and the mark is updated accordingly.


### Comments
* The comment system is driven by the box of comments in the lower-left (if right-handed mouse selected) of the annotation window.
![](figs/client_comment1.png)
* These comments combine both the delta-mark tool and the text tool. When a comment is selected then a left-click will paste both the delta-mark and the text into the window. After that the pasted comment can be treated like any other text object and the text tool will let you edit it.

* The comments should give you a very fast way of leaving consistent feedback. The markers of a particular question should decided on text + deltas to match the given question marking-scheme.

* The system saves your comments between sessions (in a json file). Giving a copy of this file to another marker means that their system will start with those same comments.

* You can reorder the comments by click-dragging up and down the list. Move your most common comments to the top of the list.

* You can create and delete comments by using the obvious buttons.

* You can also edit the comments by double clicking on the text (or delta).

* Notice that there are 3 comment tool buttons ("r","f","v" keys for right-hand-mouse). "COM UP" moves up one comment, and "COM DOWN" moves down one comment. "COM" reselects the current comment, but pressing it again will move down one comment - handy for moving around the comments.

### Done marking
* If you don't like you annotations or mark, then you can click the cancel button and the system will return you to the paper-listing window.

* More generally, once you are finished marking you can type alt-enter, or control-n or control-b, or click "End & Next" and the system will accept your work and automatically fire up the next paper.

* Clicking "End & return" accepts your work, but does not fire up next paper.

* The system does have some sanity checks (nags) built in:
  * If you are marking-up and have assigned a mark of zero then the system will ask you to confirm.
  * If you are marking-down and have assigned full marks, then the system will also ask you to confirm.
  * If you have left no text on the page, but have not given either zero or full marks, then the system will ask you to confirm. We want you to leave feedback!
