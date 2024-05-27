# Thoughts on building exams

## Words
* Administrator = probably the IT supervisor person who ensures that the system is up and running.

* Instructor = typically the instructor in charge of the subject (rather than the instructor of an individual section of the subject). This person is in charge of the constructing, running, marking and returning the assessment.

* TA = individual who will mark questions.

* Exam = refers to the whole project. A midterm-test, or quiz, or final-exam, the associated specifications and marking processes etc etc, will be an "Exam" in this context.

* Exam-name = a name for the piece of assessment. An alphanumeric string with no spaces(?). For example,  "m101mt1" meaning "Mathematics101 midterm 1". This will be used by the system to ensure scans from one project/exam are not uploaded into another project/exam.

* Test = the actual piece of assessment (midterm / quiz / final) and not all the associated infrastructure and stuff. This is perhaps what we typically think of when we think of a test - the questions and papers etc.

* Page = One face of one sheet of paper when printed. Each test will consist of the same number of pages.

* ID-page = page(s) on which student will write their name / student number / section number / course number etc etc. This will typically (but not always) be the front page of the test.

* DNM-page = "do not mark"-page = these are pages which will not be marked under any circumstances. Typically these might be "Instructions to students" or "Formula sheet" or even just "Scrap paper". **Not yet implemented in Plom but would be good to add**

* Question = A group of one or more contiguous pages. When grouped together this is what an individual TA will mark (as a whole). Typically (but not always) these pages will form a single question on the test/quiz. Eg - a question might contain several parts which will be spread out across several pages. Similarly, one question might require a non-trivial calculation and the instructor might place the question itself on one page and supply another page (or two or three or...) for the student's workings.

* Source-version = The instructor (with help) will create several versions of the test. These source versions should all have the same structure (more on this below). The paper put in front of a student is constructed from one **or more** source versions according to the blueprint (more below). We might construct N versions of the test which **must** all have the structure, though the details of individual questions will (should) differ. For example we might construct 3 versions of a test having the following structure:

| Question/Type |Page numbers | Marks | Comments |
|---------------|-------------|-------|----------|
| ID | 1 | 0 | Name/ID goes here |
| DNM | 2 | 0 | Instructions + Formulas|
| Question 1 | 3,4,5 | 12 | Multi-part question |
| Question 2 | 6 | 5 | All on one page|
| Question 3 | 7,8 |10| Two-part question|
| Question 4 | 9,10| 8 | Room for calculation |


* Version = One of the source versions. Typically we will cut the source versions up into individual questions and then recombine them. Because of this it is critical that all tests have the same structure.


* Paper = the generated pdf/paper-copy that is put in front of an individual student for assessment. Traditionally the papers in an exam would all be printed from the same PDF. In Plom all tests are necessarily different. Since the system needs to be able to reconstruct scans, each page of each paper needs a unique identifier (qt-code) and so each paper will be a separate PDF.



## Specification or Blueprint
We'll define the blueprint via an example.

* Say the instructor builds 3 source versions of the test (call them A,B,C) with the following structure:

| Question/Type |Page numbers | Marks | Comments |
|---------------|-------------|-------|----------|
| ID | 1 | 0 | Name/ID goes here |
| DNM | 2 | 0 | Instructions + Formulas|
| Question 1 | 3,4,5 | 12 | Multi-part question |
| Question 2 | 6 | 5 | All on one page|
| Question 3 | 7,8 |10| Two-part question|
| Question 4 | 9,10| 8 | Room for calculation |

* When building individual papers the Plom system will pull questions from the different versions and glue them together. So we might have a sequence of papers

|Question| Paper 1 | Paper 2 | Paper 3 | Paper 4 |
|--------|---------|---------|---------|---------|
| ID | A | A | A | A |
| DNM | A | A | A |A |
|Q1 | A | C | B |A |
|Q2 | C | B | B |A |
|Q3 | B |A  | C |C |
|Q4 | A |A |A |A |

* Notice that the above indicates that
  * All papers have the same ID-page and same Instruction/Formula page - those from Version A of the test.
  * Paper 1 has Version-A of Q1, Version-C of Q2, Version-B of Q3 and Version-A of Q4. So it is constructed by gluing together pp1,2,3,4,5 from Version A, p6 from Version C, pp7,8 from Version B, and pp9,10 from Version A.
  * Paper 2 has Version-C of Q1, Version-B of Q2, and Q3 and Q4 from  Version-A So it is constructed by gluing together pp1,2 from Version A, pp3,4,5 from Version C, p6 from Version B, pp7,8,9,10 from Version A.
  * etc.

* Notice that
  * the ID-page and DNM pages are fixed in all papers,
  * the Q1 version is chosen randomly in each paper,
  * the Q2 version is chosen randomly in each paper,
  * the Q3 version is chosen randomly in each paper, and
  * the Q4 version is fixed for all paper.

* The blueprint must specify all of the above to the Plom system.

So the blueprint needs:
* A name for the exam.
* How many versions and a PDF for each version
* How many pages
* Location of ID-page(s).
* Location of the "do not mark" (DNM) pages
* For each question:
  * Which pages - must be contiguous
  * How many marks
  * How should they be chosen from the versions:
     * Fixed (all will be version A)
     * Random (selected randomly from versions)
     * Cycle (A-B-C-..-A-B-C..) **we should remove this option - or deprecate it**
* How many papers to produce


## After blueprint established
* Instructor needs to be able to review and edit the blueprint.
* Once instructor verifies the blueprint - paper production is in 2 steps.
  * System produces a list of papers to produce. Each entry tells the system how to grab pages from the source versions to construct the papers. (Here we have labelled version by capital letters, but should be integers 1,2,3 etc.) In the example above we'd have
    * 1: [A,A,A,A,A,C,B,B,A,A]
    * 2: [A,A,C,C,C,B,A,A,A,A]
    * 3: [A,A,B,B,B,B,C,C,A,A]

  * Once production list is written the system can then glue pages together into papers and write them to an appropriate directory.

* This separation means that it is easier to change the final number of papers.
  * For example, if the instructor decides they don't need quite so many they can just not print all the produced PDFs.
  * If the instructor needs more papers then the system should be able to append to the production-list and so not mess up the random choices of papers that have already been produced (and perhaps printed).

* Notice that being able to alter the number of tests is quite an important feature **not yet implemented**. If the instructor realises that they have undercounted by 10 papers (eg - they forgot about an extra sitting?) then they shouldn't have to redo everything from scratch.

* If the instructor needs to alter the blueprint then it will invalidate the production list and also any papers that have been printed. Warnings should be given before the instructor can go back and edit.

## Construction of papers
* Each page of each paper should be marked with:
  * A triangle in the staple-corner which will contain the exam-name. Human readable. Since the page is (typically) stapled at the top-left, this will be on the top-left on odd-numbered pages and top-right on even-numbered pages.

  * A rectangle in the top-centre containing the number of the test and the page - for example "0073.4" meaning paper-73, page-4.  Human readable. This helps for manual sorting and also identification of mis-scanned pages.

  * A QR-code that encodes the TPV-code of the page. At present this is encoded as the string "tXXXXpYYvZ" where XXXX is the number of the test (zero-padded), YY is the page-number (zero padded) and Z indicates from which source-version the page was pulled. This should be placed on the opposite side of the page from the staple-corner. So top-right on odd-numbered pages and top-left on even-numbered pages.

  * In the current implementation the above QR code is also stamped on the same side of the page but at the bottom. A third QR-code containing the name of the test is stamped in the last corner.

  * **Improvement that needs testing** replace the current 3 qr-codes with a single qr-code at the top non-staple corner of the form "tXXXXpYYvZnS" where
  "S" is now the test name as a string. Some care is required on restricting the name of the test to be of reasonably short length and only contain alphanumeric. Otherwise the qr-code might need to be too large. It would be good to keep it a reasonable size.

* At present the pdf-manipulation (gluing and stamping) is done using pymupdf. However we have found it to be a bit delicate (errors on certain source pdfs), so perhaps it would be better to see if it could all be done using imagemagick?

* Also need to look into internationalisation - a4 paper? non-asci test names?

## ID-page
* We have coded up basic hand-written student-number recognition which works surprisingly well.

* This requires that the ID page have a standard template box (of fixed dimensions). The box contains room for entering name, section and 8 small squares for students to enter their ID-number. There will be internationalisation issues around ID-number length.

* Thought requires as to how to get the instructor to incorporate this standard box template into their tests. Perhaps we could require that the one half of the ID-page be left blank and then the system could stamp the template onto it.

* This might also give a (future) mechanism for generating personalised tests which already have the student's name and number printed on them.


## Printing
* After blueprint and then production, the system will have a set of PDFs sitting in a directory.

* Each PDF should be named "paper_xxxx.pdf" where xxxx is a zero-padded integer.
  * Currently this starts with "paper_0001.pdf"
  * Should this be changed to start with "paper_0000.pdf" ?

* Instructor should be able download a zip (tgz?) of the papers. The zip should expand into a directory (named by the exam-name).

* Instructor should also be able to download individual papers.

* There is not a need for the system to interface directly with a printing service.
