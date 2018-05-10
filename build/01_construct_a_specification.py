import sys
from testspecification import TestSpecification

spec = TestSpecification()

spec.Name = "Test1Test"

spec.setNumberOfTests(6)

spec.setNumberOfPages(8)
spec.setNumberOfVersions(2)

spec.setIDPages([1,2])
## Always do ID Pages first.
spec.addToSpec('f',[3,4],9)
spec.addToSpec('c',[5,6],12)
spec.addToSpec('r',[7,8],12)
spec.addToSpec('r',[9,10],6)
spec.addToSpec('r',[11,12],6)

spec.writeSpec()
spec.printSpec()
