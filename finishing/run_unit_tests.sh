#!/bin/bash

# TODO: replace with proper unit test framework (pytest?)

python3 -c "import utils; utils.test_hash()"

python3 -c "import return_tools as rt; rt.test_csv()"

