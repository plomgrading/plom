#!/bin/bash

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Colin B. Macdonald
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023 Andrew Rechnitzer

echo "Demo ready for user to upload source tests and build a spec."
echo "Server will be populated with demo users and then launch."

set -e
echo "Cleaning up any old files from previous runs."
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

echo "Build database basics"
python3 manage.py makemigrations
python3 manage.py migrate

echo "Build groups and demo-users"
python3 manage.py plom_create_groups
python3 manage.py plom_create_demo_users


# WebPlom needs a Huey consumer running in order to complete some background tasks.
# In a separate terminal window, call:
# `python3 manage.py djangohuey`
# you must do this after running demo.sh b/c demo.sh erases the huey_db file
# Here is one option for launching it automatically:
# xterm -e "python3 manage.py djangohuey" &
# and here is another.
python3 manage.py djangohuey &

# This is for production use, when Debug = False
# python3 manage.py collectstatic

# TODO: note: the server will not have any scans in it yet

python3 manage.py runserver 8000
