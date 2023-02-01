#!/bin/bash

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Colin B. Macdonald
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu

set -e

echo "Avoid perplexing errors by removing autogen migration droppings"
ls **/migrations/*.py | grep -v __init__.py
EVIL=`ls **/migrations/*.py | grep -v __init__.py`
rm -f $EVIL

rm -f db.sqlite3
rm -f huey/huey_db.*

rm -rf sourceVersions
rm -rf papersToPrint
rm -rf media
mkdir media

python3 manage.py makemigrations
python3 manage.py migrate

python3 manage.py plom_create_groups

python3 manage.py plom_create_demo_users

python3 manage.py plom_demo_spec --publicCode 93849
python3 manage.py plom_preparation_test_source upload -v 1 useful_files_for_testing/test_version1.pdf
python3 manage.py plom_preparation_test_source upload -v 2 useful_files_for_testing/test_version2.pdf

python3 manage.py plom_preparation_prenaming --enable
python3 manage.py plom_preparation_classlist upload useful_files_for_testing/cl_good.csv
python3 manage.py plom_preparation_qvmap generate

python3 manage.py plom_papers build

# WebPlom needs a Huey consumer running in order to complete some background tasks.
# In a separate terminal window, call:
# `python3 manage.py djangohuey`
# you must do this after running demo.sh b/c demo.sh erases the huey_db file
# Here is one option for launching it automatically:
xterm -e "python3 manage.py djangohuey" &

# This is for production use, when Debug = False
# python3 manage.py collectstatic

# TODO: note: the server will not have any scans in it yet

python3 manage.py runserver 8000
