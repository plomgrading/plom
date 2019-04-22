# Scanning and preparation for marking
We discuss here everything that happens after the assessment is collected from students and before the TAs start work.

## Preparation
* Papers from each sitting should be sorted into test-number order (ie the T of the TPV-code).
* Post-scan, keep the papers in order and also in their sitting-group.
* This sorting is to help in case there are any problems with scanned images - missing pages, poor scans etc.
* Save the PDFs from the scanner with sensible names - again we recommend good file hygiene.

## Upload of scans
* Almost always the scans will be PDFs. That being said the system should **in the future** be able to handle other formats.
* User should (perhaps?) be able to make a note with each uploaded PDF - something like "Section 101-part-2".
* User should also be able to download the PDF back from the system so they can check it.

## Processing scans 1
* PDF is split into individual pages - must be bitmaps.
* Each page is processed to make writing a little darker. Currently this is a simple gamma-shift (leaves white = white, but makes everything else darker).
* While the PDF-splitting is done in series, the image processing is piped through gnu-parallel to take advantage of multiple cores.
* Move processed PDF into an "alreadyProcessed" directory to avoid possible duplication.

## Processing scans 2
* Check dimensions of each page to make sure it is in portrait - rotate if not.
* Split page vertically into 5 equal pieces and run topmost and bottommost through zbarimg for qr-code decoding. Note that zbarim does not report the location of codes so splitting the page into pieces allows us to check if codes are at top or bottom of page.
* **Present behaviour** top-piece should have one qr-code giving the TGV-code of the page. The bottom-piece should have two qr-codes giving the TGV-code and the exam-name. If reversed then rotate page 180 degrees.
* **Future behaviour** top-piece should have one qr-code giving both TGV-code and name of exam. Bottom piece should contain no codes. Rotate page accordingly.
* If valid TGV and exam-name the rename image "tXXXXpYYvZ.png" where XXXX,YY,Z taken from the TGV and file in appropriate directory. The TGV should be recorded in an "exams-scanned" data-structure.
* If invalid then move page-image to a "problematicImage" subdirectory

## Problematic images
* There can be several reasons that a page-image is problematic:
  * Wrong exam - image is from a different piece of assessment (ie name is wrong). Should be filed accordingly (and automatically).
  * Mangled scan - the physical page didn't feed properly through the scanner and the resulting image cannot be read.
  * QR-codes cannot be read - perhaps printed poorly, student wrote over it (this happens!), dust on scanner, smudge etc etc.
  * Extra paper - student requested extra paper during the assessment, so this is a page which is valid but does not have any QR-codes on it. More on this below.
  * ????
* All problematic images (except those belonging to other exams) needs to be viewed by the instructor and
  * identified if the page-image is human-readible - ie instructor manually inputs the TGV-code of the page and puts page in correct orientation.
  * designated as extra paper for a given test/question.
  * discarded if too mangled.
* The manual-identifier script currently does this, but could do with improvement.

## Processing scans 3
* After all scans have been identified either by the system or by the instructor, we need to check if all papers are complete.
* Typically we will (and should) produce more papers than are needed, so many of the produced papers will not be found in the scans.
* A paper is incomplete if one or more, but not all of its pages are scanned.
* A paper will be complete if all its pages have been scanned.
  * This is a simple check of the "exams-scanned" data structure against the test-specification.
* A paper is unused if none of its pages are scanned.
  * Notice that there does not seem to be a simple way to detect the (hopefully extremely rare) possibility of missing all pages of a given used test.
* Report the list of completely-scanned papers to the instructor.
* Report the list of incomplete papers to the instructor.
  * If there are incomplete papers then the instructor will need to have the option of re-checking problematic images, and also of uploading new PDF-scans into the system and re-processing.

## Processing scans 4
* The completely scanned exams are still a collection of (appropriately named and filed) page images. Before marking they should be grouped together according to the exam blueprint.
* For example, if the blueprint says that pages 3,4,5 form question 1, then the system should tile (horizontally) those pages into a single image.
* The resulting page-groups should be named "tXXXXgYYvZ.png" where XXXX is the test number, YY is the question (or group) number and Z is the version.
* In this way a TPV-code becomes a TGV code. **Future?** call this a TQV?
* Files should then be placed in appropriate directories.

* After this grouping of pages, the system should look for any extra pages (see below) and those should be appended to the corresponding TGV. ie - tile the pages and extra pages for the question together.
* **Question?** does the grouping of extra pages have to be done after the grouping of (standard) pages? Or could this just be done in one step?
  * At present the handling of extra pages is done after - I think I was concerned about workflow. ie if the instructor finds that the system has correctly and completely identified almost all of the papers with only a few problematic scans, they might prefer to run the grouping-process in the background (as it were) while they manually ID the problematic images.

## Ready for marking?
* After all the papers have been scanned and grouped into questions, the system should be ready for the marking process to start.
* To what extent can the above run in parallel with marking? ie - if the instructor gets a big chunk of the papers scanned and processed, can marking start while the rest of the papers  are processed?

## Extra paper
* **Current behaviour** - extra paper given to students should have space for a student to write their name, ID, test-number, and question-number. Student should not use same sheet for multiple questions.
* **Future behaviour** - extra paper should have a template which includes a qr-code which the system can read as "ExtraPaper" and file accordingly. Student will still need to write their name, ID, test-number and question-number
* Any extra paper needs to be identified manually - this is currently done using the "manual page identifier" script. The instructor needs to read (and input) the test-number and question-number.
  * Notice that the system does not handle multiple extra pages for a given question particularly well. It will just append them **in scan order** to the grouped-images. So if they are scanned out of order then they will appear out of order in the (final) grouped image.
