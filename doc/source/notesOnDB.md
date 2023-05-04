# Explanation of the Plom database

A hack at trying to make some notes / questions on the database for plom.

This document tries to explain the structure of the database in `plom/db/examDB.py`.

WARNING: it may be out of date as it was last modified in 2021.


## The tables in the Plom database

### User
Who is allowed to do things in Plom - including some higher-authority actors, like the "manage" and "HAL" (who does some automatic tasks for us).

* name = user's login.
* enabled = whether or not the user is allowed to use plom currently. We want this so that we can turn off access to most users after marking is done but before review and finishing.
* password = a hash of password for comparison
* token = the current authentication token used for validating requests made by clients.
* lastActivity = when did the user last do something
* lastAction = what did the user last do (not too low-level)

### Bundle
This represents a PDF of images. ie - when 'scanner' uploads all the images from a given PDF, the DB first creates a 'bundle' and all those images will point at that bundle. The main use for this at the present is to make sure that 'scanner' does not attempt to upload the same PDF multiple times. (ie we can check name and md5sum to make sure of this)

* name = the name of the original PDF that the bundle of images came from (or similar, eg spaces replaced by underscores, that sort of thing)
* md5sum = the md5sum of the original PDF that this came from.

Note that when we do upload sanity checks we want to upload either
* a new bundle
* an existing bundle where the name **and** md5sum match exactly - this can happen when, for example, separately uploading the unknown pages of a bundle, or continuing an interrupted upload (such as after a crash).

but definitely do not want to upload when
* the name matches and existing bundle but the md5sum does not - this is bad file hygiene.
* the md5sum matches but the name does not - this is, again, bad file hygiene.

### Image
Storing both uploaded page-images as well as images annotated by clients.

* originalName = if came from an uploaded image, what was name of that image file
* fileName = the name of the file in the local (ie accessible to server) file system.
* md5sum = to check for duplication
* bundle = which PDF bundle did it come from originally
* bundle_order = the page number within the PDF from which the image came.

### Test
The overarching class that represents 1 whole paper. The main things it has to encode are the number of that testpaper and a bunch of boolean flags telling us what stage of marking it is at (see below).

* testNumber = each separate paper has a unique numerical ID - which is encoded in the QR-codes that get stamped on it. This need not be the same as the auto-generated database ID for this object (but hopefully is).
* used = was any part of this test actually scanned - ie we typically produce more test-papers than we need, so not all end up being written on and being submitted.
* scanned = has the whole test been scanned in.
* identified = have we associated a student to this paper (either automatically on test generation (ie we print name on the front), or by a human reading the name and ID number).
* marked = has every question been graded?
* recentUpload = has a new pageimage been uploaded to this test - this flag essentially tells "hey check if any questions have new pages and if so erase any annotations and restart"

### Group
This is a way of grouping together a set of page-images (hence the name). These are sub-classed according to what those pages represent - questions, ID-pages (where students write their ID), or Do-Not-Mark pages (for formula sheets and instructions).

* test = points to its parent "test"
* gid = this is a human-readible identifier like:
  * i0007 = the set of ID pages from test 7
  * d0013 = the set of do-not-mark pages from test 13
  * q0011g3 = question 3 from test 11. (note this may change to 'm0011q3' in future)
* groupType = "i", "d" or "q"  # to distinguish between ID, DNM, and question groups
* queuePosition = this is for future use. Later we want to be able to change the priority of tasks, and in particular, defer tasks until later.
* scanned = has the group of pages be scanned completely (and so ready to be processed)
* recentUpload = has a new pageimage been uploaded to this group - this flag essentially tells "hey check if any questions have new pages and if so erase any annotations and restart"


There are 3 sub-types of groups that we need.
#### IDGroup
This stores the name and ID-number of the student who wrote the given test. At the same time it represents the "task" of identifying who wrote the given test. That task will either be done automatically (by "HAL") or by a human. Consequently we also need a "status" for the IDGroup which tells us if the task is "ready", "out" or "done."
* test = points to its parent test.
* group = points to its parent group
* studentID = the ID of the student who wrote this test.
* studentName = the name of the student who wrote this test.
* user = points to the user who did the identifying, or the user who has grabbed the "task" of identifying this paper.
* status = one of
    * blank if this is not yet ready (ie not all pages scanned)
    * "ready" if pages are present but no one has claimed the task.
    * "out" if the task has been claimed by user, but not yet finished.
    * "done" if the task has been completed by the user.
* time = when was this last updated
* identified = has this been identified - slightly redundant but handy for doing queries.

Two notes:
  1. If we generate papers with names on them (ie - stamped in big letters on the front), then "HAL" will automatically identify papers for us.
  2. This object sits somewhat independent from our efforts to do automagical student ID reading (via buzzword compliant machine learning stuff). The automagical ID reading is done by a separate process and generates a list of "predicted" pairs of ["test number", "student ID"]. That list is sent to the client which makes the recommendation to the user who is running the client.

#### DNMGroup
This is basically a placeholder for completeness of the 3 types of grouping of pages. We don't do much with it.
* test = points to its parent test.
* group = points to its parent group

#### QGroup
Very similar to IDGroup, excepting that it now represents a group of papges constituting a question on the test. That question has a question-number (which we just call question) and a version (since we have multi-version tests).
* test = points to the parent test.
* group = points to the parent group
* question = what number question
* version = what version of that question
* user = who did the marking, or who has grabbed the "task" of marking this question on this test.
* status = similar to that of IDGroup
* marked = has this been marked or not. Again, redundant, but handy for queries.

#### Annotations
One thing we'd like to support in the future is having multiple people mark the same question of the same test (think careful double marking of a subset of questions to ensure consistency). We'd also like to have a record of what was done previously. Consequently a given QGroup is connected to multiple annotation objects.

* qgroup = points to the parent QGroup.
* user = who did / owns the annotation
* image = this is either blank or points to the image of the annotations
* edition = an order on the annotations for that particular question. We hope that in the future we can use this to see (for example) what changed if a user updates their marking. Further, we'd like a good review process and when the task changes ownership to a "reviewer", then they could look back at what was done before, etc etc.
* integrity_check = this is a random UUID that is created by the server whenever the underlying pages of that question are changed (ie on upload or when manager moves pages around, but not when the client moves things about). This is used as a way of checking if the underlying task has been changed by the manager while it is out with the client - this should not happen as the manager-client is not able to make changes to tasks that belong to a given user while that user is logged in. It **might** happen if homework uploads (for a given student/question) happen split over several bundles.
* plomFile = this points to a file which contains the annotations in a form that can be loaded by the annotator (think a hack version of svg). This allows us to go back to a previously marked question and keep going.
* mark = the numerical score given.
* markingTime = how long did the user spend marking. We keep this so that the manager can do some "load balancing" of users and tasks. ie - if a given question is quick to mark, then they could reassign users to slower questions.
* time = when was the question marked.
* tags = a free-form text field for user-created tagging. This is mostly for future work.

Note
* when sufficient pages are uploaded for a question the DB will create an initial annotation for that question. This will consist of the page-images and belong to "HAL".
* when the DB gives a question-marking task to a user it creates a new annotation from the previous one. Note that it does not immediately create links to the images, but instead passes the client the images in the previous annotation. When the client returns the annotated task it tells the DB which images it used and then the DB hooks them into the annotation. This allows the client to shuffle pages around reasonably simply.



## Where are the pages?
Notice that the above structure does not explain how images are connected to groups. This actually gets a little complicated due to the all the possibilities. Ideally, if everyone follows instructions, a single page will contain answers to only a single question (though, of course a single question might be over several pages). However, we need to allow for the possibility that a page (esp a student uploaded page) might contain answers for multiple questions.

So - first up, what are the different page-types, and then we'll explain how they are tied to Groups and Annotations.

Types of pages:

* TPage - this corresponds to a test-page. To be more precise, a page we'd get when giving physical test-papers to students which we then scan. Very structured. As opposed to homework. It points to an image and knows its test-number, page-number and some other stuff.

* HWPage - this corresponds to a page of student-uploaded homework (when each question is uploaded separately). It knows which student it belongs to (and so via some look-ups) it knows which test-number, which question, but it doesn't actually have a well-defined page-number, rather it only knows its "order" within the submission. This is because one student's HW response to a given question might be 2 pages, and another's might be 7. So it no longer makes sense to talk about page numbers like we do for "test pages".

* EXPage - an extra page - primarily for tests. Functionally similar to HWPages - they have an "order" but not a page number.

* UnknownPage - these are the most free-form, they do not know anything other than the image and their order within the submitted file. This is still a work-in-progress after Andrew futzed with the database structure.

* CollidingPage - these are included to handle the possibility that the user (somehow) has two pages trying to be the same test-page. The manager can then use the manager-client to decide which to keep. Simple scenarios =
  * user scans / uploads a given test page, realises its a bad scan, so scans/uploads again. The second upload will be a collision. This is a reasonable possibility.
  * someone screws up and uses the same test twice. ie - two students write identical tests. This is bad. The second upload will be collisions. Bad Bad bad. Do not let this happen.

* DiscardedPage - When we get rid of an image for whatever reason (eg - decide which of a colliding pair to keep, or get rid of an annotation, or decided that a given UnknownPage is actually a garbage scan) - then we move it to this class to keep track of it in some way.

### Linking pages to group

Since a given page can belong to several questions (eg a student writes the answer to a question where they shouldn't), we have 3 objects that link images to IDGroups, DNMGroups and Annotations (since a given question may have multiple annotations, that is where we link in images).  Consequently we have 3 sorts of linking objects: IDPage, DNMPage and APage.

#### IDPage and friends
The IDPage needs to connect an image to an IDGroup, but it also needs to know in what order those images should appear when displayed to the user. Hence
  * idgroup = points to the "parent" IDGroup
  * image = points to the "parent" image
  * order = in what order should the images be displayed to the user.

Notice the IDPage has two "parents" - I hope I've handled this structure correctly.

The DNMPage and APage are very similar except that instead of pointing to an IDGroup, they point to a DNMGroup and Annotation respectively.
