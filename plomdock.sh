#!/bin/sh

# Instructions
# ------------
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

# semi-regularly updated devel version:
export BASEIMG=docker.io/cbm755/plom:devel
# Local image:
#export BASEIMG=plomship
# Current main branch:
#export BASEIMG=registry.gitlab.com/plom/plom:master
# Official docker image, TODO: coming soon:
#export BASEIMG=docker.io/plomgrading/plom

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
