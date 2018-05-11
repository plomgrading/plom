# Walk through the process

## Build
* In the build directory there are 2 scripts to run.
* First edit the 01_construct_a_spec script to change the structure of the test you have. I have set these to reasonable values for the dummy test at hand.
* Each pagegroup is (typically) a question in the test - if a question goes over 2 or 3 pages, they will always be the same version. Later their scans will be tiled together into a single groupImage for marking.
* The dummy test is 12 pages and 6 versions. This is actually a midterm we gave in maths 101 in Feb 2018. The pdfs are in the sourceVersions directory as versionX.py.
* Now run 01(blah).py  - this will save the spec in the ../resources directory so that other scripts can use it.
* Now run the 02_build_tests_from_spec.py script.
* This will construct a .tex file for each test and pull appropriate pages from the source versions of the tests and mark them with required QR codes. The .tex files are then compiled in parallel and the results moved into the examsToPrint directory.
* These tests are now ready to feed to students.

## Interlude
* Each student must get a unique test (just like AMC, crowdmark, gradescope etc)
* They will enjoy the experience.
* Make sure they don't deface the QR codes.
* Scan in the resulting tests ( at least 200dpi and colour please)

## Scan and group.
* Move the pdfs of the scans into the scannedExams directory
* For dummy runs I recommend using something like pdfjoin to mash together the examsToPrint pdfs into a single pdf in the scannedExams directory. Eg "pdfjoin ../build/examsToPrint/test*.pdf -o scannedExams/myPretendScan.pdf"
* Run the 03_scans_to_page_images.py script - this takes each pdf of scans and decomposes them into a single image for each page. The results are saved in the pageImages directory
* Run the 04_decode_images.py script - this looks at the QR codes on each page image and works out which 'tpv' code the page has - ie which **T** est, which **P** age and which **V** ersion. The results are moved into an appropriately named subdirectory of the decodedPages directory.
* Now run 05_missing_pages.py - this looks to see that for each test we either have all the pages (ie a student sat it and we got all their pages back and into the system) or none of the pages (ie the test pdf wasn't used, or hasn't been scanned yet). This is to make sure we have no half-processed papers.
* Finally run 06_group_pages.py. This script puts the page images together into the desired page groups. The results are save in various appropriately named subdirectories of the readyForGrading directory. Each groupImage is named either tXidg.png (id-group pages from test X) or tXgYvZ.png (test X, pagegroup Y, version Z).
* Now we are ready to move onto servers and clients.
