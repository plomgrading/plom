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
   toward supporting scripting for other use-cases such as
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

We will also need a running server with the properties listed below.

* We know the server credentials of an active user from the 'manager' group.
* The server contains an assessment specification that details the number of questions, the point value for each, etc.
* The server contains an assessment source PDF compatible with the specification just mentioned.
* The server has allocated enough test-papers to ensure the database has at least one paper per student. (Internally, the allocation corresponds to a Paper-Question-Version mapping, or `pqvmap`. On the web-based user interface, users can set this up on the page headed "Manage the number of papers and the paper-question-version database".)
* The server has built printable PDFs of the assessment source, one for each student.
* The server has been told that the individualized assessment PDFs have been printed.

Several of these items reflect Plom's genesis as a tool for
presenting test booklets printed on paper to students. In that context it
is impossible to scan and upload student work without creating and printing
the booklets the students will confront. And Plom's internal logic enforces
this expectation. So for homework, we must waste some server effort producing PDFs
that nobody ever needs to see, and we must tell a white lie to the server about
having printed them when we didn't.

Processing a single homework pdf
--------------------------------

To make a single homework PDF available for marking requires three actions:
upload, process, and push.

We will illustrate the process by tackling a specific situation,
as detailed below.

* New homework has arrived from Ken Kenson, student number 88776655.
* The incoming file has 5 pages and its name is ``"fake_hw_bundle_kk.pdf"``.
* The incoming page numbers and assignment question numbers are related as follows:

   - p1 = q1
   - p2 = q2
   - p3 = garbage (i.e., no questions)
   - p4 = q2 and q3
   - p5 = q3

* Paper number 61 is available on the server and not yet in use.
* User "demoManager1" (with password "1234") is active and in the "manager" group.

Plom is built to process PDF files made by scanning bundles of physical
paper. We treat each incoming HW file as an independent virtual bundle.
The following command will upload the new submission::

    $ plom-cli upload-bundle fake_hw_bundle_kk.pdf

The response to this command will reveal the `bundle_id` assigned to the
file we have uploaded. Assume we get `bundle_id = 1`. This number is needed below.

A complete list of bundles in the system can be requested::

    $ plom-cli list-bundles

This produces a table that tells us that bundle number 1 has
been uploaded, and that it contains 5 pages,
but that its qr-codes have not been read and it has not been pushed.
(This is good because the submission does not have qr-codes.)

To process this paper, we must inform the server of what pages to
associate with which question. Plom designers call this process
"mapping", and the command-line interface maps one page at a time.
So the mapping process for this 5-page PDF takes 5 commands.
Together these inform the server about the page-to-question
correspondence shown above::

    $ plom-cli map -t 61 -q '[1]'   1 1
    $ plom-cli map -t 61 -q '[2]'   1 2
    $ plom-cli map -t 61 -q '[]'    1 3
    $ plom-cli map -t 61 -q '[2,3]' 1 4
    $ plom-cli map -t 61 -q '[3]'   1 5

Here parameter `-t` gives the paper number and `-q` gives the list
of questions for the page of interest. The positional parameters
that follow give the incoming bundle's id number (here `1`)
and the page number in the bundle (which steps through all 5 choices).

The command-line responses to the mapping commands above are not
(yet) very informative.

Now that the system knows which pages contain which questions,
we can push the bundle to the marking team::

    $ plom-cli push-bundle 1

The markers can assess the paper without knowing who it came from.
After that, however, any marks earned will have to be attributed to the student.
The following command establishes the paper-to-student link in the system::

    $ plom-cli id-paper --sid 88776655 --name 'Kenson, Ken' 61

The student ID number and name string are clearly visible here;
note also the positional parameter `61` giving the paper number
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
    $ plom-http post /api/beta/paperpdfs
    $ plom-http post /api/beta/paperpdfs/setprinted

Here the number `256` should be replaced with a generous estimate of the number of submissions you expect. If your classlist is not too small,
you can omit the suffice `/256` and a reasonable default number of papers
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
