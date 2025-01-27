.. Plom documentation
   Copyright (C) 2020 Andrew Rechnitzer
   Copyright (C) 2021-2022, 2024 Colin B. Macdonald
   SPDX-License-Identifier: AGPL-3.0-or-later

The marking process
===================

Once some of your papers have been scanned and uploaded, you can get
your marking team to start working.

.. tip::
    You do not need to wait until all papers are processed before starting.


Ready to mark
-------------

Your markers will all need to download the :ref:`desktop Plom Client app <plom-client>`.

They can then begin the process of annotating papers, leaving useful
feedback and assigning marks (grades).
It is by far the most important part of the assessment, and will
consume the vast majority of your available person-time.
Individual markers can be assigned to a specific version of a specific
question.


Marking party!
--------------

Some people recommend that your term work at least initially
in the same physical location.
Of course, you can use Plom to do your marking just about anywhere,
but it has been observed that marking goes much faster and is more
consistent when you are all in the same location.
Once your marking scheme has been exposed to real student responses
and your team has worked out the kinks, physical proximity is less
important.


Tracking progress
-----------------

You can use manager accounts to keep an eye on progress.
If you are using the older legacy server, see :doc:`manage`.


Tagging tasks
-------------

Each task can be tagged with essentially arbitrary short text tags,
which are used to communicate within the grading team (they are not by
default shown to students).

Tagging it to a particular user will mean that Plom is more likely to
assign the task to that user.


Reassigning and reverting tasks
-------------------------------

You can find tasks under the "Progress" section of your Plom admin site.
There you can "reset" (revert all annotations made to a task) a task.
You can also assign it to another user, keeping existing annotations intact.

.. caution::
    Reassigning tasks is still work-in-progress.


Quotas
------

Sometimes you may wish to temporarily limit the numbers of questions a
user can mark.
You can do this by setting a per-user quota in the User Management
part of the Plom admin site.
After a marker reaches their quota, they will not be allowed to mark
additional papers, until you remove or increase their quota limit.

Examples of this feature include:

   1. You are working with novice graders and want to review their
      marking and/or meet with them after they have graded (say) 20
      tasks.
   2. You're working with a team and want everyone to mark 10 tasks,
      then have a meeting to settle on a common set of rubrics.
   3. You have 300 tasks that need grading and want to want to ensure
      that everyone does their share.


.. _lead-markers:

Permissions and "Lead Markers"
------------------------------

Plom has various permissions or actions that can be granted to marker
accounts.  Some of these permissions can be configured on the server,
but by default they are currently lumped together under the umbrella
"lead markers"; you can promote or demote your marker account as
needed.

  * Lead markers can modify any non-system rubrics; regular markers
    can only edit rubrics they themselves created.
  * Lead markers can see any task in the currently-selected question
    and version.  They can claim any task.
  * Lead markers can reassign tasks between themselves or other
    markers.
  * Lead markers can view detailed statistics and progress
    information.
  * Lead markers can ID papers.


Responsibilities of non-lead markers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Regular (non-lead) marker accounts are generally used to mark a
particular question in the order that Plom hands out tasks.  They are
responsible for marking fairly and consistently, often using an
existing set of rubrics.  They may we working collaboratively with a
team and are responsible for communicating with that team.



Best-practices for "small" classes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you have less than say 300 student and/or a smallish marking team
(say a half-dozen folks marking) than there may not be much benefit to
making distinctions between lead and non-lead markers.  One reasonable
approach would be to simply make *everyone* lead.


Best practices for large teams
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Best practice is very much still evolving but for a large exam with a
tightly-controlled marking scheme, you might choose to have one or
more lead markers in charge of each question.

  - In a large team, there will likely be multiple markers on the same
    question: ensuring consistency and preventing rubric proliferation
    becomes even more important.
  - All rubric changes would be performed by the leads, especially
    changes that retroactively effect existing annotations.
  - Leads might review others' work with goals of improving
    consistency and/or professional development of mentorees.
  - Leads might track per-question progress and coordinate changes in
    teams as overall marking progresses.
