<!--
__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018 Andrew Rechnitzer"
__license__ = "GFDL"
 -->

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

## Image server
* The server is (presently) configured to serve files at 'localhost' - this would need to be tweaked if you want to serve files to other machines, but it works just fine for local testing.
* There are 2 relevant ports - one for message passing (to and from the clients) and one for the webdav server (which is how all files are passed to and from clients - they are just copied into the webdav and appropriate messages passed (on the other port) letting client or server know things are there). The default ports were chosen because one is the backup ssh port (and so our IT lads have it open on the departmental firewall) and I asked them to open one more for me (so it is open on my work desktop = hinge). If you want to play around with these ports (and serve files to other machines) you might need to ask the IT lads to open a port for you. Though if you are doing things on UBC wireless it might be different. Experiment.
* Before you run the server, first run userManager.py and put in a couple of users with passwords. (this is not yet ready to be done while the server is running, but it shouldnt be too hard to get that working)
* When you run image_server.py, it reads all the relevant page group images and indexes them in 2 databases (in ../resources) - one for identifying and one for marks. It also loads in the user list you have generated so that it can authenticate clients.
* Not much else to do while things are being id'd or marked.
* There are two other manager scripts = identify_manager.py and mark_manager.py which allow the IIC to look at how things are going and do some simple stats on the fly.

## Clients
### Identifying tests
* Since we don't have fancy digit recognition or AMC-style checkbox reading, we have to use hoomans to do read the student name or number on the ID pagegroup and enter them into the system.
* Run the identifier_client.py.
* You'll be prompted for name + password, and also the server and port information.
* After that you'll be presented with a gui with places to enter in names and numbers (which auto-complete from a classlist passed from the server to the client)...
* but first you need to request an image from the server - click "request next"
* the id pagegroup image is downloaded and displayed in the window. The TA can zoom in by click and drag.
* Enter the number / name in the boxes and it auto-completes. Hitting enter asks the user to confirm and then uploads this data to the server. The next image is downloaded.

### Marking tests
* Again - no AI here, just hoomans.
* Run marker_client.py
* You are prompted for username, password, which pagegroup and which version (and similar stuff about ports and servers).
* The marker client consists of 2 parts - the first is where the user interacts with the server - asking for new pagegroupimages to mark, or 'reverting' images which have already been marked (ie so they can be marked afresh). The second part is the annotation window - which is a simple paint program and a place to enter the total mark for the pagegroup.
* First up 'get next' to get an image to grade.
* You can then either click "annotate and get next" or simply press enter.
* This then opens up the annotation window.
* This has simple drawing options - line, pen, box, tick, cross. Also simple text entry. Note line, tick and cross also work with right-click. right-click with line draws an arrow, while right-click with tick gives a cross and vice-versa.
* Also one can click on the list of comments and then click into the annotation window (ie not drag) and the comment is pasted into place. Comments in the list can be added, edited, deleted. Draging them up and down reorders them.
* After the test has been annotated you can simply click a mark button (the max mark is set by the server on the basis of what you told it way back in 0101_construct_a_spec).
* Pressing cancel discards all of this and returns to the first window
* Pressing finish saves the annotated image and the mark and uploads them to the server (which files them away).
* The next image (according to the group-version chosen) is automatically downloaded. Pressing enter fires up the annotation window again.
* A previously annotated paper (from this session) can be annotated further, or can be reverted to its original state.

## Finishing
* The script in this section need some more development. They function, but could be a bit cleaner and robust.
* Running 07_check_completed (should be split into a few scripts) - first checks which papers have been marked and ID'd.
* For each completed test, a simple (latex'd) cover page is generated with the name and student number, a table of marks / versions for each pagegroup and a total.
* The coverpage is combined with the annotated pagegroup images into a single PDF - which is save in the 'reassembled' directory.
* At present the reassembled test is saved as exam_X.pdf where X is the student number.
