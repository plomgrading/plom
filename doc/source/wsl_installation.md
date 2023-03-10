<!--
__copyright__ = "Copyright (C) 2021-2022 Colin B. Macdonald"
__copyright__ = "Copyright (C) 2021 Jalal Khouhak"
__license__ = "AGPL-3.0-or-later"
 -->

Installing from source on WSL on Windows
========================================

These instructions are for getting a development environment, or perhaps for hosting a **Plom Server** on Windows.
If you only want to grade some papers, then you don't need all this; instead
go to [plomgrading.org](https://plomgrading.org) and follow instructions for
getting started with a **Plom Client**.

Plom has been developed primarily on Unix systems: here we discuss how it
can be used on Microsoft Windows using Windows Subsystem for Linux (WSL).


## Getting WSL

Go to https://docs.microsoft.com/en-us/windows/wsl/install
for detailed information.


## Installing Plom dependencies

These instructions assume you are running Ubuntu 20.04 on WSL.
1.  First install some dependencies from the package manager
    ```
    sudo apt update
    sudo apt install \
            cmake make imagemagick dvipng g++ openssl \
            libjpeg-turbo8-dev libturbojpeg0-dev \
            python3-passlib python3-pandas python3-pyqt5 python3-pytest \
            python3-dev python3-pip python3-setuptools python3-wheel \
            python3-requests-toolbelt texlive-latex-extra \
            latexmk texlive-fonts-recommended python3-pil \
            python3-tqdm python3-toml \
            libpango-1.0-0 libpangocairo-1.0-0
    ```
    (These may be out of date: compare to the instructions for Ubuntu elsewhere).
2.  `python3 -m pip install --upgrade --user pip`
2.  `pip install --upgrade --user setuptools`
3.  `pip install --user plom` (or `pip install --user .` from inside
    the Plom source tree) should pull in the remaining dependencies.
4.  Like regular Ubuntu, this seems to lack `~/.local/bin` in the path so
    you may not be able to run `plom-server`.  Probably you need to modify
	the `PATH` environment variable in a bash startup file.


TODO: Liam mentioned some IP thing is also needed?  If you dear reader
know what this is, please file an issue.
