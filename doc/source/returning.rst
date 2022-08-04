.. Plom documentation
   Copyright 2022 Colin B. Macdonald
   SPDX-License-Identifier: AGPL-3.0-or-later


Returning Work to Students
==========================

.. note::

   Stub: move and/or write documentation.



Return to the Canvas LMS
------------------------

Follow instructions above to "reassemble" the papers, make the `marks.csv`
and optionally the individualized solutions.

Make an "API key" for your Canvas account.

- Login to Canvas and click on "Account" (your picture in the top-left).
- Settings
- Click on ``+ New Access Token``.  The purpose can be "Plom upload" (or
  whatever you want) and you can set it to expire in a day or two.
- Copy the token, something like ``11224~AABBCCDDEEFF``, keep it for later
  steps.

Also in Canvas, create column "Midterm 1" (or whatever) in Canvas with the
correct number of points.

Publish the columm but set to manual release.

Get the "contrib script" called `plom-push-to-canvas.py`.  You might find it
in a directory like `/home/<user>/.local/share/plom/contrib`.  You could also
get a copy from the Plom source code.

Instructions are given at the top of script: basically you need to put the
Canvas API key into a particular file.  Instructions are also given for running
it.  Try ``./plom-push-to-canvas.py --help`` for more info.  Use the
``--dry-run`` mode first!

Go back to Canvas and examine a few papers: double check the scores.
Double check some of the PDF files.  Unfortunately, you'll probably hit
`this Canvas bug <https://github.com/instructure/canvas-lms/issues/1886>`_
(which effects instructors not students).  Workarounds are offered in the bug report.

Once happy, release the grades on Canvas.


Technical docs
--------------

* The command-line tool :doc:`plom-finish` is the current front-end
  for most tasks related to returning work.

* For scripting or other advanced usage, you can ``import plom.finish``
  in your own Python code.  See :doc:`module-plom-finish`.
