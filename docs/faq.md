Frequently Asked Questions
==========================

Common questions and tips 'n tricks that may not appear elsewhere in the
documentaiton.


Plom Client software
--------------------

### Some windows/dialogs are awkward to resize on Gnome Desktop

You could try disabling "Attach Modal Dialogs" in the "Gnome Tweaks" app.


### I don't like ____ about the UI, why don't you do ____?

We are not experts at UI design: please do send patches or merge requests
to help improve Plom.


Identifying
-----------

### How does the auto-identifier work?

Machine learning trained on the MNIST handwritten digit dataset.  A linear
assignment problem solver then matches the results against the class list.
For this reason the class list csv file should not contain large numbers
of additional students that are not in your class.


Test Preparation
----------------

### My QR codes are badly misplaced

This might be a bad interaction with `\scalebox` in LaTeX.  See
[this bug](https://gitlab.math.ubc.ca/andrewr/MLP/issues/207).
