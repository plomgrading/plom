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
