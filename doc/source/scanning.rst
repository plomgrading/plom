.. Plom documentation
   Copyright (C) 2018-2022 Andrew Rechnitzer
   Copyright (C) 2022-2025 Colin B. Macdonald
   SPDX-License-Identifier: AGPL-3.0-or-later


Scanning and uploading
======================

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
      There is a strict upper limit on bundle size and page count; these exist for security reasons and far exceed what would be a sensible bundle size.
    - Have a good physical flow of papers from pre-scan to post-scan, so that each paper is scanned exactly once.
    - Give your scans clear filenames such as ``math123mt1-sec1-bundle2.pdf``.
    - You may need to find page in these hardcopies so physically label each bundle, for example with the above filename.


Uploading to the web-based server
---------------------------------

Create one or more "scanner" accounts.
Login to your server using one of those accounts.
Follow the instructions to upload bundles of papers as PDF files.


Dealing with unknown pages, extra pages, etc
............................................

TODO




Technical docs
--------------

* The command-line tool :doc:`plom-cli` can be used to upload files
  from the command line.

* The command-line tool :doc:`plom-scan` is the current front-end for
  most tasks related to scanning work onto legacy servers.

* For scripting or other advanced usage, you can ``import plom.scan``
  in your own Python code.  See :doc:`module-plom-scan`.
