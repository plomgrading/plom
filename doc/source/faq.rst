.. Plom documentation
   Copyright (C) 2019-2025 Colin B. Macdonald
   Copyright (C) 2025 Aidan Murphy
   SPDX-License-Identifier: AGPL-3.0-or-later

Frequently Asked Questions
==========================

Common questions and tips 'n tricks that may not appear elsewhere in the
documentation.


Plom Client software
--------------------

Some windows/dialogs are awkward to resize on Gnome Desktop
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You could try disabling "Attach Modal Dialogs" in the "Gnome Tweaks" app,
but mostly this has been fixed recently by improving the way we use modal dialogs.



Test Preparation
----------------

For self-submitted work, should I start each question on a new page?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Yes.  This is important because it makes it easier for markers to find the
answers, especially if they need to use the rearrange pages dialog.

While preparing the test, we suggest writing something like *"Please start
a new page NOW"* at the start of each question.



Marking
-------

Does Plom support fractional marks?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Plom now has preliminary support for "half-marks" and in principle
finer divisions.  "+½" and "-½" delta rubrics can be added to your
server under "Rubric management".  More complete support, for example
including full clientside creating/editing of fractional rubrics could
be added by future energetic co-developers.



Why do you have "+0" and "-0" as possible delta-marks?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

(Current versions of Plom do not expose this feature.)

Mathematics use "epsilon" to represent small number, often in the
context of limits. Some markers like to indicate to students via (say)
"-0" that there is a small error in their work but it is too small to
reduce their overall mark. Similarly some markers use "+0" to indicate
that a small amount of progress has been made, but not enough to be
worth a full point.


How can I review the work of a marker?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There are several ways to do this, in various stages of development.
Suppose we wish to check all the marking by Yakov on Question 2
version 2.  We have at least three options:

1. Reset the password for Yakov.  Use their account in the client to
   look at and adjust marking as needed.

2. Login to the web interface as a manager or lead marker.  Search by
   question and username.  Look over each task.

   * You can "reassign" any tasks that need regrading to another
     marker, say, Sierra.
   * Or you can "tag" tasks (e.g., with "regrade") and ask Yakov to
     revisit them.
   * Or you can "reset", removing all annotations and putting the task
     back in the pool.
   * In either case, Sierra and/or Yakov can use Plom Client to do the
     regrading.  They might find it useful to sort tasks in the Client
     by tags.
   * When working on the same tasks in the Client and the web
     interface, it will be helpful to "refresh" the task list in the
     Client.

3. In the client---as a lead marker---toggle "show all tasks".  You
   can look at *all* tasks for the current question and version.
   In current development is the ability reassign any tasks to
   yourself, which will allow you to further edit the annotations.



Scanning
--------

Do I need to carefully pick out just the right pages when rescanning a bundle?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

It depends.  Suppose we have scanned "BundleA1" but have some page
misfeeds (e.g., pages stuck together) or pages that somehow do not
appear correctly in the resulting PDF file.  If the bundle has been
uploaded to the staging area but not pushed, we can simply rescan the
whole bundle.  Use a new bundle name, say "BundleA1-rescan".  Now
process as usual.

On the other hand, If you're already pushed an incomplete bundle, it
might be easier to rescan only the appropriate pages, to avoid needing
to discard the colliding pages.



Server administration
---------------------

What are the most important files to backup in case of server failure?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Before grading begins, the important files are the specification
`.toml`, the version-map .csv`, and the source PDF files of the
assessment, because the server can be :ref:`reconstructed from these
files <clone_server>`.

After grading begins, it obviously becomes much harder: one typically
needs the entire database and media directory.
TODO: add documentation on backing up a Plom server.




Legacy: How can I get past SSL certificate errors?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

E.g.,::

    SSLError(SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed certificate (_ssl.c:997)'))

Or ``plom-create status`` might be showing you::

    [!] insecure connection (self-signed or invalid SSL cert)

SSL is used to securely verify the identity of the server you are
connecting too.
If you're only experimenting, you can bypass the checks by setting a
special environment variable, e.g., in bash:
``export PLOM_NO_SSL_VERIFY=1``.
The :ref:`desktop Plom Client <plom-client>` offers a mechanism to
ignore SSL errors (at you and your users' own risks).

*For production servers, you'll need to investigate how to setup SSL
certificates.*


Ok, how do I setup SSL certificates?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

`LetsEncrypt <https://letsencrypt.org>`_ is probably a good place to start.


.. _clone_server:

How can I clone a server so that it accepts scans intended for another server?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You need four things from the existing server: the server specification `.toml` file,
the "public code" (which is written into the QR codes),
the question-version map `.csv`, and the classlist.

.. caution::
    One should be very carefully doing this sort of thing: the
    "public code" exists to make it difficult to accidentally upload
    papers to the wrong server.  This question shows you how to defeat
    that mechanism.

Use the saved `.toml` and the saved version map `.csv` to provision
the new server.
You'll need to manually enter the "public code" you noted above.
If prenaming, ensure you use the same settings as before.
Continue provisioning the server, creating the database etc.  No need
to physically print the papers (as they should be identical!)  You
should then be able to upload your scans (produced on the original
server) to this new server.

.. note::
    If you do not have access to your old server, you can carefully
    manually reconstruct the specification.
    You can extract the "public code" from the QR codes of the
    printed pages (e.g., using a QR app on your phone).
    See the source code ``plom/tpv_utils.py`` for hints on
    interpreting the results.
    If the server was multi-versioned, you're in trouble: in
    principle as of 2025, you could write a script to
    extract the version map from the scans themselves.


I have only one version, can I skip the version map `.csv` above?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In principle, yes, but you'll need to be careful to produce (at least)
the same paper numbers that you had before.
You'll also want to be careful with any prenaming.



How can I clone a legacy server?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Similar to :ref:`clone_server`, you need to download the ``.toml``
specification and the version-map, using the command-line legacy
management tools.

Can I scan and mark papers without QR codes on my Plom server?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This can be accomplished by treating these papers as "double-printed", the solution
is identical to the one offered for
`I messed up by double-printing some papers, now I have collisions`_:
  1. Scan the paper with the missing QR codes
  2. "discard" each of the pages belonging to the paper, then manually cast each of
     the pages to the corresponding pages of an **unused** paper (e.g. paper number 20).
  3. Push this paper to the server!

Keep in mind which unused paper you casted to will no longer be unused (i.e. you
must cast to a different unused paper each time you do this).

"I don't have an unused paper?" - that's unfortunate, see
`I messed up by double-printing and I'm using multiple versions`_

Of course, one should consider whether these papers should be marked using Plom.
If you have a large number of papers without QR codes, you might consider marking
them by hand and avoid tediously casting all pages across tens or hundreds of papers.

I messed up by double-scanning some papers and uploading and now I have collisions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If there are only collisions in your bundle, you can remove the bundle
without pushing it.

If there are some non-colliding pages in the bundle that you want to
keep, one approach might be to find those papers in the physical
bundle and rescan them.  The other option is to discard all the
colliding pages, so that you can push the remaining non-colliding
pages.


I messed up by *double-printing* some papers, now I have collisions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is a serious problem which you should avoid getting into...
If two students have written on (say) paper number 20, then you will
get collisions at upload time.

Let's suppose the scanned bundles are contiguous: that is, the two
paper number 20s are not interleaved in the scanning process.  For
example, they are in two separate bundles.  (If this is not so, have
a little cry and then consider sorting and rescanning?)

At this point you have paper 20 "A" scanned into the system.  Now
upload paper 20 "B".  You will not be able to push it because of the
collisions.

Next: if you have only one version, you can discard all the pages
then convert to known pages of some **unused**
paper number, say 107 (assuming you have spares; if not see below).


.. _dblprint_multiver:

I messed up by double-printing and I'm using *multiple versions*
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is similar to the above but we cannot simply push paper number
20 "B" into a spare unused paper slot (say 107).  This is because
paper number 107 will have different versions than 20.

We need to instantiate a new row of the database using the versions of
paper number 20.  Extract the version map.  Use the relevant values to
make a ``csv`` file with one row, using a completely new paper number:
say 1020.  Next we
need :ref:`command line access to the server <cmdline_in_container>`.

Using the command line access, use ``django-command plom-qvmap`` and
see the ``append`` option.  Now you should be able to assign the
conflicting work to paper 1020.

If the command line access is not feasible, another option is:

  1. Clone the server from the pre-scanning state (see question
     elsewhere).
  2. Update the duplicated papers into the 2nd server.
  3. Have your grading team grade on both (alternatively, have them
     do most of the grading on Server 1, then download the rubrics
     and push those rubrics to Server 2.


...I have many reused the same paper **many** times
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Read the above answers.  Suppose Paper 20 has been reused 100 times;
too many to contemplate manual work and you want to write a _script_
to deal with the reassignment of these onto (newly created) Papers 400
to 499.
First :ref:`append the version map <dblprint_multiver>` to make 100
new rows with the same versions as Paper 20.
Suppose all 100 copies of Paper 20 are in scanned in ``bundleA``.
Next, using :ref:`command-line access <cmdline_in_container>`, you
can perform commands such as::

    python3 manage.py plom_staging_bundles status
    python3 manage.py plom_staging_bundles pages bunddleA
    python3 manage.py plom_staging_discard manager bundleA 1
    python3 manage.py plom_staging_knowify bundleA assign -u manager -i 1 -p 100 -g 1
    python3 manage.py plom_staging_discard manager bundleA 2
    python3 manage.py plom_staging_knowify bundleA assign -u manager -i 2 -p 100 -g 2
    ...

This assumes the papers are in order: you'll want to check that
against the output of
``python3 manage.py plom_staging_bundles pages bunddleA``,
perhaps scraping the output of that command to decide more robustly
where to send each page.


.. _cmdline_in_container:

How do I run the command-line tools in my Docker/Podman container?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You will first need ``ssh`` access to the host machine: talk to your sysadmin.

Next, find the name of the container.  At UBC, in Nov 2024, these are
organized by term and port number, for example
``plom2024w141234_plom_1`` is served on port 41234.

Using the name of the container, you can run commands directly::

    docker exec -it plom2024w141234_plom_1 bash -c "DJANGO_SETTINGS_MODULE=plom_server.settings django-admin plom_download_marks_csv; ls"

    docker cp plom2024w141234_plom_1:/exam/marks.csv .

You can also get an interactive ``bash`` prompt::

    docker exec -it plom2024w141234_plom_1 bash



Changing the spec later
-----------------------

Students have already written my assessment, can I split one of my questions up?  Can I merge two questions?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Yes, although there is some work.  Keep the old server up for now
("Server A").  Make a new server ("Server B").  Hack the spec to
duplicate the public code from A to B (see instructions above for
"resetting a server to the pre-named state").  Change the spec as you
wish (with in the constraints of the papers you already have).  If you
have mono-versioned test, nothing else is required: upload the papers
to Server B.

If you have a multiversioned test, its a bit harder:
  1. extract the version map from Server A.
  2. modify that version map for your new paper layout.  For example,
     if you are splitting "Q5" (physically laid out as 5(a) on Page 11
     and 5(b) on Page 12) into separate "Q5" and "Q6", then they must
     both have the same version as the original Q5.
  3. upload that version map to Server B when making the database.
  4. Upload the papers to Server B.


I have already uploaded scans, can I split one of my questions up?  Can I merge two questions?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Not easily.  Currently we would suggest re-uploading to a new server
following the instructions above.
