.. Plom documentation
   Copyright 2020 Andrew Rechnitzer
   Copyright 2022-2023 Colin B. Macdonald
   SPDX-License-Identifier: AGPL-3.0-or-later


Identifying papers
==================

At some point the Plom system needs to know which paper belongs to which student and this can be done in several ways:

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

Currently, the django-server requires command line access to run
the autoidentifier.  TODO: xref here once those tools are in the docs
Tracking issue for running this via the web
UI: `Issue #2990 <https://gitlab.com/plom/plom/-/issues/2990>`_.


Running the auto-identifier (legacy server)
-------------------------------------------

1. Open the :doc:`Manager tool <manage>`, then "Progress" → "ID progress".
2. Optionally, adjust the top/bottom crop values, either manually or by clicking "Select interactively".
3. Click "Recognize digits in IDs" which starts a background job.
   Click "Refresh" to update the output window.
4. Click "Run LAP Solver".  This currently blocks and might take a
   few seconds (say 3 seconds for 1000 papers).
5. Click "Refresh Prediction list" to update the table view.

.. caution::

   You should manually and carefully check the results (the Identifier client
   will show you these by default) because it does make mistakes, especially
   when there are additional names available in your classlist who did not
   write the test.


Manually identifying
--------------------

This is typically quite quick compared to marking and you will not need
to assign much person-time.
Since it does not require any heavy thinking it can be a good task for:

- the instructor-in-charge who is regularly interrupted by questions about papers,
- a (reliable) marker who finishes their other tasks early, or
- the scanner once they have finished scanning and uploading papers.

For now see https://plomgrading.org/docs/clientUse/identifying.html
