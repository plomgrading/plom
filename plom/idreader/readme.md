# AutoMagical student ID reading
* The system can read student IDs using a simple neural network.
* This requires that the test use the provided student-information-template in the ID page of the test.
* Note that this is not perfect, so it only provides *predictions* of the ID. A TA still has to verify them.
* That being said, the system has proven itself to be about 98% accurate on real-world data.
* The neural network needs to be trained. This can be done by either
  * running the training script, which downloads the NIST hand-written digit database and trains the model, or
  * use a previously-trained model.

## Student information template
* The ID page of the source must use the information template provided.
  * either as tikz image in your latex, or
  * as an included svg/eps/pdf in your document
    - e.g., `\includegraphics{idBox}`, without changing the size.
    - It doesn't matter where it is on the first page.

## Making student ID predictions.
* The code looks at the ID page from each test and isolates the student-information box.
* Since that box has known dimensions it is easy to extract each student number digit.
* The image of each of those digits are then fed into the model which returns a list of log-likelihoods.
* The log-likelihoods are then used to assign a "cost" of assigning this test to each student number in the classlist. A good match has a low cost, while a bad match has a high cost.
* Then we use a linear-assignment-problem solver to find the lowest-cost assignment of all the scans to all the student numbers (thanks to Omer Angel for suggesting this).
* That matching is then written to the database.
* The server sends the prediction info to the ID-client which will display the predicted student ID to the TA. The TA can then accept or reject each prediction.
