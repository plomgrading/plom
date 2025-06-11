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

Let us make a few assumptions about students' homework submissions:

* a homework submission arrives as a single PDF (though perhaps this can be
  loosened later) containing at least 1 page;
* we know the name and student ID of the person who submitted each HW pdf;
* we know an unused paper-number to which we can assign this homework (again, this can potentially be loosened later); and
* we know (or can reasonably guess) which questions appear on which pages of a given HW pdf - i.e., a question-mapping.

We will also need a running server with the following properties:

* users  from groups 'manager' and 'scanner' exist, and their passwords are known;
* the server contains a test-specification that details the number of questions, the point value for each, etc.; and
* the server has allocated enough test-papers to ensure the database has at least one paper per student. (Internally, the allocation corresponds to a Paper-Question-Version mapping, or `pqvmap`. On the web-based user interface, users can set this up on the page headed "Manage the number of papers and the paper-question-version database. The corresponding printable PDFs do not actually need to be built or printed.) (Again - this can perhaps be loosened in the future)

Processing a single homework pdf
--------------------------------

To make a single homework PDF available for marking requires three actions:
upload, process, and push.

To illustrate with specifics,

* we will assign this PDF the (unused) paper number 61;
* the file name is ``"fake_hw_bundle_61.pdf"``; it has 5 pages;
* the correspondence between page numbers and question numbers is as follows:

   - p1 = q1
   - p2 = q2
   - p3 = garbage (i.e., no questions)
   - p4 = q2 and q3
   - p5 = q3

* The homework was submitted by student with id "88776655" and name "Kenson, Ken".
* We will upload the homework as user "demoScanner1"
* We will process the homework as user "demoManager1"

Plom is built to process PDF files made by scanning bundles of physical
paper. We will treat the single HW file as a virtual bundle. The following
command will upload it::

    $ python manage.py plom_staging_bundles upload demoScanner1 fake_hw_bundle_61.pdf
    Uploaded fake_hw_bundle_61.pdf as user demoScanner1 - processing it in the background now.

We can confirm the results by giving this command::

    $ python manage.py plom_staging_bundles status

The response is a table that tells us that the bundle has
been uploaded, and contains 5 pages, but its qr-codes
have not been read and it has not been pushed.
(This is good because Ken Kenson's submission does not have qr-codes.)

To process this paper, we must turn the page-to-question
correspondence shown above into a list of lists. Each entry
in the main list corresponds to a page number.
The sub-list for a given page number enumerates all the questions
answered on that page. The result is ``[ [1], [2], [], [2, 3], [3] ]``,
and it is a key parameter in the next command::

    $ python manage.py plom_paper_scan list_bundles map fake_hw_bundle_61 -t 61 -q [[1],[2],[],[2,3],[3]]

The server then returns something like::

    CAUTION: paper_scan is an experimental tool
    DEBUG: numpages in bundle: 5
    DEBUG: pre-canonical question:  [[1],[2],[],[2,3],[3]]
    DEBUG: canonical question list: [[1], [2], [], [2, 3], [3]]

Now that the system knows which pages contain which questions, we can "push" the bundle to the marking team::

    $ python manage.py plom_staging_bundles push fake_hw_bundle_61 demoScanner1
    Bundle fake_hw_bundle_61 - pushed from staging.

At this point the homework is in the system and marking can begin.
The server knows which pages contain which questions etc.
However the system does not yet know which student to associate with the paper.
Accordingly we now ID the paper using ``plom_id_direct``::

    python manage.py plom_id_direct demoManager1 61 88776655 "Kenson, Ken"

Now the system knows that Ken Kenson should get the credit for points earned on this HW.


Summary of the process
----------------------

Set up a server. For each homework submission, give appropriate versions of
the commands that follow:

* ``python manage.py plom_staging_bundles upload <scannerName> <hwpdf>``

   - This does asynchronous processing in parallel---so we must wait until it is done.
     The remaining steps are synchronous.
* ``python manage.py plom_paper_scan list_bundles map <hwpdf> -t <papernumber> -q <question_map>``
* ``python manage.py plom_staging_bundles push <hwpdf> <scannerName>``
* ``python manage.py plom_id_direct <managerName> <paper_number> <student_id> <student_name>``


Processing homework with the legacy Plom server
-----------------------------------------------

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
