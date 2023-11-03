.. Plom documentation
   Copyright (C) 2018-2022 Andrew Rechnitzer
   Copyright (C) 2022-2023 Colin B. Macdonald
   SPDX-License-Identifier: AGPL-3.0-or-later


Scanning and uploading
======================

.. note::
   These instructions are for scanning and uploading to legacy servers.
   Much of the process is similar for the django-server, however the
   command line tools are not needed.  TODO: update these docs.


At this point we assume that you have printed that papers, fed them to
your students (or the other way around), and collected the completed
tests.

Scanning papers
---------------

To get the students’ work into Plom we have to get the physical papers
scanned. The precise details of how you do this will depend on the
scanning hardware that is available.  We recommend that you:

- scan in colour, using DPI of at least 200,
- do it yourself or delegate to someone trustworthy.
- staple removal is likely a bottleneck.  Options include scissors, a
  guillotine, or staple-remover.
- use good “paper hygiene”:

    - Sort papers into test-number order before scanning, and keep them in order (opinions differ on this but if something goes wrong its very valuable).
    - Keep papers in sensible and physically manageable bundles, before, during and after scanning.
    - Have a good physical flow of papers from pre-scan to post-scan, so that each paper is scanned exactly once.
    - Give your scans clear filenames such as ``math123mt1-sec1-bundle2.pdf``.
    - You may need to find page in these hardcopies so physically label each bundle, for example with the above filename.


Processing and uploading
------------------------

You'll also need to ensure your server is running.

The command-line tool :doc:`plom-scan` is the main tool for processing
and uploading papers.


Uploading to the server
^^^^^^^^^^^^^^^^^^^^^^^

The processing and uploading of scans need not be done on
the same computer as the original PDF production.
Indeed, Plom has been set up so that scanning can be delegated to the
"scanner" user who may be running on a different computer entirely.


Make a working directory
........................

First of all we should decide on a working directory for the scanning
and upload process.
An easy choice to make a subdirectory ``upload`` where we built our
PDFs.
Move into this directory and copy one of the scan PDFs here; we'll
assume we are working on the scans from a single bundle of papers
called ``mABCmt1-s1-b2.pdf``.
If you run :doc:`plom-scan` by itself, then it will display a simple
description of the workflow required and of the sub-commands we need.


Process a PDF into page-images
..............................

Since the scan PDF consists of images of many pages, we need to
separate the scan PDF into distinct page-images.
This is done using ``plom-scan process mABCmt1-s1-b2.pdf``.
This will result in quite a lot of output, which you can perhaps skim.
There will be a new ``bundles/mABCmt1-s1-b2.pdf/`` subdirectory
containing the extracted images and various other things.

During processing, Plom reads the QR-codes from each page-image to
determine which test-page it corresponds to.
Various sanity checks are done and page orientation adjusted.

The page-images fall into several categories: "known" (technically
"TestPages"), "unknown" and "collision".
You may see notes or warnings about the latter two during processing.


Upload the known pages
......................

The "known"s are page images which contained mostly valid QR-codes which passed various sanity checks.
If the total number of collisions and unknowns is fairly low, then the known images are ready to upload to the server::

    $ plom-scan upload mABCmt1-s1-b2.pdf
    Upload images to server
    Upload 0006,06,2 = t0006p06v2.mABCmt1-s1-b2-36.jpg to server
    Upload 0008,03,1 = t0008p03v1.mABCmt1-s1-b2-45.jpg to server
    Upload 0005,05,1 = t0005p05v1.mABCmt1-s1-b2-29.png to server

Your original PDF file should have now moved to a ``archivedPDFs/``
subdirectory.


Upload the unknowns
...................

"Unknown"s are not usually a cause for concern; they typically occur
for one of two reasons:

* the page does not contain qr-codes because it is an extra-page used
  by a student.
  We discourage giving students completely blank paper since you will
  need to be able to identify which test and question that extra page
  belongs to.
  We have templates for this purpose:
  `extraSheets.tex <https://gitlab.com/plom/plom/-/blob/main/testTemplates/extraSheets.tex>`_
  and
  `extraSheets_noname.tex <https://gitlab.com/plom/plom/-/blob/main/testTemplates/extraSheets_noname.tex>`_.
  These should be printed *double-sided*.
* the qr-codes on the page were not legible for some reason.
  Generally this is due to some scanning issue such as a page being
  folded over, or skewed.
  Occasionally it is because someone wrote on the qr-code.
  In our experience this does not happen very often.

Before you upload the unknowns, it might be a good idea to take a
quick look at them in ``bundles/mABCmt1-s1-b2.pdf/unknownPages``.
If its a small percentage of the total files in your bundle or can be
explained by the above situations, you can proceed to uploading, but
note "Unknowns" will need to be handled manually (later after
uploading, with the ``plom-manager`` tool).

On the other hand, if something has systematically gone wrong, such as
all pages are blank or very few QR-codes have been read, then you'll
likely want to check your scanning.


Upload collisions
.................

"Collisions" are generally, but not always, a cause for concern. They
indicate that the Plom system has two page-images both claiming to be
the same test-page.
We **strongly** recommend that you look at the images in the
``bundles/mABCmt1-s1-b2.pdf/collidingPages`` subdirectory before
uploading them.

There are a few ways in which "collisions" might occur:

* a given test was printed and used more than once --- this is bad and
  might be difficult to correct.
* a given test was scanned twice --- in large quantities, this will be
  annoying, and might indicate poor "paper hygiene"
* a given test-page was deliberately rescanned to replace an existing
  unreadable scan in the system (e.g., due to a folded page) --- this
  is okay.

In the first two cases, perhaps you do not want to upload these files.
But images falling into the last case should definitely be uploaded:
later the ``plom-manager`` tool can be used to select which one you
want to keep.
To upload the "collisions" run ``plom-scan upload mABCmt1-s1-b2.pdf --collisions``.


Getting a status report
^^^^^^^^^^^^^^^^^^^^^^^

It is sometimes helpful to check what papers have and have not been uploaded. It is also very helpful to see if any papers have been *partially* uploaded. To get such a status-summary, run
``plom-scan status``. You will get a simple report such as::

    Test papers unused: [12–20]
    Scanned tests in the system:
        2: testPages [1-6] hwPages []
        3: testPages [1-6] hwPages []
        4: testPages [1-6] hwPages []
        5: testPages [1-6] hwPages []
        6: testPages [1-6] hwPages []
        7: testPages [1-6] hwPages []
        8: testPages [1-6] hwPages []
        9: testPages [1-6] hwPages []
        10: testPages [1-6] hwPages []
        11: testPages [1-6] hwPages []
    Number of scanned tests in the system: 10
    Incomplete scans - listed with their missing pages:
        1: t[6] h[]


Something went wrong
^^^^^^^^^^^^^^^^^^^^

The scanning workflow is very much in flux and this documentation might lag behind.
When in doubt, check the ``plom-scan --help`` and ``plom-scan <cmd> --help``, and please file issues about specific incorrect documentation.

Note currently its not easy to wipe a bundle and start again,
`see for example Issue #1189 <https://gitlab.com/plom/plom/-/issues/1189>`_.


Technical docs
--------------

* The command-line tool :doc:`plom-scan` is the current front-end for
  most tasks related to returning work.

* For scripting or other advanced usage, you can ``import plom.scan``
  in your own Python code.  See :doc:`module-plom-scan`.
