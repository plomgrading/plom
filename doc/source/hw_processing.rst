.. Plom documentation
   Copyright (C) 2023 Andrew Rechnitzer
   Copyright (C) 2023 Colin B. Macdonald
   Copyright (C) 2025 Philip D. Loewen
   SPDX-License-Identifier: AGPL-3.0-or-later

Processing homework
===================

This document outlines how we might use Plom to mark free-form homework.
The main issue here is that such homework (say uploaded by
students to an LMS like Canvas) is **not structured.** A typical
homework submission will not contain an ID-page, nor will it have questions
neatly arranged so that we know (with certainty) what precisely is on
page 7 of the submitted PDF.

.. caution::

   This feature is under active development.  Plom's primary purpose
   is to manage QR-coded hardcopy assessments; we are working
   toward supporting scripting for secondary use-cases such as
   homework.

.. note::

   For the legacy server, the process is similar and described
   later in this document.


Assumptions
-----------

We make the following assumptions about students' homework submissions.
(Various relaxations are possible; some of these are work in progress.)

* Each homework submission arrives as a single PDF containing at least 1 page.
* We know the name and student ID of the person who should get credit for each HW pdf.
* We know an unused paper-number to which we can assign this work.
* We know (or can reasonably guess) which questions appear on which pages of a given HW pdf -- i.e., a question-mapping.

We will also need a running server with the following properties.
(Notes on setting this up are provided below.)

* The server has an active user from the 'manager' group, whose credentials we know.
* The server contains an assessment specification that details the number of questions, the point value for each, etc.
* The server contains an assessment source PDF compatible with the specification just mentioned.
* The server has allocated enough test-papers to ensure the database has at least one paper per student. (Internally, the allocation corresponds to a Paper-Question-Version mapping, or `pqvmap`. On the web-based user interface, users can set this up on the page headed "Manage the number of papers and the paper-question-version database".)
* The server has built printable PDFs of the assessment source, one for each student.
* The server has been told that the individualized assessment PDFs have been printed.

Several of these items reflect Plom's genesis as a tool for
presenting test booklets printed on paper to students. In that context it
is impossible to scan and upload student work without creating and printing
the booklets the students will confront. Plom's internal logic enforces
this expectation. So for homework, we must waste some server effort producing PDFs
that no human ever needs to see, and we must tell a white lie to the server about
having printed them when we didn't.

Processing a single homework pdf
--------------------------------

To make a single homework PDF available for marking requires three actions:
upload, map, and push.

We will illustrate the process by tackling the following scenario.

* New homework has arrived from Ken Kenson, student number 88776655.
* The incoming file has 5 pages and its name is ``"fake_hw_bundle_kk.pdf"``.
* The incoming page numbers and assignment question numbers are related as follows:

   - page 1 addresses question 1
   - page 2 addresses question 2
   - page 3 is irrelevant (i.e., addresses no questions)
   - page 4 addresses question 2 and question 3
   - page 5 addresses question 3

* Paper number 61 is available on the server and not yet in use.
* User "demoManager1" (with password "1234") is active and in the "manager" group.

The work proceeds using various applications of the `plom-cli` command.
Each of these requires authentication. Credentials can be given on each
and every command line, or by setting so-called Environment Variables in
the terminal session. On Linux, the following commands achieve this::

    $ export PLOM_USERNAME=demoManager1
    $ export PLOM_PASSWORD=1234

The commands below assume that this has been done; the alternative would be to
append the string ``-u demoManager1 -w 1234`` to each and every ``plom-cli`` command.

Plom is built to process PDF files made by scanning bundles of physical
paper. We treat each incoming HW file as an independent virtual bundle.
The following command will upload our latest submission::

    $ plom-cli upload-bundle fake_hw_bundle_kk.pdf

The response to this command will reveal the ``bundle_id`` assigned to the
file we have uploaded. Assume we get ``bundle_id = 8``. This number is needed below.

A complete list of bundles in the system can be requested::

    $ plom-cli list-bundles

This produces a table of information about all the bundles the server
has ever seen. It tells us that bundle number 8 contains 5 pages,
that the server has tried to read its qr-codes and failed every time,
so that all 5 pages are considered "unknown". All unknown pages must
be recategorized before further progress is possible.

With no help from QR-codes or standard structure,
the job of telling the server of what pages to
associate with which question lands on us.
Plom designers call this process "mapping",
and the command-line interface maps one page at a time.
So the mapping process for this 5-page PDF takes 5 commands.
To inform the server about the page-to-question
correspondence detailed above, we proceed as follows::

    $ plom-cli map 8 1 -t 61 -q [1]
    $ plom-cli map 8 2 -t 61 -q [2]
    $ plom-cli map 8 3 -t 61 -q []
    $ plom-cli map 8 4 -t 61 -q [2,3]
    $ plom-cli map 8 5 -t 61 -q [3]

Here the first parameter gives the bundle id number (here 8)
and the second gives the page number in the bundle.
Then the parameter ``-t`` gives the target paper number and 
``-q`` introduces the list of questions mentioned on the page of interest. 

The command-line responses to the mapping commands above are not
(yet) very informative. However, the command `plom-cli list-bundles`
now shows 0 unknown pages, 4 extra pages, and 1 discard. With no
pages in the unknown category, the next step is at hand.
(Sticklers for logic will notice that the page counts in
the categories "known" and "unknown" add up to 0.
Never forget that this is free software.)

There is work in progress to allow single-question lists like [3]
to be presented as a bare integer question number, like 3. Other
possibilities coming soon are to allow ``-q dnm`` (for Do Not Mark)
and ``-q all`` (which would expand to [1,2,3] here).

Now that the system knows which pages contain which questions,
we can push the bundle to the marking team::

    $ plom-cli push-bundle 8

The markers can assess the paper without knowing who it came from.
After that, however, any marks earned will have to be attributed to the student.
The following command establishes the paper-to-student link in the system::

    $ plom-cli id-paper 61 --sid 88776655 --name 'Kenson, Ken'

The student ID number and name string are clearly visible here
after the positional parameter 61 giving the paper number
used throughout for this student's submission. (Different submissions
must be given different numbers.)


Summary
-------

Set up a server, containing a spec, a sample source, a PQV map,
and a generous supply of blank PDFs; set the server's flag for
'papers have been printed' to True.

For each homework submission, give appropriate versions of
the commands that follow:

* ``plom-cli upload-bundle  <hwpdf>``

   - This does asynchronous processing in parallel---so we must wait until it is done.
     The remaining steps are synchronous.

* ``plom-cli list_bundles``
* ``plom-cli map -t <paper_number> -q <question_list> <bundle_id> <bundle_page>``
* ``plom-cli push-bundle <bundle_id>``
* ``plom-cli id-paper --sid <studentid> --name <studentname> <paper_number>``



Prerequisites
-------------

To put a fresh server with an active 'manager' user into the state assumed above,
follow these steps::

    $ plom-cli upload-spec myspec.toml
    $ plom-cli upload-source fakehw.pdf
    $ plom-cli upload-classlist mystudents.csv
    $ plom-http post /api/beta/pqvmap/256
    $ plom-http post /api/beta/paperstoprint
    $ plom-http post /api/beta/paperstoprint/setprinted

The last three lines here give a glimpse behind the scenes. The ``plom-http`` function
is not available for public use yet. For now, users should use the Web interface to
complete the three tasks shown here.

Here the number ``256`` should be replaced with a generous estimate of the number of submissions you expect. If your classlist is not too small,
you can omit the suffice ``/256`` and a reasonable default number of papers
will be produced.



Notes on the legacy Plom server
-------------------------------

A script can be used, roughly:

* prename a paper to an available paper number.  A script to do this is
  ``contrib/plom-preid.py``.
  This will associate a particular Student ID to a paper number
* Use ``plom-hwscan`` to upload a PDF file to that student number.
* Optionally, use ``msgr.id_paper`` to "finalize" the identity of that paper.
  Alternatively, you can do this manually in the Plom Client identifier app.

An work-in-progress script that does these steps while pulling from
Canvas is ``contrib/plom-server-from-canvas.py``.

.. caution::

   Do not use prenaming to attach the same student number to more than one paper.
   This is not logical, and the results are not well-defined.

.. note::

   Do not use ``id_paper`` to identify the paper before you upload it.  This
   will create a situation where the paper is not seen as scanned.  We're unlikely
   to fix this, instead focusing on workflows for the nextgen server instead.
