# Identifying papers
## A little background first
* When the test papers are produced every page of every test is stamped with unique QR-codes that identify them. The code is of the form TxxxxPyyVz - where xxxx is the test number, yy is the page number and z is the version of that page.
* Hence it is easy (barring scanning mishaps) to reconstruct a paper from the scans of its individual pages - even if those scans are completely out of order. It is, however, a harder computing problem to determine *whose* paper it is.
* Unfortunately MLP doesn't yet use machine learning (or other buzzword compliant technologies) to automagically read student numbers off the front pages of tests. Perhaps in time, we'll use check-boxes or something fancier (ie buzzword compliant). But, alas, not yet.
* Hence we have to match a given paper to a given student - this is where you come in. We need you to read student numbers off the front page of tests.
* It is a little tedious, but isn't difficult.

## Identifier window
* A couple of moments after clicking "start" on the launch page, a window should pop up that looks like this:
![](figs/client1.png)
* On appearing, the window should already be populated with an ID-page of a test.
* If the page-image is too small, then you can left-click on it to zoom in, and right-click to zoom-out.
* We recommend that you identify papers by the student-number rather than student-name.
* As you enter the student-number in text-entry box, a pop-up auto-completer should appear. The pop-up is populated (all going well) by data from the class list.
* Once you've entered the number (or name), then hitting enter will pop up a "Are you sure" window (just in case). Hitting enter again will accept the result.
* The next ID-page should be automatically loaded and you can continue.
* If you need to go back to re-ID a page then you can simply click on that page from the "table of papers" and re-enter the data.
* If the system does not recognise the student-number we recommend that you tell your IIC (though there is the option to enter unrecognised student number / name pairs).

## Please close the window
* We recommend that you close the window when you leave your computer for more than a few minutes. This makes sure all data is saved on the server.
* When you fire up the launch window again it will remember the data you entered previously and you should only have to enter your password.
