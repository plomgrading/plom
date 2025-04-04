.. Plom documentation
   Copyright (C) 2022-2025 Colin B. Macdonald
   SPDX-License-Identifier: AGPL-3.0-or-later


Solutions
=========

.. note::
   These instructions are working with solutions on legacy servers.
   TODO: update these docs.


Plom can manage solutions for your exam.  These are used for showing
solutions on-screen to markers and for returning a custom solutions
file alongside a student's returned work.

The solutions can be revised, at least until they are returned to
students.


Making solutions
----------------

Your solutions can use the same structure as your blank exam or a
completely different structure.  See ``plom-solutions --help`` for
details.


Getting solutions onto the server
---------------------------------

The command-line tool :doc:`plom-solutions` can extract solutions from
PDF files, push to server, etc.  See ``plom-solutions --help`` for
more information.


Preparing solutions for students
--------------------------------

As part of a digital return, The command-line tool :doc:`plom-finish`
can construct individual PDF files for each student based on the
question-versions used in their test.  See :doc:`returning` for more
information.



Technical docs
--------------

* The command-line tool :doc:`plom-solutions` is the current front-end
  for most tasks related to returning work.

* For scripting or other advanced usage, you can ``import plom.solutions``
  in your own Python code.  See :doc:`module-plom-solutions`.
