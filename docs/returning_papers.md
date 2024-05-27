<!--
__author__ = "Andrew Rechnitzer, Colin B Macdonald, Elyse Yeager, Vinayak Vatsal"
__copyright__ = "Copyright (C) 2018-2018 Andrew Rechnitzer"
__license__ = "GFDL"
 -->

# Returning papers via the Canvas API

Oct 2020: we're in the process of a adopting a solution partially based
on the Canvas API.  Some of the info below is out of date.

Under this new workflow, ignore everything about "return codes" below.
We still use the `share/plom/contrib` script `plom-write_grades_to_canvas_csv.py`
to create `canvas_grades_to_import.csv`.

- - - -

# Returning papers via Canvas using secret codes

## Canvas limitations

Canvas does not allow us to upload pdf files or even strings.  Instead we:

  * upload pdf files to another webserver
  * provide students with a random secret code
  * students visit a URL, enter their student number and the secret code.

Start by calling `plom-finish webpage`.

  * upload the resulting `codedReturn` directory to a webserver.
  * students will visit that directory, see `index.html` which prompts
    them for the student number and their "return code".

## Uploading grades

  * Before starting, make sure your Grade Posting Policy in Canvas is set
    to "manual".
  * The relevant switch/tab is under the gear icon in the top-right corner
    of the gradebook.
  * TODO: this is a **global setting**.  It will break automatic updates of
    Webwork assignment grades.  You'll need to manually set those each back
    to automatic.  TODO: as of Oct 2020: I'm experimenting with leaving
    the global setting as "Automatic", then creating my "Test 2" column
    and immediately setting its local policy to "Manual".
  * Go to Canvas, create a column with appropriate name for your test.

      1.  Suppose that name is "Test 2".
      2.  See details below how to do this.


## Uploading the secret "return code" to Canvas

We have a secret code for each student.  We want to upload these numbers to Canvas.

  * Go to Canvas, add a new `return code` column.  Note the lack of
    capitalization.  The column must be called `return code` exactly.

      1.  Create new assignment under Assignments.
      2.  Made it a new group.  The name doesn't matter.
      3.  Check "do not count towards the grade"
      4.  Set the maximum points to `999999999999` (twelve nines).
          This might look slightly different, canvas likes to use commas.
      5.  Edit the assignment to say something non-scary so no one
          thinks its part of their score.
      6.  Publish, and check for the icon showing you that it's hidden.
      7.  Again: the name *must* be `return code` (or you will need to make
          changes to the Plom source).

  * As of autumn 2019 Canvas gradebook doesn't use "mute"; instead we set
    the "Grade Posting Policy" to "Manual", as noted above.  One can
    doublecheck this under the "..." menu in the relevant column header.

  * Export the gradebook by clicking on "export".  Save the resulting
    csv file as `canvas_from_export.csv` and move it `finishing/`.
    Possibly need to select "All Sections".


## Generating the files

   * Find some utilities in the `share/plom/contrib` directory.

       1. run `plom-return_codes_to_canvas_csv.py`
       2. this creates `canvas_return_codes_to_import.csv`.
       3. run `plom-write_grades_to_canvas_csv.py`
       4. this creates `canvas_grades_to_import.csv`.

   * Upload/Import one or both of these files back to Canvas.


## Sharing with students

  * Make a Canvas announcement or similar explaining what they need
    to do: for example:

    > Midterm return link: https://amcweb.math.ubc.ca/~your/path
    >
    > You can obtain your Midterm by visiting the link given above.  You
    > will need your student number and your 12-digit "return code" from
    > the Canvas grade sheet.
    >
    > If you've reviewed the solutions and would like someone to reconsider
    > your grade, please fill out the Grade Change Request Form at
    > SOME URL.

  * Make sure you give them a https:// link.  Double check this.

  * Post the URL somewhere secure like Canvas, not on the open
    internet.  We want to minimize brute-force attempts to get
    other peoples' exams.

  * Make sure the "return code" and the test are visible to students.  In
    older Canvas you would "unmute" them.  Nowadays, something like:

      1. Publish the return code.
      2. Publish the test marks.

    TODO: didn't we already "publish"?  How does this make them visible?


## FAQs

"Can I reuse the return code for multiple tests?"
: Probably.  Official support to follow.


"Canvas put commas in my return codes."
: So it does, this is no problem.  Students do *not* need to remove them.

"Microsoft Excel displays 12-digit return codes in scientific notation."
: If you look at the raw .csv with a text editor, they are indeed integers.
We don't recommend saving that file with Excel; if you want to spot-check
before uploading to Canvas, use a text editor.  In theory, the values are
less than `flintmax` so a round-trip through floating point should be
harmless.

"Where can I host the return files?"
: UBC-specific answer: put stuff on `amcweb`.  TODO: Ask IT if you need
help getting access to `amcweb`?  When logged into my VM, the path is
`/zfs/users/cbm/www`.  This is different than when logged into pascal or
hypatia.

"12 digits don't work any more in 2020!"
: perhaps Canvas has changed something?  We're probably moving away from
this mode of return.  TODO: update these documents.
