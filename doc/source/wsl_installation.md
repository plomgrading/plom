<!--
__copyright__ = "Copyright (C) 2021-2026 Colin B. Macdonald"
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

Note administrative access is needed, at least for the initial install.


## Getting the Plom source code

Within WSL, use `git clone` to get the source code from
[https://gitlab.com/plom/plom](the GitLab repo).  You may also want
`plom-client` and `plom-common`.


## Installing Plom dependencies

These instructions assume you are running Ubuntu 26.04 on WSL,
and were last tested roughly in summer 2026.

TODO: these should be updated for current Django-based Plom Server.

1.  First install some dependencies from the package manager
    ```
    sudo apt update
    sudo apt install \
            cmake make g++ dvipng \
            python3-passlib python3-pandas python3-pytest \
            python3-pyqt6 python3-pyqt6.qtsvg pyqt6-dev-tools \
            python3-dev python3-pip python3-setuptools python3-wheel \
            python3-requests-toolbelt texlive-latex-extra \
            latexmk texlive-fonts-recommended python3-pillow
    ```
    (These may be out of date: compare to the instructions for Ubuntu elsewhere).
2.  `python3 -m pip install --upgrade --user pip` (unlikely needed in 2026).
3.  `pip install --break-system-packages -e .` from inside
    the Plom source tree) should pull in the remaining dependencies.
4.  [This bit unconfirmed in 2026]
    Like regular Ubuntu, this seems to lack `~/.local/bin` in the path so
    you may not be able to run `plom-client`.
      - You can try `~/.local/bin/plom-client` to see if things are working
        without messing around with such config files.
      - You can use `python3 -m plom.client` instead.
      - Or you can modify the `PATH` environment variable in a
        `bash` startup file... something like adding
        `export PATH=$PATH:~/.local/bin` to the file `.bash_profile`,
        (You might need to create that file, e.g., with `nano .bash_profile`.)


## Installing VSCode

Install VSCode as per instructions elsewhere.  On the host OS (Windows) *not inside WSL*.

Install the "WSL Extension" in VSCode.

Now start WSL.  Go to the Plom source code (typically the directory
called `plom`) and type `code .`.
The first time this will install some server that is used to connect
VSCode to WSL (similar to developing on a remote machine).



## Installing and configuring Postgres

TODO: Probably this was a standard postgres install on Ubuntu, via `apt`...  To be confirmed.

#### Configure the postgres server:

Open WSL, then type `psql postgres`.  At the prompt do:
```
ALTER USER postgres WITH PASSWORD 'postgres';
CREATE DATABASE plom_db;
GRANT ALL PRIVILEGES ON DATABASE plom_db to postgres;
QUIT
```
Not sure why the database is `plom_db` is created here: the demo is supposed to do that.
Colin suspects the `ALTER USER` is the important part of this.
No idea is this is good security practice or not: use this only for the demo.



## Launching the demo

The code for launching the Plom demo is changing but generally you
should be able to launch it from within the terminal built-in to
VSCode.  Alternatively, you can launch it from inside WSL.



## Questions

* Do we need Git installed on the Windows host or can we just use the WSL git?
  Probably WSL, but haven't checked.  In summer 2026, we had trouble/confusion
  about which `git` VSCode was running.
* Do we need Python installed on the Windows host?  Probably not.
