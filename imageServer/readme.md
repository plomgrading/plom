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
   * the messages between server and client (and server and manager) are handled using some simple(ish) asyncio stuff with ssl encryption.
   * when the client logs in initially the send a message ['AUTH', user, password] - the server then checks the password against the hashed password list stored in '../resources/userList'. If the password is fine then the server returns an authorisation token. This token is used to check (subsequently) that the user is authorised to make requests of the server.
   * **NOTE** when a client logs in again we should make sure anything in the database listed as 'OutForIDing' or 'OutForMarking' gets put back on the todo list. Similarly when they close. Not sure if we can also put in some time-out thingy in case a client crashes out of the system?

   * a message is of the form of a list ['CMD', user, token, 'ARG1', 'ARG2',...].
     * Where 'CMD' is some 3-letter command (such as 'ACK' - for acknowledge or  'ERR' for error or 'RCL' = requestClassList)
     * user = the name of the user
     * token = authentication token.
     * The later ARGs depend on the command. eg to request the classlist, the identifier-client sends ['iRCL', user] to the server. The server then copies the classlist into the webdav directory and sends back ['ACK', filename]. Once the identifier-client has the classlist it sends back ['iGCL',filename] which the server acknowledges with ['ACK'] and deletes the file from the webdav.
     * When an id-client identifies a paper it sends ['iRID', user, code, sid, sname] - the username, the test's code, the student ID number and the student's name.
     * If the id-client wants another paper to identify, it sends ['iNID',user] and the server responds with ['ACK', code, fname] being the code of the test and the temp filename of the page image in the webdav.
     * list of commands sent from id-client or manager:
       * AUTH = request for authorisation - if the user/password pair are validated then a token is returned (a uuid4 random thingy)
       * UCL = user is closing their client. the server removes the authorisation token from their list.
       * iDNF = didntFinish = the client sends this for each unid'd paper they have. tells the server to put these papers back in the ToDo list.
       * iNID = nextUnIDd = asking for the next unid'd paper in the database.
       * iGTP = gotTest = sent to acknowledge that the client got the test image and that the server can delete it.
       * iRID = returnIDd = sent with code, student id number and student name. Server can then update the database with this information.
       * iRAD = returnAlreadyIDd = as previous excepting that the client had previously ID'd the paper and went back and ID'd it again (ie they made a mistake the first time).
       * iRCL = requestClassList = client requesting the classlist for the course (which is stored in ../resources/classlist.csv)
       * iGCL = gotClassList = tells the server that the client got the classlist and the server is free to delete the copy from the webdav.

     * Messages sent by the marker-client
       * AUTH and UCL = as abobve
       * mDNF = didntFinish - on closing the marker-client sends one for each pageimage it has but has not marked. These pageimages need to go back on the ToDo list.
       * mNUM = nextUnmarked - used by the client to ask for the next ToDo paper in the assigned pagegroup and version. The server copies the pageimage into the webdav and sends an ACK.
       * mGTP = gotTest - an acknowledgement sent by the client that it has copied the pageimage from the webdav and it is safe to remove it.
       * mRMD = returnMarked - the client sends this along with the mark, and the location (in the webdav) of the annotated pageimage.
       * mRAM = returnAlreadyMarked - as above, but the client has remarked this pageimage.
       * mGMX = getPageGroupMax - on starting the client sends this to ask the server what is the maximum mark that can be assigned to the pagegroup.

     * Responses from server
       * ACK = acknowledgement, followed by relevant data
       * ERR = error, followed by error message

   * The message list is JSON'd and then sent over the ssl'd socket. The code for doing this is pretty standard stuff (I hope I've used reasonable code here)
   * We use a simple (once you've seen it) python trick to translate the 3 letter messages sent over the socket into actual python commands. First a dictionary translates the 3letter command into the string of the function that should actually be called. Then call getattr(Object, String) which is equivalent to Object.String. Very handy.
   * the message passing (from the server end, and the client end is similar) is split into 3 parts.
     * proc_cmd() actually parses the message into a command call (using the getattr trick). This is relatively straightforward.
     * handle_messaging() is more involved. I have tried to code this using standard bits of asyncio code. See [this page](https://pymotw.com/3/asyncio/ssl.html) and also [here](https://docs.python.org/3/library/asyncio-protocol.html#protocol-examples) and many other googled pages. This waits (more on that in a moment) for a connection, reads the data from it, decodes the JSON into a list. The message is passed through proc_cmd, which processes the actual command and returns what ever acknowledgement or error is required. The ack/err is then sent back.
     * the asyncio stuff - pretty much taken directly from [here](https://docs.python.org/3/library/asyncio-protocol.html#protocol-examples)
       * loop = an asyncio event loop - read some of the asyncio python pages - they'll do a better job than me. Roughly speaking, this handles the asynchronous nature of the incoming connections so that whole system doesn't hang waiting for things to happen.
       * server = the event loop uses this to invoke the coro server thingy when needed (I think **more thinking about this needed** but it works fine).
       * coro = an asyncio coroutine that listens for incoming connections and passes them to handle_messaging. See [here](https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.AbstractEventLoop.create_server)
    * The eventloop runs forever until there is a user-interrupt and then things are closed down.
   * On closing the image_server also re-saves the databases as JSON files '../resources/examsIdentified.json' and '../resources/groupImagesMarked.json'


* userManager = a very simple user-management script / gui. The manager can add or remove users.
 * At present the script does not communicate through the server. We need to add communication with the running server to be able to add/delete users. Adding users should be straightforward, however care might be needed with deleting users (esp if they have images checked out)
 * usernames and hashes (using passlib recommended defaults) are stored in '../resources/userList.json'

* authenticate = gives Authority = a simple class for authenticating clients trying access the server.
 * authenticate loads the username/password-hash from ../resources/userList.json.
 * when the server gets an authorisation request, it passes username + password to Authority to validate it. If fine then it creates a token (using uuid4) which it stores and passes back to the server (who passes it on to the client).
 * this token is then used for user authentication (rather then verifying passwords at each interaction = slow).
