<!--
__copyright__ = "Copyright (C) 2019-2024 Colin B. Macdonald"
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


Scanning
--------

### Do I need to carefully pick out just the right pages when rescanning a bundle?

It depends.  Suppose we have scanned "BundleA1" but some pages misfed,
and do not appear in the resulting PDF file.  In this case, its
perfectly fine to rescan the whole bundle.  Use a new bundle name, say
"BundleA1-rescan".  Now process as usual.  When uploading, `plom-scan
upload BundleA1-rescan` will upload the new non-colliding pages and
you'll get a message about collisions (lots and lots of collisions!)
Just ignore that and *do not* pass `--collisions`.



Server administration
---------------------

### My server sometimes has random disk I/O errors

Like this `peewee.OperationalError: disk I/O error`?
Plom uses an SQLite database; it
[should not be run on NFS storage](https://gitlab.com/plom/plom/-/issues/811).
Apparently "people" know this but we were just as "thrilled" as you probably
are to discover it on a production server.


### How can I get past SSL certificate errors?

E.g.,
```
SSLError(SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed certificate (_ssl.c:997)'))
```
Or `plom-create status` might be showing you:
```
[!] insecure connection (self-signed or invalid SSL cert)
```
SSL is used to securely verify the identity of the server you are
connecting too.
If you're only experimenting, you can bypass the checks by setting a
special environment variable, e.g., in bash:
```
export PLOM_NO_SSL_VERIFY=1
```
The graphical client offers a mechanism to ignore SSL errors (at you
and your users' own risks).

**For production servers, you'll need to investigate how to setup SSL
certificates.**


### Ok, how do I setup SSL certificates?

We are not experts on this topic, but
[LetsEncrypt](https://letsencrypt.org) is a good place to start.



### How can I clone a server?

For example, how can I make another copy of a running server?  One way
is to copy the filesystem of the running server, then modify
``serverDetails.toml`` to change the port.
Its also possible to make a new server from scratch that accepts scans
intended for the old server.  This is discussed next.


### How do I change the public code and/or private seed of my server?

This can be done provided you have not yet made PDF files (whose
QR-codes would contain that public Code).

On the new Django-based server, login as any Admin user, then go to `/admin`.
This gives your direct access to most of the raw database tables.
Find the Specification and change the publicCode and/or privateSeed.

One should be very carefully doing this sort of thing: the
`publicCode` exists to make it difficult to accidentally upload the
papers to the wrong server.  This question shows you how to defeat
that mechanism.


### How do I reset my legacy server to the pre-scanned state?

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


### I messed up by double-scanning some papers and uploading and now I have collisions!

If there are only collisions in your bundle, you can remove the bundle
without pushing it.

If there are some non-colliding pages in the bundle that you want to
keep, one approach might be to find those papers in the physical
bundle and rescan them.  The other option is to discard all the
colliding pages, so that you can push the remaining non-colliding
pages.


### I messed up by *double-printing* some papers, now I have collisions!

This is a serious problem which you should avoid getting into...
If two students have written on (say) paper number 20, then you will
get collisions at upload time.

Let's suppose the scanned bundles are contiguous: that is, the two
paper number 20s are not interleaved in the scanning process.  For
example, they are in two separate bundles.  (If this is not so, have
a cry and consider sorting and rescanning?)

At this point you have paper 20 "A" scanned into the system.  Now
upload paper 20 "B".  You will not be able to push it because of the
collisions.

Next: if you have only one version, you can discard all the pages
then convert to known pages of some **unused**
paper number, say 107 (assuming you have spares; if not see below).


### I messed up by double-printing and I'm using *multiple versions*

This is similar to the above but we cannot simply push paper number
20 "B" into a spare unused paper slot (say 107).  This is because
paper number 107 will have different versions than 20.

A [future version of Plom](https://gitlab.com/plom/plom/-/issues/1745)
might allow you to instantiate arbitrary new rows of the database using
the versions of paper number 20.  Roughly: extract the relevant
version numbers for paper 20.  Use those
to make the brand new row, using a complete new paper number: say 1020.

But for now, the workaround is complicated:
  1. Clone the server from the pre-scanning state (see question
     elsewhere).
  2. Update the duplicated papers into the 2nd server.
  3. Have your grading team grade on both (alternatively, have them
     do most of the grading on Server 1, then download the rubrics
	 and push those rubrics to Server 2.



Changing the spec later
-----------------------

### Students have already written my assessment, can I split one of my questions up?  Can I merge two questions?

Yes, although there is some work.  Keep the old server up for now
("Server A").  Make a new server ("Server B").  Hack the spec to
duplicate the public code from A to B (see instructions above for
"resetting a server to the pre-named state").  Change the spec as you
wish (with in the constraints of the papers you already have).  If you
have mono-versioned test, nothing else is required: upload the papers
to Server B.

If you have a multiversioned test, its a bit harder:
  1. extract the version map from Server A
     (``plom-create get-ver-map -s plomA.example.com``).
  2. modify that version map for your new paper layout.  For example,
     if you are splitting "Q5" (physically laid out as 5(a) on Page 11
     and 5(b) on Page 12) into separate "Q5" and "Q6", then they must
     both have the same version as the original Q5.
  3. upload that version map to Server B when making the database.
     ``plom-create make-db --from-file my_new_vermap.csv -s plomB.example.com``
  4. Upload the papers to Server B.


### I have already uploaded scans, can I split one of my questions up?  Can I merge two questions?

Not easily.  Currently we would suggest re-uploading to a new server
following the instructions above.
