#!/bin/sh

# Instructions
# ------------
#
# First, build plomdockerbuild by running:
#   `sudo docker build . --tag plomdockerbuild`
# in whatever directory has the `Dockerfile` in it.
# (for example, inside your git clone)
#
# Next, copy this script somewhere
#   `cp plomdock.sh ${HOME}/plomdock/`
#   `cd ${HOME}/plomdock`
#
# Run this script

export BRANCH=master
export BASEIMG=plomdockerbuild
export MINTESTDATA=${HOME}/tmp/dockerHack/minTestServerData
export UID=`id -u`

#before_install:
git clone https://gitlab.math.ubc.ca/andrewr/MLP.git plomsrc
cd plomsrc
git checkout $BRANCH
cd ..
# make fresh copy
rm -rf plom
/bin/cp -ra plomsrc plom

# docker pull ${BASEIMG}
sudo docker run -p 41984:41984 -p 41985:41985 --name=plom0 --detach --init --env=LC_ALL=C.UTF-8 --volume=$PWD/plom:/plom:z ${BASEIMG} sleep inf
sudo docker exec plom0 adduser -u $UID --no-create-home --disabled-password --gecos "" $USER

# TODO: could also clone within the docker image:
#docker exec plom0 git clone https://gitlab.math.ubc.ca/andrewr/MLP.git plom
#docker exec plom0 bash -c "cd plom; git check ${BRANCH}"

#install:
# docker exec plom0 apt-get update
# # prevent some interactive nonsense about timezones
# docker exec plom0 env DEBIAN_FRONTEND=noninteractive apt-get install -y tzdata
# docker exec plom0 apt-get --no-install-recommends --yes install  \
#     parallel zbar-tools cmake \
#     python3-passlib python3-seaborn python3-pandas python3-pyqt5 \
#     python3-pyqt5.qtsql python3-pyqrcode python3-png \
#     python3-pip python3-setuptools python3-wheel imagemagick \
#     texlive-latex-extra dvipng g++ make python3-dev
#
# docker exec plom0 pip3 install --upgrade \
#        wsgidav easywebdav2 pymupdf weasyprint imutils \
#        lapsolver peewee cheroot

#script:
mkdir plom/scanAndGroup/scannedExams/
mkdir plom/imageServer/markingComments
mkdir plom/imageServer/markedPapers
/bin/cp -fa $MINTESTDATA/resources/* plom/resources/
/bin/cp -a $MINTESTDATA/*.pdf plom/scanAndGroup/scannedExams/
sudo docker exec --user $USER plom0 bash -c "cd plom/scanAndGroup; python3 03_scans_to_page_images.py"
sudo docker exec --user $USER plom0 bash -c "cd plom/scanAndGroup; python3 04_decode_images.py"
sudo docker exec --user $USER plom0 bash -c "cd plom/scanAndGroup; python3 05_missing_pages.py"
sudo docker exec --user $USER plom0 bash -c "cd plom/scanAndGroup; python3 06_group_pages.py"
# TODO: add IDing NN later?  this replaces prediction list and classlist

# Server stuff
IP=`sudo docker inspect -f "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}" plom0`
sed -i "s/127.0.0.1/${IP}/" plom/resources/serverDetails.json
# TODO: chmod 644 mlp.key?
# TODO: permission error on server.log on 18k1-cbm1.math.ubc.ca
echo "Server IP is ${IP}"
sudo docker exec --user $USER plom0 bash -c "cd plom/imageServer; python3 image_server.py"

#after_script:
# sudo docker stop plom0
# sudo docker rm plom0
