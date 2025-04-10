<!--
__copyright__ = "Copyright (C) 2018 Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2023, 2025 Colin B. Macdonald"
__copyright__ = "Copyright (C) 2020 Victoria Schuster"
__copyright__ = "Copyright (C) 2023 Julian Lapenna"
__license__ = "AGPL-3.0-or-later"
 -->

Installing from source on MacOS
===============================

Tested on Catalina 10.15.4, in mid 2020.
First some stuff from a package manager, here using [Homebrew](https://brew.sh):

```
brew install cmake pango
```
You will also need Python, perhaps:
```
brew install python3
```
You will also need latex.  Here is one approach:
```
brew install basictex
eval "$(/usr/libexec/path_helper)"
sudo tlmgr update --self
sudo tlmgr install latexmk dvipng preview exam preprint
```
or maybe `brew install mactex-no-gui` or perhaps via some other UI means.

At this point `pip install plom` (or `pip install --user .` from inside
the Plom source tree) should pull in the remaining dependencies.
