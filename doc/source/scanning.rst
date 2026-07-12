.. Plom documentation
   Copyright (C) 2018-2022 Andrew Rechnitzer
   Copyright (C) 2022-2026 Colin B. Macdonald
   Copyright (C) 2026 Aidan Murphy
   SPDX-License-Identifier: AGPL-3.0-or-later


Scanning and uploading
======================

At this point we assume that you have printed exam papers, fed them to
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
      There is a strict upper limit on bundle size and page count; these exist for security reasons and far exceed what would be a sensible bundle size.
    - Have a good physical flow of papers from pre-scan to post-scan, so that each paper is scanned exactly once.
    - Give your scans clear filenames such as ``math123mt1-sec1-bundle2.pdf``.
    - You may need to find page in these hardcopies so physically label each bundle, for example with the above filename.


Uploading to the web-based server
---------------------------------

Create one or more "scanner" accounts.
Login to your server using one of those accounts.
Follow the instructions to upload bundles of papers as PDF files.


Dealing with unknown pages, extra pages, error pages, etc
.........................................................

After uploading PDF files to your server, you likely have some
"Pages that need your attention":

- Pages without readable QR codes are classed as **unknown pages**..
- Plom **extra pages** need assignment to specific papers and questions.
- **Error pages** have readable QR codes, but Plom won't process them
  for marking.

**These require manual intervention using the web interface**. Scanner users can
manually reclassify the "pages that need your attention", or rescan and upload
relevant pages or bundles if there are issues with the scanned images (e.g., a
folded page obscuring an examinee's work).


Collisions
..........

QR codes on papers are intended to be unique.
A _collision_ occurs when Plom interprets two uploaded pages as having
the same QR codes.
Collisions can occur either within one bundle or between a page of
bundle and pages that have already been pushed.

"Good collisions" are caused for example by re-scanning a page.
These can be dealt with using the web interface, for example by
discarding one of them.

"Bad collisions" come from accidental reuse of papers, most commonly
because of double-printing.
This is a more serious problem, see :doc:`faq`.


Technical docs
--------------

* The command-line tool :doc:`plom-cli` can be used to upload files
  from the command line.
