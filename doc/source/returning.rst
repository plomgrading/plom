.. Plom documentation
   Copyright 2020 Andrew Rechnitzer
   Copyright 2020-2022 Colin B. Macdonald
   SPDX-License-Identifier: AGPL-3.0-or-later


Returning Work to Students
==========================

Once marking is done (or very nearly done) it is time to reassemble the papers, build the spreadsheet and return results to students. But before that we need to check that everything is done so that we can assign any remaining tasks. We will use `plom-finish` to do this. Note that this can only be run by "manager".

## Is everything done?
Once we are mopping up the last few questions, and it becomes very important to know what is tasks are left to do.
One way to access this information is through the [manager-tools]({% link docs/walkthrough/manager.md %}), but a simpler way of getting a quick overview is to use the `plom-finish` command:
```
$ plom-finish status
Please enter the 'manager' password:
*********************
** Completion data **
Produced papers: 20
Scanned papers: 20 (currently)
Completed papers: 1–20
Identified papers: 1–20
Totalled papers: 1–20
Number of papers with 0 questions marked = 0. Tests numbers =
Number of papers with 1 questions marked = 0. Tests numbers =
Number of papers with 2 questions marked = 0. Tests numbers =
Number of papers with 3 questions marked = 20. Tests numbers = 1–20
20 of 20 complete
```
This shows that everything is actually done.


## Spreadsheets
Now that everything is done, Plom can build a [CSV spreadsheet](https://en.wikipedia.org/wiki/Comma-separated_values) for us.
```
$ plom-finish csv
Please enter the 'manager' password:
>>> Warning <<<
This script currently outputs all scanned papers whether or not they have been marked completely.
Marks written to "marks.csv"
```
Please do note the warning --- Plom will include all scanned papers in this sheet. While you can run this at any stage in the marking process, the sheet will not be complete until the marking is all done.

The sheet is saved as `marks.csv` and is human-readible. Take a quick look at the first few rows:

| StudentID | StudentName | TestNumber | Question 1 Mark | Question 2 Mark | Question 3 Mark | Total | Question 1 Version | Question 2 Version | Question 3 Version | Warnings|
|--------|------|-|-|-|-|
| 67719396 | Dickey, Rachel| 	1	| 1	| 0	| 5	| 6	| 1	| 1	| 2	| |
| 82911040 | Hancock, Norman| 2	| 9	| 5	| 1	| 15	| 2	| 1	| 2	| |

It contains the students ID and name, the number of the test-paper they wrote, their marks for each question, and the total. It also includes the versions of each question and a "Warnings" column. This last one will warn you:
* `[unidentified]`: this test has not yet been identified
* `[unmarked]`: at least one question on this test is unmarked
* `[no ID]`: no ID given on test, but some questions were answered
* `[blank ID]`: no ID was given was given and test is blank

It should not be too difficult to tweak the resulting spreadsheet for upload into your favourite LMS (or at least the one you have to use).

## Reassembly
Once everything is IDd and marked and you've done any necessary mopping up and reviewing it is time to reassemble all the annotated page-images into papers complete with simple cover-pages.
```
$ plom-finish reassemble
Please enter the "manager" password:
Reassembling 20 papers...
100%|████████████████████████████████████████████████████████| 20/20 [00:04<00:00,  4.16it/s]
```
Note that for a long paper and a large class this could take some time.
The resulting papers now reside in `reassembled`. Each is named `<testName>_<studentID>.pdf` where the `<testName>` is the short name that you gave your test in the [specification]({% link docs/walkthrough/create.md %}#namesAndNumbers) and `<studentID>` is the ID-number of the student. Here is a sample paper (very obviously not real data, nor real annotations)

|[<img src="/images/mockup-0.png">](/images/mockup-0.png)|[<img src="/images/mockup-1.png">](/images/mockup-1.png)|[<img src="/images/mockup-2.png">](/images/mockup-2.png)|[<img src="/images/mockup-3.png">](/images/mockup-3.png)|[<img src="/images/mockup-4.png">](/images/mockup-4.png)|[<img src="/images/mockup-5.png">](/images/mockup-5.png)|

You can also prepare individual solutions: see `plom-finish solutions --help`.

## Return
There are various ways to return PDFs to your students.

### Return via Canvas
As of Autumn 2021, we have been using an experimental code `contrib/plom-push-to-canvas.py` to push PDFs, solutions and grades back to the Canvas LMS.

Website return
--------------

See `plom-finish webpage --help` which has various options to prepare a webpage of non-predictable file names, and leaves you the problem of returning a "secret code" (from `return_codes.csv`) to each student.


Return to the Canvas LMS
------------------------

Follow instructions above to "reassemble" the papers, make the `marks.csv`
and optionally the individualized solutions.

Make an "API key" for your Canvas account.

- Login to Canvas and click on "Account" (your picture in the top-left).
- Settings
- Click on ``+ New Access Token``.  The purpose can be "Plom upload" (or
  whatever you want) and you can set it to expire in a day or two.
- Copy the token, something like ``11224~AABBCCDDEEFF``, keep it for later
  steps.

Also in Canvas, create column "Midterm 1" (or whatever) in Canvas with the
correct number of points.

Publish the columm but set to manual release.

Get the "contrib script" called `plom-push-to-canvas.py`.  You might find it
in a directory like `/home/<user>/.local/share/plom/contrib`.  You could also
get a copy from the Plom source code.

Instructions are given at the top of script: basically you need to put the
Canvas API key into a particular file.  Instructions are also given for running
it.  Try ``./plom-push-to-canvas.py --help`` for more info.  Use the
``--dry-run`` mode first!

Go back to Canvas and examine a few papers: double check the scores.
Double check some of the PDF files.  Unfortunately, you'll probably hit
`this Canvas bug <https://github.com/instructure/canvas-lms/issues/1886>`_
(which effects instructors not students).  Workarounds are offered in the bug report.

Once happy, release the grades on Canvas.


Technical docs
--------------

* The command-line tool :doc:`plom-finish` is the current front-end
  for most tasks related to returning work.

* For scripting or other advanced usage, you can ``import plom.finish``
  in your own Python code.  See :doc:`module-plom-finish`.
