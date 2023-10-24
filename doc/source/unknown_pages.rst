.. Plom documentation
   Copyright (C) 2022-2023 Colin B. Macdonald
   Copyright (C) 2022-2023 Chanelle Chow
   SPDX-License-Identifier: AGPL-3.0-or-later


Classifying Unknown Pages
=========================

After scanning, you likely have some "Unknown Pages", such as pages
without QR codes due to printing/scanning troubles, extra pages using
our template or even adhoc pages such as looseleaf.

1. open the :doc:`Manager tool <manage>` and go to the "Scanning" tab.

2. In the "Unknown Pages" tab you'll find a list of unknown pages.

3. Double click on one of them.

4. Generally, for anything that isn't a QR-coded Test Page, choose
   "Extra Page":

   - type in the test number
   - select any questions this page is part of.  If you're uncertain,
     select them all.  E.g., if you think it might be Q7 and/or Q9,
     click both those.
   - "Click to confirm".
   - this action is now "staged" (has not happened yet).

     - You can click "Perform staged actions" to make it permanent.
     - You can stage more than one action if you want.
     - Refreshing or exiting the Manager tool will discard staged actions.

5. If the page is a blank Extra Page, you can instead Discard.

6. Misread Test Pages.
   Occasionally, you may see pages where the QR-reader has failed (hopefully
   these are rare).  Folded pages are one possibility: you may
   need to re-scan a page; see Collisions below.  If its simply misread:

   - click "Test Pages".
   - specify the test number and page number
   - confirm (as with Extra Pages, the action is now "staged").


You might want to do these operations before grading begins.
If done later, adding pages will automatically invalidate any relevant
marking work (e.g., you assign an extra page to 0124 Q7 then 0124 Q7
will need to be regraded).


Collisions
----------

"Good collisions" are caused for example by re-scanning a page.
These can be dealt with similarly to Unknown Pages in the :doc:`Manager tool <manage>`.
"Bad collisions" come from accidental reuse of papers e.g., from double-printing.
This is a much more serious problem, see :doc:`scanning` and :doc:`faq`.
