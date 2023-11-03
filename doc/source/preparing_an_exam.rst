.. Plom documentation
   Copyright (C) 2022-2023 Colin B. Macdonald
   SPDX-License-Identifier: AGPL-3.0-or-later


Preparing an Exam
=================

.. note::

   This page of documentation is incomplete.
   For now, see https://plomgrading.org/docs/walkthrough/create.html


Designing your test
-------------------


What software should I use?
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Its up to you.  Plom will need a PDF file of your test (PDF files if
you are using multiple versions).  Plom came out of the mathematics
community where LaTeX is commonly used, and we provide a template.
But you can use any software you like.


What should each "question" be?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. tip::
   Plom defines a question as the smallest unit of independently
   markable material.

So if 5(a) and 5(b) can be marked by TAs Jane and Austin
*simultaneously* and *independently*, then those can be separate
questions.  You can use the ``label`` field in the test spec (see :ref:`Creating a spec`) to
*display* the two questions as "5(a)" and "5(b)".

Currently there is an additional constraint: each question must begin
on a new page.  We anticipate relaxing this requirement in the future.

Note that questions can span multiple pages, even in a multi-versioned
assessment.


.. _Creating a spec:

Creating a "spec file"
----------------------

For now, see https://plomgrading.org/docs/walkthrough/testspec.html



Technical docs
--------------

* On legacy servers, the command-line tool :doc:`plom-create` is used for
  most tasks related starting a new test.

* For scripting or other advanced usage, you can ``import plom.create``
  in your own Python code.  See :doc:`module-plom-create`.
