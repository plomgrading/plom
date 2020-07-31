#!/bin/sh

# Instructions
# ------------
#
# First, build plomdockerbuild by running:
#   `docker build . --tag plomship`
# in whatever directory has the `Dockerfile` in it.  For example, inside your
# git clone and in whatever branch you want; change --tag name if you want.
#
# Next, copy this script somewhere
#   `cp plomdock.sh ${HOME}/plomdock/`
#   `cd ${HOME}/plomdock`
#
# Adjust ports: notation is `host_port:container_port`.
#
# Run this script.

export BASEIMG=plomship
export PD=plom0
export UID=`id -u`

# Take it down
 #rm -rf plom
#docker stop $PD
#docker rm $PD

mkdir -p plom

# docker pull ${BASEIMG}
docker run -p 41984:41984 --name=$PD --detach --init --env=LC_ALL=C.UTF-8 --volume=$PWD/plom:/plom:z ${BASEIMG} sleep inf
docker exec $PD adduser -u $UID --no-create-home --disabled-password --gecos "" $USER

docker exec --user $USER $PD bash -c "cd /plom; plom-demo"
