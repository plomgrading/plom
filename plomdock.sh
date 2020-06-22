#!/bin/sh

# Instructions
# ------------
#
# First, build plomdockerbuild by running:
#   `sudo docker build . --tag plomship`
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
#sudo docker stop $PD
#sudo docker rm $PD

mkdir -p plom

# docker pull ${BASEIMG}
sudo docker run -p 41984:41984 --name=$PD --detach --init --env=LC_ALL=C.UTF-8 --volume=$PWD/plom:/plom:z ${BASEIMG} sleep inf
sudo docker exec $PD adduser -u $UID --no-create-home --disabled-password --gecos "" $USER

IP=`sudo docker inspect -f "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}" $PD`
#sed -i "s/127.0.0.1/${IP}/" plom/todo/foo.json
echo "Server IP is ${IP}"
sudo docker exec --user $USER $PD bash -c "cd /plom; plom-demo"
