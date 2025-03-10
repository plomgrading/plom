.. Plom documentation
   Copyright (C) 2024 Aidan Murphy
   Copyright (C) 2024-2025 Colin B. Macdonald
   SPDX-License-Identifier: AGPL-3.0-or-later

*********************************
Developer guide
*********************************

Plom aims to facilitate digital marking of physical exams without
(meaningfully) altering the experience of examinees,
outside of writing the exam they should have no interaction with Plom.

Project structure
================================

Most Plom code can be found in one of two directories in the
`project repository <https://gitlab.com/plom/plom>`_:
 * ``plom/``
 * ``plom_server/``
The former is currently (2025 March) "in-flux" as the marking client has
moved to a separate Plom-Client repo <https://gitlab.com/plom/plom-client>`_.
The latter contains the "current" (non-legacy) Plom server.

Note both ``plom/`` and ``plom_server/`` are modules.


Contributing to Plom
================================

Contributions to this project could broadly focus on:
 * improving usability for users (mostly higher education instructors).
 * gathering and **minimal** wrangling of test/marker data.
 * documenting the project.
 * code refactoring or packaging improvements to make maintenance easier.

Plom development is guided by several motifs.

**User-focused:** Plom's "users" are people preparing tests and
markers; they are not generally exam-takers.

**Data and Privacy:** Using Plom, data related to marking patterns and examinee performance can,
without intruding on the marking process, be collected very accurately
and on a large scale.
Much of this data is: sensitive; private; or, in the case of marking patterns,
highly context dependent.
It is extremely important that Plom does not overstep the bounds of
personal privacy, or create bias by over analyzing data that requires
additional context.

**Plom is not an LMS:** Plom is to act as a supporting tool for users rather than a complete
Learning Management System, it should contain a minimal set of features to
comfortably facilitate digital marking, and leave the rest to the user.

**Pragmatic:** A common refrain of Plom development is "use as little
of ____ as possible but no less than that".  Examples include "use as
little Javascript as possible but no less than that", and "avoid HTML
in-line styling is, unless its helpful."  This is a re-stating of
"practicality beats purity" from
`The Zen of Python <https://peps.python.org/pep-0020/>`_.

Automatic updating of dependencies is beyond the scope of this project.
Plom is not a package manager.


Getting started
---------------------------------

This project is controlled with git, maintainers will happily welcome
contributors but are not keen to teach the basics of git.
There are many guides and tutorials freely available to learn git, here is one by
`gitlab <https://docs.gitlab.com/ee/tutorials/learn_git.html>`_.


Repository set up
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Plom uses a distributed model for git development, contributors are to fork the
main repository: ``plom/plom``, if you don't know how to do this, gitlab has
`instructions <https://docs.gitlab.com/ee/user/project/repository/forking_workflow.html>`_.

Next, clone your forked repository to your local machine and track the official
Plom repository as an upstream repository, for example:

.. code-block:: sh

   $ git clone git@gitlab.com:$user_name/plom.git
   $ cd plom
   $ git remote add upstream https://gitlab.com/plom/plom.git

There are now **3** Plom repositories relevant to you:
 * **upstream**: the official Plom repository, this exists on on a gitlab server.
 * **origin**: your fork of the upstream repository, this exists on a gitlab server.
 * **local**: the clone of origin, this exists on your machine.

As a contributor you will not be able to commit changes or new branches directly to the
upstream repository; you will need to commit branches to origin and open
`Merge Requests <https://docs.gitlab.com/ee/user/project/merge_requests/creating_merge_requests.html>`_
to the upstream/main branch.

You will need to keep your origin/main branch up to date with upstream/main branch,
the pattern to do this should look familiar:

.. code-block:: sh

   # in your local repository
   $ git checkout main
   $ git fetch upstream
   $ git merge upstream/main


Best practices
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Guidelines and information more specific to this project can
be found on the
`Plom project wiki <https://gitlab.com/plom/plom/-/wikis/home>`_.
