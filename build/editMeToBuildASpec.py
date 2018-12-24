__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018 Andrew Rechnitzer"
__license__ = "GPLv3"

import sys
# the following allows us to import from ../resources
sys.path.append('..')
from resources.testspecification import TestSpecification

spec = TestSpecification()

spec.Name = "AFunTest"

spec.setNumberOfTests(10)

spec.setNumberOfPages(12)
spec.setNumberOfVersions(4)

spec.setIDPages([1, 2])
# Always do ID Pages first.
spec.addToSpec('f',[3, 4], 9)
spec.addToSpec('f',[5, 6], 12)
spec.addToSpec('f',[7, 8], 12)
spec.addToSpec('f',[9, 10], 6)
spec.addToSpec('f',[11, 12], 6)

spec.writeSpec()
spec.printSpec()
