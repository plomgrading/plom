from testspecification import TestSpecification
import json
import os

def readExams():
    global exams
    with open("../resources/examsProduced.json") as data_file:
        exams = json.load(data_file)

def scriptBuild():
    fh = open("./commandlist.txt","w")
    for x in exams:
        fh.write("python3 merge_and_code_pages.py {} {} {} {} \"{}\"\n".format(spec.Name, spec.Length, spec.Versions, x, exams[x]))
    fh.close()
    os.system("parallel --bar <commandlist.txt")
    # os.system("rm commandlist.txt")

spec = TestSpecification()
spec.readSpec()
exams={}
readExams()
scriptBuild()
