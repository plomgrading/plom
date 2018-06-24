import json
import os
import sys
sys.path.append('..') #this allows us to import from ../resources
from resources.testspecification import TestSpecification


def readExams():
    global exams
    with open("../resources/examsProduced.json") as data_file:
        exams = json.load(data_file)

def scriptBuild():
    fh = open("./commandlist.txt", "w")
    for x in exams:
        fh.write("python3 mergeAndCodePages.py {} {} {} {} \"{}\"\n".format(spec.Name, spec.Length, spec.Versions, x, exams[x]))
    fh.close()
    os.system("parallel --bar <commandlist.txt")
    # os.system("rm commandlist.txt")

spec = TestSpecification()
spec.readSpec()
exams = {}
readExams()
scriptBuild()
