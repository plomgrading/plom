<!--
__copyright__ = "Copyright (C) 2019-2022 Colin B. Macdonald"
__license__ = "AGPL-3.0-or-later"
 -->

Frequently Asked Questions
==========================

Common questions and tips 'n tricks that may not appear elsewhere in the
documentation.


Plom Client software
--------------------

### Some windows/dialogs are awkward to resize on Gnome Desktop

You could try disabling "Attach Modal Dialogs" in the "Gnome Tweaks" app,
but mostly this has been fixed recently by improving the way we use modal dialogs.



Identifying
-----------

### How does the auto-identifier work?

Machine learning trained on the MNIST handwritten digit dataset.  A linear
assignment problem solver then matches the results against the class list.
For this reason the class list csv file should not contain large numbers
of additional students that are not in your class.


### Student wrote a different paper; I cannot ID their new paper.

You must first "Unidentify" the prenamed paper.  For example suppose
Isla's name was printed on paper 0120 but they wrote blank paper 1280
instead.  In this case you should "UnID" paper 0120, and then you'll
be able to identify paper 1280 to Isla.

The UnID operation is exposed in the beta Manager Tool -> ID Progress
tab.



Test Preparation
----------------

### For self-submitted work, should I start each question on a new page?

Yes.  This is important because it makes it easier for markers to find the
answers, especially if they need to use the rearrange pages dialog.

While preparing the test, we suggest writing something like *"Please start
a new page NOW"* at the start of each question.



Marking
-------

### Why doesn't Plom have fractional marks?

Because the main developers of Plom don't use them. We feel that they
tend to over-complicate marking schemes and that it is better to simply
make your test out of a larger total rather than mess about with "1/2"s
or "1/3"s. This also makes things more consistent when a large team is
trying to mark using the same scheme / rubric. We admit that this is
forcing our own ideas about marking onto others, however, after
supervising the marking of many tests and exams, we feel that this is
the right way to go (the absence of fractional marks, not the forcing
people to do what we think)

Of course, if an energetic co-developer would like to implement fractional marks, then we won't stop them.


### Why do you have "+0" and "-0" as possible delta-marks?

(Current versions of Plom do not expose this feature.)

Mathematics use "epsilon" to represent small number, often in the
context of limits. Some markers like to indicate to students via (say)
"-0" that there is a small error in their work but it is too small to
reduce their overall mark. Similarly some markers use "+0" to indicate
that a small amount of progress has been made, but not enough to be
worth a full point.



Server administration
---------------------

### My server sometimes has random disk I/O errors

Like this `peewee.OperationalError: disk I/O error`?
Plom uses an SQLite database; it
[should not be run on NFS storage](https://gitlab.com/plom/plom/issues/811).
Apparently "people" know this but we were just as "thrilled" as you probably
are to discover it on a production server.


### How can I clone a server?

For example, how can I make another copy of a running server?  One way
is to copy the filesystem of the running server, then modify
``serverDetails.toml`` to change the port.
Its also possible to make a new server from scratch that accepts scans
intended for the old server.  This is discussed next.


### How do I reset my server to the pre-scanned state?

You need two things: the ``question_version_map.csv`` file which you
can get with the command line tools: ``plom-create get-ver-map``.
This is important because Plom needs to know which versions to expect
for which question.  You can upload this to your new server using
``plom-create make-db --from-file old_qvmap.csv``.

You will also need the ``verifiedSpec.toml`` which is harder to get:
it can be extracted from the file system of your old server by copying
``specAndDatabase/verifiedSpec.toml``.

There are two fields in ``verifiedSpec.toml`` that are probably not
in your original spec file:
```
privateSeed = "0052084227513987"
publicCode = "302386"
```
Calling ``plom-create uploadspec verifiedSpec.toml`` to push this spec
into the new server will (currently) populate those fields as-is,
thus ensuring the server will be able to read in physical papers
printed from the original server.  In future, this might require
more effort such as passing a ``--force``.

If you do not have access to the file system of your old server, it
should be possible to extract the `publicCode` from the QR codes of
the printed pages.  See the source code ``plom/tpv_utils.py`` for
hints on how to do this.  The `privateSeed` should not be necessary
for this procedure.

<!-- todo: switch to ReST and use alert box here, and fix links -->

One should be very carefully doing this sort of thing: the
`publicCode` exists to make it difficult to accidentally upload the
papers to the wrong server.  This question shows you how to defeat
that mechanism.
