.. Plom documentation
   Copyright 2018-2022 Andrew Rechnitzer
   Copyright 2022 Colin B. Macdonald
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

- scan in colour,
- use DPI at least 200,
- do it yourself or delegate to someone trustworthy. Scanning is a key task.
- staple removal is likely a bottleneck.  Options include scissors, a
  guillotine, or staple-remover.
- use good “paper hygiene”: "paper":
    - Sort papers into test-number order before scanning, and keep them in order (opinions differ on this but if something goes wrong its very valuable).
    - Keep papers in sensible and physically manageable bundles, before, during and after scanning.
    - Have a good physical flow of papers from pre-scan to post-scan, so that each paper is scanned exactly once.
    - Give your scans clear filenames such as ``math123mt1-sec1-bundle2.pdf``.
    - You may need to find page in these hardcopies so phyiscally label each bundle, for example with the above filename.

You'll also need your server running.


Processing and uploading
------------------------

The command-line tool :doc:`plom-scan` is the main tool for processing
and uploading papers.


Unknown pages
-------------


Python module: ``plom.scan``
----------------------------

For scripting or other advanced usage, you can ``import plom.scan``
in your own Python code.

.. automodule:: plom.scan
    :members:
