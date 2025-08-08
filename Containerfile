# SPDX-License-Identifier: FSFAP
# Copyright (C) 2019-2023 Andrew Rechnitzer
# Copyright (C) 2019-2025 Colin B. Macdonald
# Copyright (C) 2021 Peter Lee
# Copyright (C) 2023 Julian Lapenna
#
# Copying and distribution of this file, with or without modification,
# are permitted in any medium without royalty provided the copyright
# notice and this notice are preserved.  This file is offered as-is,
# without any warranty.

FROM ubuntu:24.04
RUN apt-get -y update && \
    DEBIAN_FRONTEND=noninteractive apt-get -y install tzdata && \
    apt-get --no-install-recommends -y install \
        cmake make g++ \
        openssl \
        dvipng latexmk texlive-latex-extra texlive-fonts-recommended texlive-pictures \
        libpango-1.0-0 libpangocairo-1.0-0 \
        file \
        python3 \
        python3-dev \
        python3-pip \
        python3-setuptools \
        python3-wheel \
        python3-pytest \
        python3-magic && \
    apt-get -yq autoclean

# file-magic: https://gitlab.com/plom/plom/-/issues/1570

COPY requirements.txt /src/
WORKDIR /src
ENV PIP_BREAK_SYSTEM_PACKAGES=1
# RUN pip install -U --no-cache-dir pip
# --ignore-installed: don't try to uninstall system packages (i.e., "packaging")
RUN pip install --no-cache-dir --ignore-installed -r requirements.txt

# Minimal deps for Qt, e.g., to support installing client inside container for testing
RUN apt-get -y update && \
    apt-get --no-install-recommends -y install libglib2.0-0 libgl1 libxcb-cursor0 \
    libegl1 libxkbcommon0 libdbus-1-3 && \
    apt-get -yq autoclean

COPY . /src
WORKDIR /src
RUN pip install --no-cache-dir .

EXPOSE 41984

RUN mkdir /exam
WORKDIR /exam
CMD ["plom-new-server"]
