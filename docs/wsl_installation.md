<!--
__copyright__ = "Copyright (C) 2021-2022 Colin B. Macdonald"
__copyright__ = "Copyright (C) 2021 Jalal Khouhak"
__license__ = "AGPL-3.0-or-later"
 -->

Installing Plom via WSL on Windows
==================================

These instructions are for getting a development environment, or perhaps for hosting a **Plom Server** on Windows.
If you only want to grade some papers, then you don't need all this, instead go to https://plomgrading.org and follow instructions for getting started with a **Plom Client**.

**Plom** has been developed primarily on Unix systems: here we discuss how it can be used on Windows system using **WSL**: *"Windows subsystem for Linux"*.

## Getting WSL

There are several options for installing WSL. Go to https://docs.microsoft.com/en-us/windows/wsl/install-win10 and then you can find detailed information.


## Installing Plom dependencies

These instructions assume you are running Ubuntu 20.04 on WSL.
1. First install some dependencies from the package manager
```
sudo apt update
sudo apt install \
        cmake make imagemagick dvipng g++ openssl \
        libzbar0 libjpeg-turbo8-dev libturbojpeg0-dev python3-cffi \
        python3-passlib python3-pandas python3-pyqt5 python3-pytest \
        python3-dev python3-pip python3-setuptools python3-wheel \
        python3-requests-toolbelt texlive-latex-extra \
        latexmk texlive-fonts-recommended python3-pil \
        python3-tqdm python3-toml \
        libpango-1.0-0 libpangocairo-1.0-0
```
2. `python3 -m pip install --upgrade --user setuptools`
3. `pip3 install --user testresources`
4.  Some libraries that are either not in package manager or are too old
```
python3 -m pip install --upgrade --user pymupdf weasyprint imutils \
        aiohttp pyzbar jpegtran-cffi peewee \
        lapsolver opencv-python-headless
```
5. `pip3 install --user plom`
6. Seems to have the same lack of `~/.local/bin` in path, just like on regular Ubuntu.


## TODO list

  * what is `testresources` for?
  * Liam mentioned some IP thing needed
  * Point users to a soln for the `.local/bin` in Path problem.
