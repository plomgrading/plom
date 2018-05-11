import sys
from testspecification import TestSpecification

spec = TestSpecification()

spec.Name = "AFunTest"

spec.setNumberOfTests(20)

spec.setNumberOfPages(12)
spec.setNumberOfVersions(4)

spec.setIDPages([1,2])
## Always do ID Pages first.
spec.addToSpec('f',[3,4],9)
spec.addToSpec('c',[5,6],12)
spec.addToSpec('r',[7,8],12)
spec.addToSpec('r',[9,10],6)
spec.addToSpec('r',[11,12],6)

spec.writeSpec()
spec.printSpec()
