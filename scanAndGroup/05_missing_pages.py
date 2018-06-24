import json
import os
import sys

sys.path.append('..') #this allows us to import from ../resources
from resources.testspecification import TestSpecification

def readExamsScanned():
    global examsScanned
    if os.path.exists("../resources/examsScanned.json"):
        with open('../resources/examsScanned.json') as data_file:
            examsScanned = json.load(data_file)

def checkTest(t):
    missing = []
    for p in range(1, spec.Length+1):
        if str(p) not in examsScanned[t]:
            missing.append(p)
    if missing:
        print(">> Test {:s} is missings pages".format(t), missing)
    else:
        print("Test {:s} is complete".format(t))


spec = TestSpecification()
spec.readSpec()

readExamsScanned()
for t in sorted(examsScanned.keys(), key=int):
    checkTest(t)
