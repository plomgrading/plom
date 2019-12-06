#!/bin/bash

# TODO: replace with proper unit test framework (pytest?)

python3 -c "import misc_utils; misc_utils.test1(); misc_utils.test_shortruns()"

if [ $? -ne 0 ]; then
    echo "FAIL"
    exit 1
fi
