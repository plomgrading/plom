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


## Uploading the secret "return code" to Canvas

We have a secret code for each student.  We want to upload these numbers to Canvas.

  * Go to Canvas, add a new "return code" column.  TODO: I don't recall
    the exact steps, please update with step-by-step instructions...

      1.  Create new assignment or maybe somethin in gradebook
      2.  Set it to not count towards their grade
      3.  Set the maximum score to `99999`.
      4.  The name *must* be `return code` (or you will need to make
          changes to `11_....py`).

   * Export the gradebook by clicking on "export".  Save the resulting csv
     file as `canvas_from_export.csv` and move it `finishing/`

   * Run `11_write_to_canvas_spreadsheet.py`: this will create
     `canvas_to_import.csv`.

   * Upload/Import `canvas_to_import.csv` back to Canvas.


## Uploading grades to Canvas

We don't do this for you (yet).  You probably can put the grades from
`testMarks.csv` into `canvas_to_import.csv` before uploading, but this
is not well testing nor automated.
