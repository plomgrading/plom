.. Plom documentation
   Copyright (C) 2022-2025 Colin B. Macdonald
   Copyright (C) 2018 Andrew Rechnitzer
   SPDX-License-Identifier: AGPL-3.0-or-later


Multi-version assessments
=========================

Plom is designed for giving multi-version assessments suitable for
crowded classrooms and multiple sittings.

You provide several versions of your assessment, and Plom interleaves
questions from each version to create a large number distinct
assessments.

Plom produces a different PDF file for each student by
"slicing-and-dicing" your input "sources".


Restrictions
------------

For this interleaving to be possible, and for scoring to be practical,
different versions of a question must take the occupy the same page(s)
and must be worth the same number of points.

Loosening these restrictions is probably possible in theory, but none
of the built-in tooling will help you do this.

Any questions that share a page must be the same version (this will
happen automatically if you let Plom create the version mapping).


The question-version mapping
----------------------------

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



Multiversioning FAQs
--------------------

I want to use different versions of my ID page
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For example, maybe you want to interleave versions 1 and 2 for section
101 and version 3 for section 102.
In this case you might want to write "Section 101" on the front (ID)
page of papers numbered 1-199 and "Section 102" on papers 200-350.
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


Can I create my own per-student PDFs and use multiversioning?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Yes.  You need only provide Plom with your chosen question-version
map.


In that case, could different versions of Q1 and Q2 share a page?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Yes, provided you make the individualized PDF files yourself.
