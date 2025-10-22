.. Plom documentation
   Copyright (C) 2020 Andrew Rechnitzer
   Copyright (C) 2020-2025 Colin B. Macdonald
   Copyright (C) 2023 Philip D. Loewen
   SPDX-License-Identifier: AGPL-3.0-or-later


Returning Work to Students
==========================

Once marking is done (or very nearly done) it is time to reassemble the
papers, build a spreadsheet and return results to students.

Plom doesn't interface directly with students; Plom is not an LMS!

You can use the "Reassemble" and "Spreadsheets and Reports" sections
of the Plom web interface to extract files and data from Plom to
return to students via other means.

Spreadsheet
-----------

While you can extract a `marks.csv` file at any stage in the marking
process,the sheet will not be complete until the marking is all done.
The file is human-readable and looks something like:

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
up and reviewing, it is time to reassemble all the annotated page-images
into papers complete with simple cover-pages.

You can look at individual PDF files within the web interface or you can
download all the reassembled papers as one large zip file.


Solutions
---------

You can also prepare individualized solutions: this is useful to
students when you had a multi-versioned assessment so that they do now
have search through multiple files to locate solutions to their
versions of the problems.


Return
------

There are various ways to return PDFs to your students.

Website return
~~~~~~~~~~~~~~

See ``plom-finish webpage --help`` which has various options to prepare a
webpage of non-predictable file names, and leaves you the problem of
returning a "secret code" (from ``return_codes.csv``) to each student.

Webpage return has not been used recently; it will probably move to
`contrib/` scripts or otherwise be deprecated.


Return via Canvas: instructor first steps
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Finish marking all papers.  Finish IDing all papers.  Reassembly all papers.
If using solutions and/or reports, generate those as well.

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

For the next steps you will also need some numbers corresponding to your
Canvas Course and Assignment, which can be extracted from the URL::

    https://canvas.example.com/courses/112233/assignments/1234123



Return via Canvas: scripting
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. tip::

    This feature is still being "beta" tested and is not yet
    integrated into Plom.  There is no UI; only a command-line
    script.  Perhaps someone will do this part for you.  If
    so, that person will need:

      * A manager-level account on your Plom server, and
        the address of your Plom server.
      * Your Canvas API key from above.
      * The Canvas Course and Assignment numbers,
        112233 and 1234123 above.
      * Whether you are returning solutions (and/or reports)
        in addition to the papers and grades.

Get the script called ``plom-push-to-canvas-uncached.py``.
You might find it in a directory like ``/home/<user>/.local/share/plom/contrib``
or you can get it from the Plom source code.
Copy it to a new empty working directory.
Make the script executable, e.g., `chmod a+x plom-push-to-canvas-uncached.py`.

Run ``./plom-push-to-canvas-uncached.py --help`` for instructions and interactivity.
Use the ``--dry-run`` mode first!
You almost certainly want ``--no-section`` unless you are doing something
very specialized (see ``--help`` for more info).
An example invocation looks something like::

    ./plom-push-to-canvas-uncached.py \
        --dry-run \
        --course 112233 \
        --assignment 1234123 \
        --no-section \
        --no-solutions \
        2>&1 | tee push.log

.. tip::

    If the script doesn't work, and complains about missing modules, try:
    ``pip install tqdm canvasapi exif`` and Plom itself
    via ``pip install --no-deps plom``
    (Plom itself has many dependencies which we don't need to run this
    simple script).
    You may even need
    ``pip install --no-deps --break-system-packages plom`` although you
    may want to understand what that does!



Return via Canvas: old script
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

An alternative to the above, you could use the older ``plom-push-to-canvas.py``.
In this case, you will need to manually download the ``marks.csv``
and reassembled` papers from your Plom server.
Place a copy of ``plom-push-to-canvas.py`` in the same directory
where you have the unzipped ``reassembled/`` subdirectory and ``marks.csv``.
Proceed similarly to the above.



Return via Canvas: instructor final steps
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Go back to Canvas and examine a few papers: double check the scores.
Double check some of the PDF files.  Unfortunately, you'll probably hit
`Canvas bug #1886 <https://github.com/instructure/canvas-lms/issues/1886>`_
(which effects instructors not students).  Workarounds are offered in the bug report.

Once happy, release the grades on Canvas.


Reassembly on legacy servers
----------------------------

* The command-line tool :doc:`plom-finish` is the front-end for
  working with legacy servers.

* For scripting or other advanced usage, you can ``import plom.finish``
  in your own Python code.  See :doc:`module-plom-finish`.
