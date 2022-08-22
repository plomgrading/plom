#!/bin/sh

set -e

rm -f db.sqlite3

#python3 manage.py makemigrations TestCreator Preparation
#python3 manage.py makemigrations Connect
python3 manage.py makemigrations
python3 manage.py migrate

# new thing to try #90
#python3 manage.py reset_migrations Authentication Preparation TestCreator


# old way, have to type password every time
#python3 manage.py createsuperuser --username cbm  --email foo@bar.com

python3 manage.py plom_create_groups
#python3 manage.py creategroups

python3 manage.py plom_create_demo_users

python3 manage.py runserver
