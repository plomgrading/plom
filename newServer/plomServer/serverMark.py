from datetime import datetime
import hashlib
import imghdr
import json
import os
import subprocess
import tempfile
import uuid


def MgetQuestionMax(self, q, v):
    iv = int(v)
    iq = int(q)
    # check question /version in range.
    if iq < 1 or iq > self.testSpec["numberOfQuestions"]:
        return [False, "QE"]
    if iv < 1 or iv > self.testSpec["numberOfVersions"]:
        return [False, "VE"]
    # Send back the max-mark for that q/v
    return [True, self.testSpec["question"][str(iq)]["mark"]]


def MprogressCount(self, q, v):
    """Send back current ID progress counts to the client"""
    iv = int(v)
    iq = int(q)
    return [self.DB.McountMarked(iq, iv), self.DB.McountAll(iq, iv)]


def MgetDoneTasks(self, user, q, v):
    """When a marked-client logs on they request a list of papers they have already marked.
    Check the (group/version) is valid and then send back a textfile with list of TGVs.
    """
    iv = int(v)
    iq = int(q)
    return self.DB.MgetDoneTasks(user, iq, iv)


def MgetNextTask(self, q, v):
    """The client has asked for the next unmarked paper, so
    ask the database for its task and send back to the
    client.
    """
    give = self.DB.MgetNextTask(q, v)
    if give is None:
        return [False]
    else:
        return [True, give]


def MlatexFragment(self, user, fragment):
    # TODO - only one frag file per user - is this okay?
    tfrag = tempfile.NamedTemporaryFile()
    with open(tfrag.name, "w+") as fh:
        fh.write(fragment)

    fname = os.path.join(self.tempDirectory.name, "{}_frag.png".format(user))
    if subprocess.run(["python3", "latex2png.py", tfrag.name, fname]).returncode == 0:
        return [True, fname]
    else:
        return [False]


def MclaimThisTask(self, user, task):
    return self.DB.MgiveTaskToClient(user, task)


def MdidNotFinish(self, user, task):
    """User didn't finish marking the given task. Tell the
    database to put this back on the todo-pile.
    """
    self.DB.MdidNotFinish(user, task)
    return


def MreturnMarkedTask(
    self, user, task, qu, v, mark, image, plomdat, comments, mtime, tags, md5
):
    """Client has marked the pageimage with task, mark, annotated-file-name
    and spent mtime marking it.
    Send the information to the database and send an ack.
    """
    # score + file sanity checks were done at client. Do we need to redo here?
    # image, plomdat are bytearrays, comments = list
    aname = "markedQuestions/G{}.png".format(task[1:])
    pname = "markedQuestions/plomFiles/G{}.plom".format(task[1:])
    cname = "markedQuestions/commentFiles/G{}.json".format(task[1:])
    #  check if those files exist already - back up if so
    for fn in [aname, pname, cname]:
        if os.path.isfile(fn):
            os.rename(
                fn, fn + ".rgd" + datetime.now().strftime("%d_%H-%M-%S"),
            )
    # now write in the files
    with open(aname, "wb") as fh:
        fh.write(image)
    with open(pname, "wb") as fh:
        fh.write(plomdat)
    with open(cname, "w") as fh:
        json.dump(comments, fh)

    # Should check the aname is valid png - just check header presently
    if imghdr.what(aname) != "png":
        print("EEK = {}".format(imghdr.what(aname)))
        return [False, "Misformed image file. Try again."]
    # Also check the md5sum matches
    md5n = hashlib.md5(open(aname, "rb").read()).hexdigest()
    if md5 != md5n:
        return [
            False,
            "Misformed image file - md5sum doesn't match serverside={} vs clientside={}. Try again.".format(
                md5n, md5
            ),
        ]

    # now update the database
    rval = self.DB.MtakeTaskFromClient(
        task, user, mark, aname, pname, cname, mtime, tags, md5n
    )
    if rval:
        self.MrecordMark(user, mark, aname, mtime, tags)
        # return ack with current counts.
        return [True, self.DB.McountMarked(qu, v), self.DB.McountAll(qu, v)]
    else:
        return [False, "Database problem - does {} own task {}?".format(user, task)]


def MrecordMark(self, user, mark, aname, mtime, tags):
    """For test blah.png, we record, in blah.png.txt, as a backup
    the filename, mark, user, time, marking time and any tags.
    This is not used.
    """
    fh = open("{}.txt".format(aname), "w")
    fh.write(
        "{}\t{}\t{}\t{}\t{}\t{}".format(
            aname, mark, user, datetime.now().strftime("%Y-%m-%d,%H:%M"), mtime, tags,
        )
    )
    fh.close()


def MgetImages(self, user, task):
    return self.DB.MgetImages(user, task)


def MgetOriginalImages(self, task):
    return self.DB.MgetOriginalImages(task)


def MsetTag(self, user, task, tag):
    return self.DB.MsetTag(user, task, tag)


def MgetWholePaper(self, testNumber):
    return self.DB.MgetWholePaper(testNumber)
