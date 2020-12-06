# SPDX-License-Identifier: FSFAP
# Copyright (C) 2019-2020 Andrew Rechnitzer
# Copyright (C) 2019-2020 Colin B. Macdonald
#
# Copying and distribution of this file, with or without modification,
# are permitted in any medium without royalty provided the copyright
# notice and this notice are preserved.  This file is offered as-is,
# without any warranty.

FROM ubuntu:18.04
RUN apt-get -y update && \
    DEBIAN_FRONTEND=noninteractive apt-get -y install tzdata && \
    apt-get --no-install-recommends -y install \
        cmake make g++ \
        imagemagick \
        openssl \
        dvipng latexmk texlive-latex-extra texlive-fonts-recommended \
        libpango-1.0 libpangocairo-1.0 \
        libzbar0 \
        libjpeg-dev \
        libjpeg-turbo8-dev \
        libturbojpeg0-dev \
        python3 \
        python3-dev \
        python3-pip \
        python3-setuptools \
        python3-wheel \
        python3-pytest

RUN pip3 install --no-cache-dir --upgrade pip setuptools
# Note: `python3 -m pip` used below on old Ubuntu 18.04
# Note: need newer setuptools to avoid cairocffi issue

# install cffi first: https://github.com/jbaiter/jpegtran-cffi/issues/27
RUN python3 -m pip install --no-cache-dir cffi==1.14.4 pycparser==2.20
COPY requirements.txt /src/
WORKDIR /src
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# client dependency: keep in image for now after others so easy to discard
RUN apt-get -y update && \
    apt-get --no-install-recommends -y install \
        `apt-cache depends qt5-default  | awk '/Depends:/{print$2}'`

# TODO: I want to install Plom (from current dir) into the Docker image...
# TODO: don't need/want /src in the docker image
COPY setup.py README.md org.plomgrading.PlomClient.* /src/
COPY plom/ /src/plom/
COPY contrib/ /src/contrib/
WORKDIR /src
RUN python3 -m pip install .

EXPOSE 41984

RUN mkdir /exam
WORKDIR /exam
CMD ["plom-demo"]
