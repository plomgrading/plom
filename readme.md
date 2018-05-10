# MLP
System to generate tests from a small number of similar source versions

* Given a small number (say 4) versions of a test, the scripts in 'build' allow the manager to generate interleaved tests.

 * The test versions must all have the same structure - ie the same questions numbers on each page and same number of pages

 * The pages of the tests can be grouped together - ID pages (where student name / number information is written), as well as 'pagegroups' which should be thought of as the pages that comprise a given question.

 * The manager can then set how each pagegroup is chosen from the available versions.
  * 'Fixed' = all tests get version 1
  * 'Random' = each test gets a randomly selected version of the pagegroup
  * 'Cycle' = the versions will cycle 1,2,3,4,1,2,3,4, etc through the produced papers

* After the test structure has been specified, the desired number of tests are generated (according to that specification).
 * Each page of each test is stamped with QR-codes. 1x code giving the name of the test (eg something like '101Midterm'), and then 2 copies of a code 'txxxxpyyvz' - where xxxx is the number of the test paper, yy is the page number and z is the version from which the page has been taken. These codes enable later scripts to correctly identify the page and file it away appropriately.
 * To construct the tests a small latex wrapper pulls the desired pages together and stamps them with QR-codes using a combination of the tikz, pdfpages and qrcode latex packages.
 * The build script (and other scripts) makes use of (reasonably) standard linux packages and commands. Further, when many commands need to be run, we build a small text file of the commands and then parallelise them by piping the commands file through the unix parallel command.

* After building and the test has been printed and sat by students, the pages need to be scanned and sorted in to their groups and versions.
 * Based on our experiences with [AMC](https://www.auto-multiple-choice.net/) we use [imagemagick](https://www.imagemagick.org/script/index.php) to apply a simple gamma-shift to each page image in order to keep white as white, but to make all other colours darker.
 * Since every page has a unique QR-code stamp on it it is not difficult, via zbarimg, to identify the pages.
 * The pages are tiled together into their page groups using imagemagick.
 * At present the scripts have some simple methods to avoid processing files many times (eg if you scan in the first 50 tests and then later scan in another 100) - but this definitely needs improving.

* The main part of MLP lies in the image_server and clients directories. The image_server does what its name suggests - it serves up page images to the clients (ie the markers) and then keeps track of the resulting IDs, annotated images and marks.

* The image_server is split into several pieces
  * some database handling code (which should be moved from python's [peewee](http://docs.peewee-orm.com/en/latest/) library to use (perhaps?) Qt's [database library](http://doc.qt.io/qt-5/sql-connecting.html). One for associating student numbers and names with papers, and then another to record marks + annotated pagegroup images.
  * a simple user manager - to keep track of passwords. The passwords are stored hashed using [passlib](https://passlib.readthedocs.io/en/stable/).
  * a simple 'authority' which verifies passwords and hands out authorisation tokens to the server (which can then be passed on to clients). The tokens are produced using [uuid4](https://docs.python.org/3.6/library/uuid.html).
  * the main server which keeps track of who has which file and what information is coming back from the clients.
  * files are served and retrieved from clients using a [webdav server](https://wsgidav.readthedocs.io/en/latest/).
  * messages between clients and the server are handled using the standard python [asyncio](https://docs.python.org/3/library/asyncio.html) library.
  * These messages are encrypted using SSL. We've included a certificate here (in the resources directory), but this definitely needs to be rebuilt for each project.
  * There are also two manager scripts in the image server directory - these display information from the current databases and allow the manager to filter the data and display some basic statistics.

* There are 2 different clients - the identifier and the marker.

* The identifier client displays the id pages from a test and the TA needs to enter either the student's ID number or their name.
  * The client requests a copy of the class list from the server (which currently must be a comma delimited file at 'resources/classlist.csv' with headings 'id', 'surname', 'name' )  
  * Having a local copy (stored in a temp directory) of the class list means that both the student number and student name text entry boxes have auto-completion.
  * One the TA has identified the current paper, the information is sent back to the server and then a new id page image is downloaded.

* The marker client is much more involved - not least because page images must be downloaded from the client and then annotated, graded and uploaded again.
 * on start up the marker client is asked to pick the pagegroup and version of the test they are marking.
 * then the main window opens up - this shows the current test as well as options for annotation, reversion (ie going back to the original pageimage) etc. Initially no pageimages are present and the TA has to click "get next test".
 * on clicking this the client requests a groupimage (ie matching the pagegroup + version the TA is marking) from the server. The server copies the a relevant groupimage into the webdav and tells the client what the filename is. The client then downloads the image and returns a 'I got it' message to the server, which can then delete the file from the webdav.
 * now the TA can annotate the paper (by pressing the big 'annotate' button). This fires up a separate window with a little annotation application in it.
 * The annotation window has several simple paint tools (like pen, line, box, tick, cross). Using left-click with line draws a line, while right-click draws a line with an arrow-head. Left-click with tick/cross produces a tick/cross, while right-click gives a cross/tick.
 * There is a simple text tool (which one leaves using the escape key). Additionally the TA can click on a 'standard comment' and then click in the window to paste that comment. Comments in the comment list can be edited, added, deleted etc. They are stored in the 'commentList.json' file.
 * If you click "cancel" then the annotation windown is closed with no changes made to the image and the app returns to its main window.
 * After annotating, the TA assigns a mark (by clicking the appropriate button) and then clicking finish. This will close the window, stamp the grade in the top-left corner of the image, save the annotated image and the grade and then upload them to the server. It then downloads the next pageimage to the client main window. Pressing enter will fire up the annotator with this new pageimage.

* After all the pageimages are marked and all the papers identified, one should close the servers and move on to finishing.
* This stage requires more polishing and the scripts present should be split up a little more.
* The script checks to see which papers have been completely graded and identified. For each such paper a simple cover page is produced (via latex) displaying the student name and id number, their mark for each pagegroup and the version of that page group, and their total mark.
* This cover page, the id-pages and the annotated pagegroup images and then combined into a single pdf.
* The pdf is renamed as exam_X.pdf where X is the student number. This should also perhaps be extended to give the option of naming the file differently - eg including an exam code for simple authentication when returning papers (as we have done with AMC).
