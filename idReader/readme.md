# AutoMagical student ID reading
* The system can read student IDs using a simple neural network.
* This requires that the test use the provided student-information-template in the ID page of the test.
* Note that this is not perfect, so it only provides *predictions* of the ID. A TA still has to verify them.
* That being said, the system has proven itself to be about 98% accurate on real-world data.
* The neural network needs to be trained. This can be done by either
  * running the training script, which downloads the NIST hand-written digit database and then uses tensorflow to train the model, or
  * use a previously trained model.

## Requirements
* Tensorflow (for all your buzzword compliant machine learning)
* opencv (for image manipulations)
* imutils (convenience functions for image manipulations)
* lapsolver (for solving linear assignment problems)

## Student information template
* The ID page of the source must use the information template provided.
  * either as tikz image in your latex, or
  * as an included svg/eps/pdf in your document
    - e.g., `\includegraphics{idBox}`, without changing the size.
    - It doens't matter where it is on the first page.
* **Future** - the system stamps the template onto the front page automatically?

## Training the model
* Training the model takes some time - on the order of ten-fifteen minutes on my laptop.
* You only need to do this once. **Not once per project** but **once**
* If you have not trained the model previously, then you should run `trainModelTF.py`
* This is not fast, but when done once you can just copy the model to new projects.
* More precisely, copy all files `digitModel*` to the same directory in a new project. These files are about 13mb.
* **Future** include the model in the repo or...?

## After model training
* You cannot proceed until  all papers have been scanned and grouped. ie just before the image server is run.
* The system needs the classlist in order to make worthwhile predictions. Without the classlist I wouldn't bother.
* Once the classlist is in place and the model has been trained (in the repo directory, not in the current project), just copy the idReader directory and its contents into the current project.
  * The classlist is imported by `imageServer/serverSetup.py`
* Then run `locateID.py` to select region on page which contains the student information template.

## LocateID
* This loads the first ID-group image and asks the user to isolate the part of the page that contains the student information template.
* Using the two sliders the user can increase/decrease the top/bottom rectangles and so blank out the irrelevant parts of the ID-group image.
* Clicking "go" then fires up the ID-prediction script "readStudentID.py" and passes the vertical range of the image to be examined.


## Making student ID predictions.
* That script looks at the ID page from each test and isolates the student-information box.
* Since that box has known dimensions it is easy to extract each student number digit.
* The image of each of those digits are then fed into the tensorflow model which returns a list of log-likelihoods.
* The log-likelihoods are then used to assign a "cost" of assigning this test to each student number in the classlist. A good match has a low cost, while a bad match has a high cost.
* Then we use a linear-assignment-problem solver to find the lowest-cost assignment of all the scans to all the student numbers (thanks to Omer Angel for suggesting this).
* That matching is then written to the file "predictionlist.csv" in the resources directory.
* The server sends that file to the ID-client which will display the predicted student ID to the TA. The TA can then accept or reject each prediction.
