.. Plom documentation
   Copyright (C) 2023-2025 Colin B. Macdonald
   SPDX-License-Identifier: AGPL-3.0-or-later


Rubrics
=======

Plom uses the term "rubrics" to refer to reusable comments, where each
rubric is often (but not always) associated with a change in score.


Rubrics in the Client
---------------------

The list of rubrics appears on the left side of the client window, and
rubrics are typically organized into several tabs.  Keyboard shortcut
keys are designed to allow navigation up-and-down the list and between
tabs of rubrics.  You can press the ``?`` key to learn more about
Plom's shortcut keys.

Rubrics can be associated spatially with a particular region of the
page by dragging to create a box then clicking again to place the
rubric.

.. note::
   Rubrics are shared between markers.  When you create a new rubric, it
   is immediately created server-side and shared with all users.
   Depending on server settings, you might be able to modify rubrics.
   created by others.  Consult with your instructor.

.. note::
   Currently rubrics are pulled from the server on Annotator start,
   or when users click the ``Sync`` button in the lower-left.
   We anticipate more automatic synchronization in the future.


Creating and modifying rubrics
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

One of Plom's goals is that a group of markers can collaboratively
construct and consistently apply a set of fair rubrics.

Managers can control who can create new rubrics and modify existing
ones.
For example, you might want to carefully construct rubrics yourself
and require your markers to apply your grading scheme exactly as is.
At the other extreme, you might want to allow everyone to modify any
rubric as they see fit.
The default is somewhere in the middle; anyone can create their own
rubrics, and some users can modify all rubrics.

.. warning::
   Currently, there is no mechanism to revisit papers that were
   affected by modifying a rubric.  For example if you change "-1 not
   the chain rule" into "-2 not the chain rule" then previously-marked
   papers will still have the "-1" version.  Developing a workflow for
   updating for such changes is of considerable interest:
   see `Issue #3351 <https://gitlab.com/plom/plom/-/issues/3351>`_.


Rubric Scope
------------

Question scope
^^^^^^^^^^^^^^

By default, rubrics are not shared between questions.
Currently this is not changeable,
see `Issue #3253 <https://gitlab.com/plom/plom/-/issues/3253>`_.


Version-level scoping
^^^^^^^^^^^^^^^^^^^^^

If you have multiple versions, rubrics are by default shared between
versions of a question.  There are two ways of restricting things:

1. You can parameterize a rubric over versions, inserting text
   substitutions on a per-version basis.  This works well, for
   example, if one question has "x" while another has "y".

2. You can restrict rubrics to a particular version (or versions).

.. warning::
   Parameterized rubrics are a relative new feature: please discuss whether
   or not to use them with senior members of your grading team.


Scoping within a question
^^^^^^^^^^^^^^^^^^^^^^^^^

You can restrict a rubric to one part of a question in an informal
sense by creating groups.  For example, suppose Q3 is out of 12
points, where part (a) is worth 5 of those points.  You can create a
Rubric Group called "(a)", and restrict some of your rubrics to that
group.  Clients will typically display grouped rubrics in a tab.

Additionally, if several rubrics are marked as **exclusive** within a
group, then clients will allow you to choose at most one of them.
This can be combined with absolute rubrics such as "3 of 5: used
product and chain rules but calculations incorrect" and "4 of 5: right
idea, but there is a small calculation error".

.. warning::
   Rubric groups are a new feature: please discuss whether or not
   to use them with senior members of your grading team.


Managing rubrics
----------------

It also possible to populate the rubric database in bulk from external
tools such as a spreadsheet.  For example, this could be done before
marking begins or by reusing rubrics from a previous assessment.
This still needs to be implemented:
see `Issue #3352 <https://gitlab.com/plom/plom/-/issues/3352>`_.

If you're using the legacy server,
see the :doc:`plom-create` command-line tool or the :doc:`module-plom-create`.
