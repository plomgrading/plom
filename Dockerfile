# SPDX-License-Identifier: FSFAP
# Copyright (C) 2019-2020 Andrew Rechnitzer
# Copyright (C) 2019-2020 Colin B. Macdonald
#
# Copying and distribution of this file, with or without modification,
# are permitted in any medium without royalty provided the copyright
# notice and this notice are preserved.  This file is offered as-is,
# without any warranty.

FROM ubuntu:19.10
RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y tzdata

# Note: Ubuntu ships "python3-opencv" but pip will later grab "opencv_python" anyway

RUN apt-get --no-install-recommends --yes install  \
    cmake make imagemagick g++ openssl \
    python3-passlib python3-pandas python3-pyqt5 python3-pytest \
    python3-pyqrcode python3-png python3-dev \
    python3-pip python3-setuptools python3-wheel python3-pil \
    texlive-latex-extra dvipng latexmk texlive-fonts-recommended \
    python3-tqdm libpango-1.0 libpangocairo-1.0 \
    libzbar0 libjpeg-turbo8-dev libturbojpeg0-dev python3-cffi \
    curl
RUN pip3 install --no-cache-dir --upgrade pip
# TODO: bit odd to CI-only deps here? (curl)

# TODO: advantages/disadvanages of using requirements.txt here?

RUN pip3 install --no-cache-dir \
    pymupdf weasyprint imutils lapsolver peewee toml \
    requests requests-toolbelt aiohttp pyzbar jpegtran-cffi \
    imutils tensorflow lapsolver opencv-python \
    packaging pyinstaller


# TODO: so much stuff listed explicitly: help me!
# TODO: I want to install Plom (from current dir) into the Docker image...
# TODO: don't need/want /src in the docker image
COPY setup.py README.md org.plomgrading.PlomClient.* /src/
COPY plom/ /src/plom/
WORKDIR /src
RUN pip3 install .
