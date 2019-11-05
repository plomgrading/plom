<!--
__author__ = "Andrew Rechnitzer, Colin B Macdonald, Elyse Yeager, Vinayak Vatsal"
__copyright__ = "Copyright (C) 2018-9 Andrew Rechnitzer"
__license__ = "GFDL"
 -->

# Returning papers

## Canvas limitations

Canvas does not allow us to upload pdf files or even strings.  Instead we:

  * upload pdf files to another webserver
  * provide users with a secret code (hashed from their student number)
  * students visit a URL, enter their student number and the secret code.


## Renaming PDF files

  * Set the `SALTSTR` in `utils.py`.  TODO: move?
  * call `10_prepare_coded_return.py`
  * upload the resulting `codedReturn` directory to a webserver.
  * students will visit that directory, see `index.html` which prompts
    them for the student number and their "return code".

Note: `SALTSTR` should be set once per course so that multiple midterms
can be returned with the same code.


## Uploading grades

  * Before starting, make sure your grade posting policy in Canvas is set
    to "manual".
  * The relevant switch/tab is under the gear icon in the top-right corner
    of the gradebook.
  * Go to Canvas, create a column with appropriate name for your test.

      1.  Suppose that name is "Test 2".
      2.  See details below how to do this.

  * Edit `11_write_to_canvas_spreadsheet` to specify "Test 2 (".  Note the
    open parenthesis.  TODO: this is obviously not ideal!


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
          changes to `11_....py`).

  * As of autumn 2019 Canvas gradebook doesn't use "mute"; instead we set
    the "Grade Posting Policy" to "Manual", as noted above.  One can
    doublecheck this under the "..." menu in the relevant column header.

  * Export the gradebook by clicking on "export".  Save the resulting
    csv file as `canvas_from_export.csv` and move it `finishing/`.
    Possibly need to select "All Sections".


## Generating the files

   * Run `11_write_to_canvas_spreadsheet.py` to create two csv files:

       1. `canvas_return_codes_to_import.csv`.
       2. `canvas_grades_to_import.csv`.

   * Upload/Import one or both of these files back to Canvas.

   * If you kept the same salt, you may be able to upload just the
     grades.

   * Note: This script requires python 3.6 (on Ubuntu 16.04 call python3.6 explicity)


## Sharing with students

  * Make a Canvas announcement or similar explaing what they need
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
