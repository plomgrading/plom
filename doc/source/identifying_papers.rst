.. Plom documentation
   Copyright 2020 Andrew Rechnitzer
   Copyright 2022 Colin B. Macdonald
   SPDX-License-Identifier: AGPL-3.0-or-later


Identifying papers
==================

At some point the Plom system needs to know which paper belongs to which student and this can be done in several ways:

1. Papers named from the start — Plom can produce papers with student
   names already printed on them.
   In this case Plom already knows which paper belongs to who and
   typically no extra work is needed.
2. Automated ID reading — When tests are producing using Plom’s ID
   Template, the system can use `machine learning <https://xkcd.com/1838>`_
   to read the digits from the student-ID boxes and match against the
   classlist.
   In practice these appear to be over 95% accurate, but are not
   infallible.
3. Manual association — The simplest method is for a human to just read
   the ID from the page and enter it into the system.

These last two cases require human-intervention, which is where “identifier” comes in.


Running the auto-identifier
---------------------------


Manually identifying
--------------------

This is typically quite quick compared to marking and you will not need
to assign much person-time.
Since it does not require any heavy thinking it can be a good task for:

- the instructor-in-charge who is regularly interrupted by questions about papers,
- a (reliable) marker who finishes their other tasks early, or
- the scanner once they have finished scanning and uploading papers.

For now see https://plomgrading.org/docs/clientUse/identifying.html
