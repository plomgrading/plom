# SPDX-License-Identifier: FSFAP
# Copyright (C) 2019-2020 Andrew Rechnitzer
# Copyright (C) 2019-2020 Colin B. Macdonald
#
# Copying and distribution of this file, with or without modification,
# are permitted in any medium without royalty provided the copyright
# notice and this notice are preserved.  This file is offered as-is,
# without any warranty.

FROM ubuntu:18.04
RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y tzdata

RUN apt-get --no-install-recommends --yes install  \
    cmake make imagemagick g++ openssl \
    texlive-latex-extra dvipng latexmk texlive-fonts-recommended \
    libpango-1.0 libpangocairo-1.0 \
    libzbar0 libjpeg-turbo8-dev libturbojpeg0-dev libjpeg-dev \
    python3 python3-pip python3-dev python3-setuptools python3-wheel \
    python3-pytest

RUN pip3 install --no-cache-dir --upgrade pip
# Note: `python3 -m pip` used below on old Ubuntu 18.04

# install cffi first: https://github.com/jbaiter/jpegtran-cffi/issues/27
RUN python3 -m pip install --no-cache-dir cffi==1.14.0 pycparser==2.20
COPY requirements.txt /src/
WORKDIR /src
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# client dependency: keep in image for now after others so easy to discard
RUN apt-get --no-install-recommends --yes install python3-pyqt5

# TODO: I want to install Plom (from current dir) into the Docker image...
# TODO: don't need/want /src in the docker image
COPY setup.py README.md org.plomgrading.PlomClient.* /src/
COPY plom/ /src/plom/
WORKDIR /src
RUN python3 -m pip install .
