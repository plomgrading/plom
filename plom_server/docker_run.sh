#!/bin/bash
# SPDX-License-Identifier: FSFAP
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

python3 manage.py plom_demo --no-waiting
python3 manage.py runserver 0.0.0.0:8000

# Some stuff for making a basic server
# TODO: needs huey stuff
# python3 manage.py makemigrations
# python3 manage.py migrate
# python3 manage.py createsuperuser --username root --noinput --email root@example.com
# python3 manage.py plom_create_groups
# python3 manage.py shell -c "from django.contrib.auth.models import User, Group; manager_group = Group.objects.get(name='manager'); User.objects.create_user(username='manager', password='1234').groups.add(manager_group)"
