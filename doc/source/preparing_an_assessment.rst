.. Plom documentation
   Copyright (C) 2022-2024 Colin B. Macdonald
   SPDX-License-Identifier: AGPL-3.0-or-later


Preparing an assessment
=======================

.. note::

   This page of documentation is incomplete.
   For now, see https://plomgrading.org/docs/walkthrough/create.html


Designing your assessment
-------------------------


What software should I use?
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Its up to you.  Plom will need a PDF file of your assessment (PDF files if
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
questions.
You can use the ``label`` field in the specification (see :ref:`Creating a spec`) to
*display* the two questions as "5(a)" and "5(b)".

There can be more than one question on a page; any shared pages will
be duplicated during marking (that is, each marker will get their own
copy for annotating).
Any questions sharing a page will be drawn from the same version.

Questions can also span multiple pages, even in a multi-versioned
assessment.


.. _Creating a spec:

Creating a "spec file"
----------------------

For now, see https://plomgrading.org/docs/walkthrough/testspec.html



Technical docs
--------------

* On legacy servers, the command-line tool :doc:`plom-create` is used for
  most tasks related starting a new assessment.

* For scripting or other advanced usage, you can ``import plom.create``
  in your own Python code.  See :doc:`module-plom-create`.
