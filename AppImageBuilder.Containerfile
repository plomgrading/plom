# SPDX-License-Identifier: FSFAP
# Copyright (C) 2022-2023 Colin B. Macdonald
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
# Do we want to keep Ubuntu back on 20.04 to have earliest supported OS?
#
# TODO: what bits of our source code to put in src?


# from "breeze-icon-theme" onward is copy-paste from appimage-builder-1.1.0:
FROM ubuntu:20.04
RUN apt-get -y update && \
    DEBIAN_FRONTEND=noninteractive apt-get -y install tzdata && \
    apt-get install -y python3-dev && \
    apt-get install -y \
        fuse \
        bash \
        coreutils \
        binutils \
        util-linux \
        patchelf \
        squashfs-tools && \
   apt-get install -y \
        breeze-icon-theme \
        desktop-file-utils \
        elfutils \
        fakeroot \
        file \
        git \
        gnupg2 \
        gtk-update-icon-cache \
        libgdk-pixbuf2.0-dev \
        libglib2.0-bin \
        librsvg2-dev \
        libyaml-dev \
        python3 \
        python3-pip \
        python3-setuptools \
        strace \
        wget \
        zsync && \
    apt-get -yq autoclean

# used to get errors on validating our file
RUN apt-get -y install appstream appstream-util

RUN python3 -m pip install --upgrade pip
RUN pip install appimage-builder>=1.1.0

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
