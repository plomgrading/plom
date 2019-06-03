#!/bin/sh

export BRANCH=dev

#before_install:
# TODO: on gitlab CI, we would have the appropriate commit checked out in `MLP`?
git clone https://gitlab.math.ubc.ca/andrewr/MLP.git plom
cd plom
git checkout $BRANCH

# TODO: use `ubuntu:latest` or `ubuntu:18.04` instead
# TODO: mtmiller/octave has some our deps already, so faster pull
docker pull mtmiller/octave
docker run --name=plom0 --detach --init --env=LC_ALL=C.UTF-8 --volume=$PWD:/plom:z mtmiller/octave sleep inf

# TODO: could also clone within the docker image:
#docker exec plom0 git clone https://gitlab.math.ubc.ca/andrewr/MLP.git
#docker exec plom0 cd MLP; git check dev

#install:
docker exec plom0 apt-get update
# prevent some interactive nonsense about timezones
docker exec plom0 env DEBIAN_FRONTEND=noninteractive apt-get install -y tzdata
docker exec plom0 apt-get --no-install-recommends --yes install  \
    parallel zbar-tools \
    python3-passlib python3-seaborn python3-pandas python3-pyqt5 \
    python3-pyqt5.qtsql python3-peewee python3-pyqrcode python3-png

# TODO: cmake dep missing in lapsolver: file upstream?
docker exec plom0 pip3 install wsgidav easywebdav2 pymupdf \
                               weasyprint imutils lapsolver

#script:
# TODO: something like:
docker exec plom0 cd /plomsrc/build; python3 editMeToBuildASpec.py

#after_script:
docker stop plom0
docker rm plom0
