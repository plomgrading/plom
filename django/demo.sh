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

python3 manage.py makemigrations
python3 manage.py migrate

# Plom-classic commands. Will fail gracefully if there is no core server connection
# TODO: needs to have PYTHON_PATH hacked or Plom classic installed
PLOMDIR=webplom_classic_server
PLOMPORT=41984
rm -rf $PLOMDIR
python3 -m plom.server init $PLOMDIR --manager-pw 1234
python3 -m plom.server launch $PLOMDIR &
python3 manage.py plom_connect server --name localhost --port $PLOMPORT
python3 manage.py plom_connect manager

python3 manage.py plom_create_groups

python3 manage.py plom_create_demo_users

python3 manage.py plom_demo_spec
python3 manage.py plom_preparation_test_source upload -v 1 useful_files_for_testing/test_version1.pdf
python3 manage.py plom_preparation_test_source upload -v 2 useful_files_for_testing/test_version2.pdf

python3 manage.py plom_preparation_prenaming --enable
python3 manage.py plom_preparation_classlist upload useful_files_for_testing/cl_good.csv
python3 manage.py plom_preparation_qvmap generate

# will fail gracefully if a core server isn't connected
python3 manage.py plom_connect send all

# This is for production use, when Debug = False
# python3 manage.py collectstatic

python3 manage.py runserver
