## Idea
* The manager produces (say) 4 versions of the test they want to give to their students (think crowded midterm situation). All versions must have the same structure since their pages will be mixed and matched to construct the tests the students see.

* The manager gives the test a name (alphanumeric, no spaces), so that the scans for this test don't get mixed up with the scans from another test (bitter experience tells me that this is a good idea).

* The manager specifies 4 versions, how many pages in the test, and how many tests are to be printed.

* These (say) 4 versions need to be put in the sourceVersions directory and called version1.pdf, version2.pdf etc.

* The manager needs to decide how to combine these versions to produce tests for the class.
  1. ID pages - these are the page(s) that the students fill in with their student number, name etc. Typically this is just the first page of a test. Maybe it includes the second page where all the instructions are given.
  2. PageGroups - the manager should specify which pages (after the id pages) should be grouped together. Typically these will be the pages for a single question. Eg - if a question has several parts of if the student might need a couple of pages for their working of a single question, then these will go together in a single group - and at the far end of the process they will be marked as one unit (as a group, not page by page)
  3. ID / Fixed / Cycle / Random - each pagegroup needs to be set to be one of these options.
   * The ID pages are set to "id", while the other pagegroups are set to one of fixed , cycle or random.
   * A pagegroup that is set to 'fixed' will be set as version 1 in all produced tests. ie - all students will get that pagegroup from version1.pdf
   * A pagegroup set to 'cycle' will cycle through the different versions. So the pagegroup in test 1 will get version 1, in test 2 is gets version 2, test 3 version 3, test 4 version 4, test 5 version 1 etc. ie test n gets version (n mod V)+1 - where V is the number of versions.
   * A pagegroup set to 'random' will be selected randomly from the available versions for each test.

* To do this, the manager hacks the 01_construct_a_specification file to enter the relevant data (a gui needs to be built). Then run 02_build_tests_from_specification to build the separate pdfs for each test (saved in the examsToPrint directory)

* After the exams are build as separate pdfs they can be printed and given to students. It is critical that each student get a separate pdf since every page produced has a unique QR code on it. If two students get a test from the same pdf, then their pages will get mixed up.

* Each page will be stamped with 3 QR codes. 1 at the top and 1 at the bottom is of the form tXpYvZ - where X= test number, Y=page number and Z=version number. There is a second QR code on the bottom to encode the name of the test. Note that having 1 code at the top and 2 at the bottom will allow us (later) to re-orient the pages in case they are scanned up-side-down.

* Also - we strongly recommend that the user produce extra tests - just in case of some contingency. It is much easier to produce extra PDFs at this stage rather than trying to produce extra ones later. (again learned through painful experience)

## Files
* testspecification.py = gives testSpec object. This object encodes all the information about the setting up and producing the tests. Also does basic tests for self-consistency.

* 01_construct_a_specification = a script (that at present the manager edits) that interacts with the test specification class to produce and save the specification in the resources directory
 * Note - always set id pages first. set page groups in order. id-pages are effectively pagegroup0, while the other pagegroups go from 1 onwards. This does make a few scripts a little awkward later since one has to avoid pagegroup0.
 * Note - the script saves the test specification as "testSpec.json" in the ../resources directory where it can be accessed by other scripts

* 02 build_tests_from_spec = a script to build the pdfs of the tests from the specifications given. No hacking required.
  * Note this stores data in the ../resources directory as "examsProduced.json" - this encodes test-by-test which version was used for each page.

* examsToBuild = a temp-ish directory that contains the latex files of the tests to be built (roughly speaking - just enough latex to load in the pdf pages of the source test versions and put the required QRcode stamps on them)

* examsToPrint = a directory where the built tests go. There is one per student.

* sourceVersions = the manager needs to put the original test pdfs in here. The code will then mix and match pages from these to build the tests printed for the students.
