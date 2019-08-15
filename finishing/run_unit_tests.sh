#!/bin/bash

# TODO: replace with proper unit test framework (pytest?)

python3 -c "import utils; utils.test_hash()"

if [ $? -ne 0 ]; then
    echo "FAIL"
    exit 1
fi

python3 -c "import return_tools as rt; rt.test_csv()"

if [ $? -ne 0 ]; then
    echo "FAIL"
    exit 1
fi
