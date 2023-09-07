#!/bin/bash
# SPDX-License-Identifier: FSFAP
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

# A demo
python3 manage.py plom_demo --no-waiting --quick
python3 manage.py runserver 0.0.0.0:8000

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
# # one can also do this in a separate terminal connected with `podman exec -it ...`
# python3 manage.py shell -c "import Demo.servers DemoProcessesService; proc_service = DemoProcessesService(); huey_worker_proc = proc_service.launch_huey_workers()"
#
# python3 manage.py runserver 0.0.0.0:8000
