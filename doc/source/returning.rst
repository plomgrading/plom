.. Plom documentation
   Copyright (C) 2020 Andrew Rechnitzer
   Copyright (C) 2020-2024 Colin B. Macdonald
   Copyright (C) 2023 Philip D. Loewen
   SPDX-License-Identifier: AGPL-3.0-or-later


Returning Work to Students
==========================

Once marking is done (or very nearly done) it is time to reassemble the
papers, build a spreadsheet and return results to students.

.. note::

   Much of this information refers to "Legacy Servers" and needs updating.


Is everything done?
-------------------

..
    TODO: One way to access this information is through the :doc:`plom-legacy-manager`.

Once we are mopping up the last few questions, and it becomes important
to know what tasks are left to do.
You can get a quick overview on the command line::



    $ plom-finish status
    Please enter the 'manager' password:
    *********************
    ** Completion data **
    Produced papers: 20
    Scanned papers: 20 (currently)
    Completed papers: 1–20
    Identified papers: 1–20
    Totalled papers: 1–20
    Number of papers with 0 questions marked = 0. Tests numbers =
    Number of papers with 1 questions marked = 0. Tests numbers =
    Number of papers with 2 questions marked = 0. Tests numbers =
    Number of papers with 3 questions marked = 20. Tests numbers = 1–20
    20 of 20 complete

This shows that everything is actually done.


Spreadsheet
-----------

Plom can build a
`CSV spreadsheet <https://en.wikipedia.org/wiki/Comma-separated_values>`_
for us::

    $ plom-finish csv
    Please enter the 'manager' password:
    >>> Warning <<<
    This script currently outputs all scanned papers whether or not they have been marked completely.
    Marks written to "marks.csv"

Please do note the warning --- Plom will include all scanned papers in this sheet.
While you can run this at any stage in the marking process, the sheet
will not be complete until the marking is all done.

The sheet is saved as `marks.csv` and is human-readable:

=========  ===========  ==========  =======  =======  =====  ==========  ==========  ========
StudentID  StudentName  TestNumber  Q1 mark  Q2 mark  Total  Q1 version  Q2 version  Warnings
=========  ===========  ==========  =======  =======  =====  ==========  ==========  ========
67719396   Dix, Rachel    1           1        4       5         1           1
82911040   Hain, Norm     2           9        5       14        1           2
=========  ===========  ==========  =======  =======  =====  ==========  ==========  ========

It contains the students ID and name, the number of the test-paper they
wrote, their marks for each question, and the total.
It also includes the versions of each question and a "Warnings" column:

  * ``[unidentified]``: this test has not yet been identified
  * ``[unmarked]``: at least one question on this test is unmarked
  * ``[no ID]``: no ID given on test, but some questions were answered
  * ``[blank ID]``: no ID was given was given and test is blank

It should not be too difficult to tweak `marks.csv` for upload into your
favourite LMS (or at least the one you have to use).
See `Return via Canvas`_ for an automated approach.


Reassembly
----------

Once everything is IDd and marked and you've done any necessary mopping
up and reviewing it is time to reassemble all the annotated page-images
into papers complete with simple cover-pages::

    $ plom-finish reassemble
    Please enter the "manager" password:
    Reassembling 20 papers...
    100%|--------------------| 20/20 [00:04<00:00,  4.16it/s]

Note that for a long paper and a large class this could take some time.
The resulting papers now reside in ``reassembled/``.
Each is named `<testName>_<studentID>.pdf` where the `<testName>` is the
short name of the assessment.

..
    TODO: link shortname to something about the spec

You can also prepare individual solutions: see ``plom-finish solutions --help``.


Return
------

There are various ways to return PDFs to your students.

Website return
~~~~~~~~~~~~~~

See ``plom-finish webpage --help`` which has various options to prepare a
webpage of non-predictable file names, and leaves you the problem of
returning a "secret code" (from ``return_codes.csv``) to each student.


Return via Canvas
~~~~~~~~~~~~~~~~~

.. caution::

    This feature is still being "beta" tested and is not yet
    integrated into Plom.  Proceed with caution.

Get the script called ``plom-push-to-canvas.py``.
You might find it in a directory like ``/home/<user>/.local/share/plom/contrib``
or you can get it from the Plom source code.
Copy it to your working directory (where the ``reassembled/`` directory and
``marks.csv`` are).
Make the script executable, e.g., `chmod a+x plom-push-to-canvas.py`.

Make an "API key" for your Canvas account:

  - Login to Canvas and click on "Account" (your picture in the top-left)
    then "Settings".
  - Click on ``+ New Access Token``.  The "purpose" can be "Plom upload" (or
    whatever you want) and you can set it to expire in a day or two.
  - Copy the token, something like ``11224~AABBCCDDEEFF...``.
  - Who can do this?  The instructor can.  So can TAs, but be cautious:
    Canvas has three kinds of TAs: `TA`, `TA Grader`, and `TA Course Builder`,
    and at least before 2022-11-08 at UBC, it would fail for TA Graders,
    `Issue #2338 <https://gitlab.com/plom/plom/-/issues/2338>`_.

Also in Canvas, create an Assignment "Midterm 1" (or whatever) in Canvas with the
correct number of points.  **Publish the Assignment** but set to manual release.

Run ``./plom-push-to-canvas.py --help`` for instructions.
Use the ``--dry-run`` mode first!
You almost certainly want ``--no-section`` unless you are doing something
very specialized (see ``--help`` for more info).
An example invocation looks something like::

    ./plom-push-to-canvas.py \
        --dry-run \
        --course 112233 \
        --assignment 1234123 \
        --no-section \
        --no-solutions \
        2>&1 | tee push.log

Go back to Canvas and examine a few papers: double check the scores.
Double check some of the PDF files.  Unfortunately, you'll probably hit
`Canvas bug #1886 <https://github.com/instructure/canvas-lms/issues/1886>`_
(which effects instructors not students).  Workarounds are offered in the bug report.

Once happy, release the grades on Canvas.


Technical docs
--------------

* The command-line tool :doc:`plom-finish` is the current front-end
  for most tasks related to returning work.

* For scripting or other advanced usage, you can ``import plom.finish``
  in your own Python code.  See :doc:`module-plom-finish`.
