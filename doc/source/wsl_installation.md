<!--
__copyright__ = "Copyright (C) 2021-2025 Colin B. Macdonald"
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

Go to [https://learn.microsoft.com/en-us/windows/wsl/install](https://learn.microsoft.com/en-us/windows/wsl/install)
for detailed information.


## Installing Plom dependencies

These instructions assume you are running Ubuntu 22.04 on WSL,
and were last tested in March 2023.

1.  First install some dependencies from the package manager
    ```
    sudo apt update
    sudo apt install \
            cmake make imagemagick dvipng g++ \
            python3-passlib python3-pandas python3-pytest \
            python3-pyqt6 python3-pyqt6.qtsvg pyqt6-dev-tools \
            python3-dev python3-pip python3-setuptools python3-wheel \
            python3-requests-toolbelt texlive-latex-extra \
            latexmk texlive-fonts-recommended python3-pillow
    ```
    (These may be out of date: compare to the instructions for Ubuntu elsewhere).
2.  `python3 -m pip install --upgrade --user pip`
3.  `pip install --user plom` (or `pip install --user .` from inside
    the Plom source tree) should pull in the remaining dependencies.
4.  Like regular Ubuntu, this seems to lack `~/.local/bin` in the path so
    you may not be able to run `plom-client`.
      - You can try `~/.local/bin/plom-client` to see if things are working
        without messing around with such config files.
      - You can use `python3 -m plomclient.client` instead.
      - Or you can modify the `PATH` environment variable in a
        `bash` startup file... something like adding
        `export PATH=$PATH:~/.local/bin` to the file `.bash_profile`,
        (You might need to create that file, e.g., with `nano .bash_profile`.)
