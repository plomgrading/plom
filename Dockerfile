# SPDX-License-Identifier: FSFAP
# Copyright (C) 2019-2023 Andrew Rechnitzer
# Copyright (C) 2019-2023 Colin B. Macdonald
# Copyright (C) 2021 Peter Lee
#
# Copying and distribution of this file, with or without modification,
# are permitted in any medium without royalty provided the copyright
# notice and this notice are preserved.  This file is offered as-is,
# without any warranty.

FROM ubuntu:20.04
RUN apt-get -y update && \
    DEBIAN_FRONTEND=noninteractive apt-get -y install tzdata && \
    apt-get --no-install-recommends -y install \
        cmake make g++ git\
        imagemagick \
        openssl \
        dvipng latexmk texlive-latex-extra texlive-fonts-recommended \
        file \
        python3 \
        python3-dev \
        python3-pip \
        python3-setuptools \
        python3-wheel \
        python3-pytest \
        python3-magic && \
    apt-get -yq autoclean

# Note that git is required for pip install of zxingcpp on ubuntu 20.04
# - see https://github.com/zxing-cpp/zxing-cpp/issues/489

# file-magic: https://gitlab.com/plom/plom/-/issues/1570

COPY requirements.txt /src/
WORKDIR /src
RUN pip install --no-cache-dir -r requirements.txt

# Because source includes the PyQt client, we need minimal deps for Qt.
# For example, to install PyQt and run tests
RUN apt-get -y update && \
    apt-get --no-install-recommends -y install libglib2.0-0 libgl1-mesa-glx && \
    apt-get -yq autoclean

COPY . /src
WORKDIR /src
RUN pip install .

EXPOSE 41984

RUN mkdir /exam
WORKDIR /exam
CMD ["plom-demo"]
