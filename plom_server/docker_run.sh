#!/bin/bash
# SPDX-License-Identifier: FSFAP
# Copyright (C) 2023-2024 Edith Coates
# Copyright (C) 2023-2024 Colin B. Macdonald

# A demo
# python3 manage.py plom_demo --no-waiting

# set server binding port
if [[ -z $PLOM_PUBLIC_FACING_PORT ]]; then
    PORT="8000"
else
    PORT=$PLOM_PUBLIC_FACING_PORT
fi

# A basic server
if [[ "$PLOM_DEBUG" -eq 0 ]]
then
    python3 manage.py plom_init --no-waiting
    gunicorn Web_Plom.wsgi --bind 0.0.0.0:$PORT
else
    python3 manage.py collectstatic --clear --no-input
    python3 manage.py plom_init --no-waiting
    python3 manage.py runserver 0.0.0.0:$PORT
fi

# Some stuff for making a basic server
# ------------------------------------
# One way to run this is to copy this script into a working dir then
# podman run -it --rm -p 41983:8000 -v $PWD:/exam/:z --env PLOM_MEDIA_ROOT=/exam/media_root --env PLOM_DATABASE_BACKEND=sqlite plomgrading/server ./docker_run.sh
# or with postgres running locally, which will be needed for huey
# podman run -it --rm -p 41983:8000 -v $PWD:/exam/:z --env PLOM_MEDIA_ROOT=/exam/media_root --env PLOM_DATABASE_HOSTNAME=127.0.0.1 plomgrading/server ./docker_run.sh

# mkdir media_root
# # currently nextgen server needs to be run inside its own source code
# cd /src/plom_server
# python3 manage.py makemigrations
# python3 manage.py migrate
# python3 manage.py createsuperuser --username root --noinput --email root@example.com
# python3 manage.py plom_create_groups
# python3 manage.py shell -c "from django.contrib.auth.models import User, Group; manager_group = Group.objects.get(name='manager'); User.objects.create_user(username='manager', password='1234').groups.add(manager_group)"
#
# # can also use separate terminal: `podman exec -it ... bash -c "cd /src/plomserver; python3 manage.py djangohuey"`
# python3 manage.py shell -c "from Demo.services import DemoProcessesService; proc_service = DemoProcessesService(); huey_worker_proc = proc_service.launch_huey_workers()"
#
# python3 manage.py runserver 0.0.0.0:8000
