import toml
import random

from specParser import SpecVerifier, SpecParser

sv = SpecVerifier()
sv.verifySpec()
sv.checkCodes()
sv.saveVerifiedSpec()

sp = SpecParser()
sp.printSpec()
