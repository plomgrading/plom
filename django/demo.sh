#!/bin/sh

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Colin B. Macdonald
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu

set -e

rm -f db.sqlite3
rm -rf huey
mkdir huey

rm -rf sourceVersions
rm -rf papersToPrint
rm -rf media
mkdir media

python3 manage.py makemigrations
python3 manage.py migrate

python3 manage.py plom_create_groups

python3 manage.py plom_create_demo_users

python3 manage.py plom_demo_spec
python3 manage.py plom_preparation_test_source upload -v 1 useful_files_for_testing/test_version1.pdf
python3 manage.py plom_preparation_test_source upload -v 2 useful_files_for_testing/test_version2.pdf

python3 manage.py plom_preparation_prenaming --enable
python3 manage.py plom_preparation_classlist upload useful_files_for_testing/cl_good.csv
python3 manage.py plom_preparation_qvmap generate

# WebPlom needs a Huey consumer running in order to complete some background tasks.
# In a separate terminal window, call:
# `python3 manage.py djangohuey`

# This is for production use, when Debug = False
# python3 manage.py collectstatic

python3 manage.py runserver
