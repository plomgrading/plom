.. Plom documentation
   Copyright (C) 2022-2025 Colin B. Macdonald
   Copyright (C) 2018 Andrew Rechnitzer
   SPDX-License-Identifier: AGPL-3.0-or-later


Preparing an assessment
=======================


Designing your assessment
-------------------------


What software should I use?
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Its up to you.  Plom will need a PDF file of your assessment (PDF files if
you are using multiple versions).  Plom came out of the mathematics
community where LaTeX is commonly used, and we provide a template below.
But you can use any software you like.



What should each "question" be?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. tip::
   Plom defines a question as the smallest unit of independently
   markable material.

So if 5(a) and 5(b) can be marked by TAs Jane and Austin
*simultaneously* and *independently*, then those can be separate
questions.
You can use the ``label`` field in the specification (see :ref:`Creating a spec`) to
*display* the two questions as "5(a)" and "5(b)".

If you enable shared pages (see below), there can be more than one
question on a page; any shared pages will
be duplicated during marking (that is, each marker will get their own
copy for annotating).
Any questions sharing a page will be drawn from the same version.

Questions can also span multiple pages, even in a multi-versioned
assessment.


Be careful with your margins
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Plom needs space on the corners of every page to stamp QR-codes and a
gap in the middle of the page for general information.
One way to check your margins is to upload your PDF file(s) to Plom,
and use the "Mock" feature to quickly mock-up how your paper will look
with QR codes.


A template assessment
^^^^^^^^^^^^^^^^^^^^^

.. note::
   The example exam
   (`PDF file <https://plomgrading.org/images/demoTest/latexTemplate.pdf>`_)
   consists of 6 pages and 3 questions:

   .. image:: https://plomgrading.org/images/demoTest/lt1-0.png
     :width: 104
     :alt: example page 1
   .. image:: https://plomgrading.org/images/demoTest/lt1-1.png
     :width: 104
     :alt: example page 2
   .. image:: https://plomgrading.org/images/demoTest/lt1-2.png
     :width: 104
     :alt: example page 3
   .. image:: https://plomgrading.org/images/demoTest/lt1-3.png
     :width: 104
     :alt: example page 4
   .. image:: https://plomgrading.org/images/demoTest/lt1-4.png
     :width: 104
     :alt: example page 5
   .. image:: https://plomgrading.org/images/demoTest/lt1-5.png
     :width: 104
     :alt: example page 6

   * page 1 is an "ID-page" on which students write their name and ID-number.
   * page 2 consists of further instructions to students and also a formula sheet;
     students should not write anything on this page.
   * page 3 is question 1 worth 5 marks,
   * page 4 is question 2 worth 5 marks, and
   * pages 5-6 are question 3 worth 10 marks.

You can download the `LaTeX source version 1 <https://gitlab.com/plom/plom/-/blob/main/testTemplates/latexTemplate.tex>`_.
The second version of the same exam has **exactly** the same structure, just different question text:
`PDF version 2 <https://plomgrading.org/images/demoTest/latexTemplatev2.pdf>`_,
`source version 2 <https://gitlab.com/plom/plom/-/blob/main/testTemplates/latexTemplatev2.tex>`_.
To compile these files you will also need the
`ID Box image <https://gitlab.com/plom/plom/-/blob/main/testTemplates/idBox4.pdf>`_.



.. _Creating a spec:

Creating a "spec file"
----------------------

The specification is stored as a TOML file, and describes the
structure of your assessment (which questions on are on which pages;
how many marks is each question worth, etc).  You can use the Plom
interface to help you create a specification, by answering a few
questions, or you can prepare one in a file on your own computer.

The ``spec.toml`` for the template assessment above looks like::

    name = "plomdemo"
    longName = "Midterm Demo using Plom"

    numberOfVersions = 2
    numberOfPages = 6
    totalMarks = 20
    numberOfQuestions = 3
    idPage = 1
    doNotMarkPages = [2]

    [[question]]
    pages = [3]
    mark = 5

    [[question]]
    pages = [4]
    mark = 3

    [[question]]
    pages = [5, 6]
    mark = 10


There are other fields which can be added to this file, for example,
each question can have ``label = ...`` to specify something other than
the "Qn" default.
The file can also contain comments starting with ``# ...``

.. tip::
   Shared pages are a new experimental feature: you can enable them by
   explicitly putting ``allowSharedPages = true`` in your specification.


Building the database of papers
-------------------------------

After creating and uploading your assessment specification, you can
use the management web interface to upload "source PDFs" of your
assessment, optionally upload a classlist, build a database of papers
and create the actual QR-coded PDF files to print for you assessment.


The question-version mapping
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. tip::
   The first time you use Plom, we recommend using just a single
   version of your assessment (and skipping this section!)

When creating a multi-versioned assessment, a critically-important
step is the creation of the "QV map" or the "question-version
mapping", which tells Plom what versions to expect for each question
and for each paper.

You can have Plom create this mapping automatically, or specify your
own via a spreadsheet if you have additional requirements.

.. caution::
   Its a good idea to download and backup a copy of your QV-map.  If
   something goes catastrophically wrong, it (and the specification)
   are crucial components to recreate your assessment elsewhere.


I want to use different versions of my ID page
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For example, maybe you want to use versions 1 and 2 for section 101
and version 3 for section 102.
In this case you might want to write "Section 101" on the front (ID)
page of some papers and "Section 102" on others.
This can be done by adding a ``id.version`` column to your custom "QV
map" ``.csv`` file.

.. danger::
   Versioned ID-pages is a new feature, without much (any?) real-world
   testing.  Use at your own risk.  If you've tested it, please get in
   touch so we can remove this message following your act of bravery.

.. tip::
   The "IDBox" template must be in the exact same location on
   different versions of your ID page.
   If this is not so, the auto-ID reader may fail.



Technical docs
--------------

* For scripting, the command-line tools `django-admin plom_preparation_test_spec`,
  `django-admin plom_qvmap`, `django-admin plom_build_paper_pdfs`, and others
  can used.

  ..
     TODO: ideally we'd get these argparse'd into the docs like the legacy tools.

* On legacy servers, the command-line tool :doc:`plom-create` is used for
  most tasks related starting a new assessment.

* For scripting or other advanced usage, you can ``import plom.create``
  in your own Python code.  See :doc:`module-plom-create`.
