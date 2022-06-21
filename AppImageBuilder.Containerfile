# SPDX-License-Identifier: FSFAP
# Copyright (C) 2022 Colin B. Macdonald
#
# Copying and distribution of this file, with or without modification,
# are permitted in any medium without royalty provided the copyright
# notice and this notice are preserved.  This file is offered as-is,
# without any warranty.

# This container builds Plom's AppImage, a portable single-file for GNU/Linux
#
# I first tried `FROM appimage-builder` but failed with fontconfig errors.
#
# Instead of running this file you can execute the commands interactively,
# e.g., inside `podman run -it --rm -v ./:/media:z ubuntu:20.04`.
#
# TODO: what bits of our source code to put in src?


FROM ubuntu:20.04
RUN apt-get -y update && \
    DEBIAN_FRONTEND=noninteractive apt-get -y install tzdata && \
    apt-get install -y python3-dev && \
    apt-get install -y python3-pip \
        python3-setuptools patchelf desktop-file-utils libgdk-pixbuf2.0-dev \
        fakeroot strace fuse \
        gtk-update-icon-cache \
        wget

# too old?  errors on validating our file
# RUN apt-get -y install appstream

RUN wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage -O /usr/local/bin/appimagetool && \
    chmod +x /usr/local/bin/appimagetool

RUN python3 -m pip install --upgrade pip
RUN pip install appimage-builder

COPY AppImageBuilder.yml /app/
COPY . /app/src/
WORKDIR /app

# Note tests require a display and an user to click close the app
RUN APPIMAGE_EXTRACT_AND_RUN=1 appimage-builder --skip-tests

# To get it out, something like:
# docker create -ti --name dummy IMAGE_NAME bash
# docker cp dummy:/app/PlomClient... .
# docker rm -f dummy
# https://stackoverflow.com/questions/22049212/docker-copying-files-from-docker-container-to-host
