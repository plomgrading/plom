.. Plom documentation
   Copyright (C) 2025-2026 Aidan Murphy
   SPDX-License-Identifier: AGPL-3.0-or-later

Glossary
========

Much of Plom is under heavy development, some of these terms will
undoubtedly change.


.. glossary::
   :sorted:

   Bundle
      A .pdf file uploaded to Plom. It can contain work from one or more
      assessment submission[s].
   Collision
      The situation where an image in a staged :term:`Bundle` has been interpreted
      (or intentionally assigned) as being an image of a page from a particular
      :term:`QR-coded Paper` which already has an associated image.

      For example, if page 3 from Paper 0054 has been pushed to a Plom server,
      and you stage a bundle ``my_bundle.pdf`` that contains another image
      (or the same image) of page 3 from Paper 0054, there exists a collision
      and it could be said that the staged image of page 3 from Paper 0054
      is a colliding image.

      Note that an :term:`Extra page` cannot cause a collision.
   Extra page
      An image pushed to a Plom server in a :term:`Bundle` that is not part of
      a :term:`QR-coded Paper`, but has been associated with one or more
      questions on a particular :term:`Paper`.

      Plom has generic micro-qr-codes that allow Plom to automatically categorise
      an image of paper as an "Extra page", though a :term:`Scanner` must still
      manually associate each extra sheet a particular paper, and optionally
      one or more questions.
   Identify
      Associate an examinee ID (a sequence of numbers) and name with a paper.
   Lead Marker
      A :term:`Marker` that has decision making authority over one or more question.
   Manager
      A user permitted to manage the server.
   Marker
      A user permitted to digitally mark (i.e., grade) scanned papers.
   Paper
      A collection of work that can be attributed to a single assessment submission.
      This can refers to both physical papers and the scans uploaded to Plom.
   QR-coded Paper
      A :term:`Paper` with QR codes on each page that are recognisable by Plom.
      When scanned and uploaded, these pages will be categorised automatically.
   Scanner
      A user permitted to upload papers.
   Specification
      A description of the structure of the assessment and blueprint for building
      QR-coded papers. It describes how scanned work should be grouped together and
      retrieved for markers.
      Sometimes shortened to "Spec".
