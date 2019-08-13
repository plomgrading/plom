<!--
__author__ = "Andrew Rechnitzer, Colin B Macdonald"
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

  * Go to Canvas, create a column with appropriate name for your test.

      1.  Suppose that name is "Test 2".
      2.  See details below how to do this.

  * Edit `11_write_to_canvas_spreadsheet` to specify "Test 2".
    TODO: this is obviously not ideal!


## Uploading the secret "return code" to Canvas

We have a secret code for each student.  We want to upload these numbers to Canvas.

  * Go to Canvas, add a new "return code" column

      1.  Create new assignment under Assignments.
      2.  Made it a new group.
      3.  Check "do not count towards the grade"
      3.  Set the maximum points to `999999999999` (twelve nines).
          This might look slightly different...
      4.  Edit the assignment to say something non-scary so no one
          thinks its part of their score.
      4.  Publish and Immediately mute it.
      5.  The name *must* be `return code` (or you will need to make
          changes to `11_....py`).

   * Export the gradebook by clicking on "export".  Save the resulting
     csv file as `canvas_from_export.csv` and move it `finishing/`.
     Possibly need to select "All Sections".


## Generated the files

   * Run `11_write_to_canvas_spreadsheet.py` to create two csv files:

       1. `canvas_return_codes_to_import.csv`.
       2. `canvas_grades_to_import.csv`.

   * Upload/Import one or both of these files back to Canvas.

   * If you kept the same salt, you may be able to upload just the
     grades.


## Sharing with students

   * Make a Canvas announcement or similar explaing what they need
     to do: TODO: add suggested text here:

   * Make sure you give them a https:// link.  Double check this.

   * Post the URL somewhere secure like Canvas, not on the open
     internet.  We want to minimize brute-force attempts to get
     other peoples' exams.

   * Unmute the return code.

   * Unmute the test.
