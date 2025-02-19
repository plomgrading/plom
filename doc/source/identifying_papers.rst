.. Plom documentation
   Copyright (C) 2020 Andrew Rechnitzer
   Copyright (C) 2022-2025 Colin B. Macdonald
   SPDX-License-Identifier: AGPL-3.0-or-later


Identifying papers
==================

At some point the Plom system needs to know which paper belongs to
which student.  This can be done in several ways:

1. Prenamed papers: Plom can produce papers with student names and IDs
   already printed on them.
2. Automated ID reading — When tests are producing using Plom’s ID
   Template, the system can use `machine learning <https://xkcd.com/1838>`_
   to read the digits from the student-ID boxes and match against the
   classlist.
   In practice these appear to be over 95% accurate, but are not
   infallible.
3. Manual association — The simplest method is for a human to just read
   the ID from the page and enter it into the system.

All these eventually require verification by a human.


Running the auto-identifier
---------------------------

This will only work if your assessment uses our ``idBox`` template because
the code first looks for the outer bold rectangle and then tries to locate
the 8 digits of the student number, based on known locations inside that
larger box.

To run the auto-identifier, locate it under "ID Progress" in the Plom
web interface.

..
    TODO: xref to the `plom_server.Identify` app later, assuming those
    top-level apps show up in the docs in a meaningful way.
    I don't really want these docs to describe exactly what to click on
    the webpage b/c I'd prefer the webpage be self-documenting.

Note that by default a human will still need to confirm the
machine-read predictions.

.. tip::
   You can re-run the ID predictor at anytime, such as after confirming
   some of the IDs manually.


.. caution::

   You should manually and carefully check the results (the Identifier client
   will show you these by default) because it does make mistakes, especially
   when there are additional names available in your classlist who did not
   write the test.


Confirming and/or manually identifying
--------------------------------------

This is currently done using :ref:`the desktop client <plom-client>`.

Identifying is typically quick compared to marking and you will not need
to assign much person-time.
Since it does not require any heavy thinking it can be a good task for:

- the instructor-in-charge who is regularly interrupted by questions about papers,
- a (reliable) marker who finishes their other tasks early, or
- the scanner once they have finished scanning and uploading papers.


What to do if an ID page looks blank or is missing information?
---------------------------------------------------------------

If there is insufficient information on the page, you
can click ``View whole paper``: perhaps the ID can be found on
another page, or maybe the entire paper is blank (i.e., unused).
Clicking ``Blank page...`` will ask you to confirm the situation.


I made a mistake identifying: how can I revert an ID?
-----------------------------------------------------

Login to the web interface as either a manager or
:ref:`lead marker <lead-markers>` account.
Go to "Identifying Progress" and click on ``clear`` by the paper you
wish to reset.

On legacy servers, The UnID operation is exposed in the
beta Manager Tool -> ID Progress tab.


What is the purpose of confirming prenamed papers?
--------------------------------------------------

1. Students might sit at the wrong seat, scratch out the name and
   write their own.

2. Despite your best efforts in careful paper handling, you might
   accidentally scan a blank paper with Manji's name and ID prenamed
   on the front.  In the worst case, that could result in you
   (incorrectly) assigning a grade of zero to Manji, instead of
   recording that they Did Not Write.

All of these things and more have happened to us; its worth the time
to check.



A student wrote a different paper than what was prenamed for them
-----------------------------------------------------------------

For example suppose Isla's name was prenamed on paper 0120 but they
wrote blank paper 1280 instead.  Plom's "prenaming" is a "prediction"
because of exactly this situation.  Simply ID 1280 as normal.
(If 0120 was *also* scanned and is blank, and unsigned, then the Identifier
interface will have you confirm).
