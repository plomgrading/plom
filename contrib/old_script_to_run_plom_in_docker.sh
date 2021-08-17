#!/bin/sh

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2021 Colin B. Macdonald
# Copyright (C) 2020 Andrew Rechnitzer

# Instructions
# ------------
#
# This script runs a Plom demo in a Docker container.  Not sure its useful
# compared to `docker run -it --rm -p ... -v ... plomgrading/server plom-demo`
# but it remains here for reference.
#
# Copy this script somewhere
#   `cp plomdock.sh ${HOME}/plomdock/`
#   `cd ${HOME}/plomdock`
#
# Adjust ports: notation is `host_port:container_port`.
#
# Run this script.
#
# If you wish, you can build your own local docker:
#   `docker build . --tag plomship`
# in the plom source directory, where the `Dockerfile` is.

# Official docker image
export BASEIMG=docker.io/plomgrading/server
# Local image:
#export BASEIMG=plomship
# Current main branch:
#export BASEIMG=registry.gitlab.com/plom/plom:master

export PD=plom0
export UID=`id -u`

mkdir -p plom

docker pull ${BASEIMG}
docker run -p 41984:41984 --name=$PD --detach --init --env=LC_ALL=C.UTF-8 --volume=$PWD/plom:/plom:z ${BASEIMG} sleep inf
docker exec $PD adduser -u $UID --no-create-home --disabled-password --gecos "" $USER

docker exec --user $USER $PD bash -c "cd /plom; plom-demo"

# Take it down
#docker stop $PD
#docker rm $PD
#rm -rf plom
