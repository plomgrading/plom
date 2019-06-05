# Random thoughts on marker-client / server interactions.

## Words
* Server = the image-server.py running on central machine
* Client = the client.py application running on user's machine
* TA = the user who is running the client on their machine and will do the actual marking of question-images.
* IIC = (instructor in charge) - the faculty-member/manager (not administrator) who is in charge of making sure the test/exam gets marked and back to the students.

## Initialisation
* TA inputs
  * their login / password
  * test details (at present server name / ports)
  * which question / version they will mark


* Client sends a ping to the server to confirm it is up and running
* Server returns and acknowledgement


* Client sends authorisation request to server (login/password)
* Server sends back authorisation-token (at present a hex UUID)


* Client requests "rubric" (for the question given by TA)
* Server sends back the maximum mark for that question.


* Client requests list of questions already marked
* Notice that this list could be quite long, so it is actually communicated to server (at present) by sending a file rather than sending the list directly over the socket.
* Server constructs a file which contains the list of TGV-codes + marks + time-spent. The TGV-codes (test/group/version) are only those marked by that login (and nobody else). The file is copied into the webdav and the name sent back to the client.
* Client gets the file, processes those TGV+mark pairs. Sends back a "Done with this file" message
* Server deletes the file.
* More on this below


* Client asks for counts
* Server sends back the total number of that question/version pair and the number that have been marked (by everyone) so far.


* Client requests next unmarked paper (question/version pair)
* Server looks up TODO question/version pair from database. Copies relevant image-file to webdav and sends TGV+filename back to client.
* Client copies the file and adds the TGV+filename to its list, updates the current image displayed. Sends back a "Done with this file" message.
* Server deletes the file.


## After client has finished marking a question.
* TA ends the annotation session.
* Client records the mark, the time spend marking and whether or not to automatically relaunch the annotator with the next paper (which still needs to be transferred from server).

* Client uploads the annotated image file to the webdav server
* Client sends message to server returning a marked paper with
  * username + authorisation token
  * which TGV code
  * the mark given
  * the location of the file on the webdav server
  * the time spend marking
  * the question number + version number

* Server moves file from webdav to appropriate directory
* Updates its database record for that test/question/version with
  * who marked it
  * mark given
  * time spent marking
  * location of annotated image file
* Server sends back an acknowledgement which includes updated counts of total number of papers (that question/version) and how many are completed.

* Client updates its progress bar based on the revised counts

* If TA has selected "relaunch annotator" then client requests next unmarked paper (question/version pair)
* Server looks up TODO question/version pair from database. Copies relevant image-file to webdav and sends TGV+filename back to client.
* Client copies the file and adds the TGV+filename to its list, updates the current image displayed. Sends back a "Done with this file" message.
* Client relaunches annotator on that file.
* Server deletes the file.

## When TA finishes current marking session
* TA clicks "close" button
* Client loops through its internal paper list looking for any paper that does not have "marked" status.
  * For each such paper it sends a "Did not finish" message to the server which includes the TGV code of the paper.
  * The server updates the status of each TGV in the database from "OutForMarking" to "TODO" and returns and acknowledgement.

* After this loop is finished the client sends a "User is closing" message and then closes itself.
* The server revokes the TA's current authorisation token.

## Handling previously marked papers
* If the TA has marked this question previously then when they log in the client will download the list of those papers from the server. This list is just the TGV-codes and the marks given.
* The client displays these papers (+marks+times) in its list of papers.
* Images of those papers will not be downloaded unless the TA selects one of those TGV from the paper list. This is because each image can be about 200kb - and if there are 100-papers then this is quite a lot of overhead upon login.

* The TA selects a paper from the list.
* The client checks if it has already downloaded the image-file
  * If it has, then it displays that image (either the annotated file, if the paper has been marked, or the original file if the paper has not been marked)
  * If it has not, then it sends a "get group image" request to server.
* The server copies the original image to the webdav and, if it exists, also the annotated image.
* The server sends an acknowledgement back to the client with the location of either one or two files.
* The client grabs the files from the webdav and sends "done with this file" messages back to the server. The client displays the annotated image (if it exists) and otherwise the original image.
* The server deletes the copies of the files from the webdav.
