## Stuff
* markedPapers = directory containing all the marked pageimages. Each image is renamed as GXgYvZ.png with (G=graded) and X=test number, Y=pagegroup and Z=version. For additonal neurosis each file is also stored with GXgYvZ.png.txt which is a 1-line text file that contains the name of the pagegroup image, the mark, who marked it and at what time. These files are not really needed - just backup.

* testspecification.py = a copy of the testSpec object described in the build directory.

* cleanAll = utility script to delete user generated content

* examviewwindow.py = defines a widget for exam viewing window used by the mark_manager. Displays the pagegroup image in the mark-manager and allows the manager to zoom in on parts of it.

* identify_manager = this is a relatively simple(?) gui that reads in the identity.db file and displays it using the Qt library's stuff. The manager can then filter by the marker (ie the TA) and also by the status of the paper. It also displays the 'user progress' - ie how many of the currently displayed papers has each user ID'd.
 * the script must be run locally since it reads the database and the image files from the current directory. We could, in time, make this work remotely (like the id and mark clients).
 * need to add ability to interact with the server - particularly to put a given test back on the ToDo pile or to identify it.

* mark-manager = a manager script that loads in the '../resources/test_marks.db' database and displays its contents.
 * the script must run locally - since it needs access to the pageimage files and the database files. Maybe this should be redone so it can run remotely... but that generates security issues.
 * selecting a pagegroup and pressing 'enter' loads the image into the window.
 * The manager can filter that display by pagegroup, version, status, marker and mark.
 * It also has the ability to display progress in each pagegroup, each version and each user (ie how many pageimages marked)
 * It can also display version and user histograms. This is useful to make sure versions have similar mark distributions and that TAs are giving similar distributions.
 * The progress displays and histograms are generated from the data currently displayed - ie with the current filters in place.
 * Note - need to add ability to annote a pagegroup futher, or send it back to the ToDo pile (if the TA has done it poorly).

 * id_storage.py = the script that handles the database (stored in '../resources/identity.db'). That database contains a list of the tests, the code for the IDpagegroup, their current status, who ID'd it, at what time, the relevant student ID and name.
  * code for the ID group is a string of the form 'tXidg' where X is the test number (filled with 0's to make it 4 characters long). This is almost the filename of the relevant pagegroup image - just append .png to it. This is what the server uses to find the image files.
  * status = 'ToDo' (if needs ID'ing), 'OutForIDing' (if it is currently allocated to a client), 'identified' if it has been ID'd be a client.
  * user = the user who ID'd the paper
  * time = time at which the paper was ID'd
  * SID = student id number on the paper
  * sname = student name - At present this is set up as 'FamilyName'+', '+'GivenName'
  * The database is actually handled using the python peewee library and we should probably think about moving to the Qt library's database stuff instead?

* mark-storage - this is the wrapper around the database using peewee to handle the actual database calls. Should perhaps be changed to use Qt database stuff. Information about each pageimage is stored in the database:
  * tgv = the code of the pageimage tXgYvZ, where X=testnumber (filled with zeros to make it 4 characters), Y=group number (filled with zeros to make it 2 characters) and Z=version number.
  * the relative path to the pagegroup image (in the ''../scanAndGroup/readyForGrading' directory)
  * the test number
  * the pagegroup number
  * the version number
  * the name of the annotated pagegroup image file (if it exists) - which resides in the 'markedPapers' directory
  * the status of the pageimage
    * ToDo = untouched, still needs to be marked
    * Marked = has been marked
    * OutForMarking = the pagegroup image has been assigned to TA and they are working on it.
  * the user who marked the pagegroup (or is working on it)
  * the time at which it was sent out for marking, or was returned marked
  * and the mark - set to -1 initially.

  * image_server - this is where all the fun happens. This script needs to understand how to communicate with the two databases (which it does through the objects in id_storage and mark_storage) as well as communicate with the clients.
   * the configuration of the various ports, hostname, username + password needs improving.
   * The database interactions are relatively straightforward (probably needs someone to look at it carefully for exceptions and errors)
   * image files are served to clients.  The files come from the '../scanAndGroup/readyForGrading' directory, so it must be run in place. Annotated image files are placed in the 'markedPapers' directory.

   * the messages between server and client (and server and manager) are handled using aiohttp at the server-side and requests at the client side. The client sends https-messages to the server (we've tried to make them REST-API style), and the server runs async-aiohttp to respond to those requests.

   * when the client logs in, it sends a put/request to "{server}:{port}/users/{user}" with the username, password and API-version. The server then checks the API and the password against the hashed password list stored in '../resources/userList'. If the password is fine then the server returns an authorisation token. This token is used to check (subsequently) that the user is authorised to make requests of the server.
   * Similarly, when a client logs out, it sends a delete request to the same "{server}:{port}/users/{user}" - which causes the server to delete the authorisation token.

   * **NOTE** when a client logs in again we should make sure anything in the database listed as 'OutForIDing' or 'OutForMarking' gets put back on the todo list. Similarly when they close. Not sure if we can also put in some time-out thingy in case a client crashes out of the system?

   * messages from the client to the server are HTTP requests to various URLS. These (mostly) start with either "/ID/", "/TOT/" or "/MK/" - for identifier, totaler, or marker, the exceptions being the login/logout and API-check urls.

   * The messages sent by the identifier, totaler and marker are HTTP requests sent to the server. We give the list of the URLS here. All of these pass the username and authorisation-token for verification.



## Messenger messages
When the client is started the user is prompted for various details: username, password, port, server etc. The user the selects a task and the client fires up the messenger which acts as the message-passing intermediary between the client and the server. The messenger then
* put "/users/{user}" - (with username, password, API included as data). The server verifies the user/password/API and then returns the auth-token
* delete "/users/{user}" (with username, token included as data). The server verifies the token and then deletes the authorisation token - logging out the user.


## Identifier messages
I have tried to list these in the order in which they are called by the identifier-client (after the initial authorisation message). All of these include the username + token in order to authenticate the user before any actions performed.

   * get "/ID/classlist" - server returns classlist file (used for auto-completion of names and IDs`)
   * get "/ID/predictions" - server return prediction-list file (generated by machine-learning student-number reader)
   * get "/ID/tasks/complete" - server return list of tasks completed (ie papers-identified) by that user
   * get "/ID/progress" - server returns [#papers identified by all users, #total papers to be identified]
   * get "/ID/tasks/available" - server returns [code for next available task] or 204-code (if no tasks left). Note that this task is not automatically assigned to the user. The user has to send a separate "claim task" request.
   * patch "/ID/tasks/{task}" - user asks to claim task (if still available) and the server returns either an error-code (if task taken by another user) or the corresponding image of the id-page.
   * put "/ID/tasks/{task}" - when user IDs a paper, the client sends this message to the server (with the ID/Name). The server either reports a success or an error-code if that ID-number has been used already.
   * delete "/ID/tasks/{task}" - when a user closes the identifier, any un-finished tasks have to be reported to the server. This message unclaims a given task, the server will then put the task back on the todo-list.
   * get "/ID/images/{tgv}" - when the user clicks on a previous completed task the client will look to see if it has the corresponding image already and display it. If the file is not present, then it sends this message to the server and it returns the image-file.

## Totaler Messages
These are very similar to those for the identifier - indeed the only differences are that it doesn't require a classlist or prediction-list, it needs the max-possible mark for the paper. And instead of passing back student-ID/Names, it returns the (user-inputted) mark.

* get "/TOT/maxMark" - return max-total-mark for test
* get "/TOT/tasks/complete" - return list of tasks completed by that user
* get "/TOT/tasks/available" - return the next available task or an error code if none left
* get "/TOT/progress" - return [#done, #total]
* patch "/TOT/tasks/{task}" - claim task (if still available) - return imagefile
* put "/TOT/tasks/{task}" - update the mark of the task (ie test)
* delete "/TOT/tasks/{task}" - unclaim task
* get "/TOT/images/{tgv}" - return imagefile of that tgv

## Marker Messages
Most of these are similar to those of the identifier and totaler, but there are necesarily more complications since the marker's task is more involved. Again, we've tried to list these in the approximate order they are called.

* get "/MK/maxMark" - server returns max-mark for the page-group (ie question)
* get "/MK/tasks/complete" - server returns list of tasks (within that page-group/version) completed by that user
* get "/MK/progress" - server returns [#done, #total] for tasks within that pagegroup/version
* get "/MK/tasks/available" - server returns next available task within that pagegroup/version

* get "/MK/latex" - user sends a latex-fragment which the server then processes into a png and returns. Note this runs at the start of the marker to cache user-defined latex-comments. It is then run each time the user makes a new latex comment.

* patch "/MK/tasks/{task}" - marker claims the task (if still available) - server returns imagefile or an error code if task already taken by another user.

* put "/MK/tasks/{tgv}" - client sends back annotated-image, plom-file, comments, mark etc to server. Server responds with error if any problems, or with a progress update [#done, #total] if all good.

* delete "/MK/tasks/{task}" - unclaim the task.

* patch "/MK/tags/{tgv}" - client sends user-tags of that tgv to the server.

* get "/MK/images/{tgv}" - when the user clicks on a previous completed task the client will look to see if it has the corresponding image (original/annotated) already and display it. If the file is not present, then it sends this message to the server and it returns the original image, the annotated image, and the plom-file (ie the svg-like file which allows system to continue editing an already annotated image).

* get "/MK/whole/{number}" - during annotation user can press F1 and system displays whole of the paper. Client sends this request to server and server returns group-images of entire paper (except id-page)

* get "/MK/originalImage/{tgv}" - in marker window if user pressed "view" and enters a test-number then sends tgv (with the current page-group+version) to server. server returns (original, unannotated) imagefile of that tgv.


## Other stuff


* userManager = a very simple user-management script / gui. The manager can add or remove users.
 * At present the script does not communicate through the server. We need to add communication with the running server to be able to add/delete users. Adding users should be straightforward, however care might be needed with deleting users (esp if they have images checked out)
 * usernames and hashes (using passlib recommended defaults) are stored in '../resources/userList.json'

* authenticate = gives Authority = a simple class for authenticating clients trying access the server.
 * authenticate loads the username/password-hash from ../resources/userList.json.
 * when the server gets an authorisation request, it passes username + password to Authority to validate it. If fine then it creates a token (using uuid4) which it stores and passes back to the server (who passes it on to the client).
 * this token is then used for user authentication (rather then verifying passwords at each interaction = slow).
