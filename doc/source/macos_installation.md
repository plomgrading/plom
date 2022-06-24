<!--
__copyright__ = "Copyright (C) 2018 Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2022 Colin B. Macdonald"
__copyright__ = "Copyright (C) 2020 Victoria Schuster"
__license__ = "AGPL-3.0-or-later"
 -->

Installing from source on MacOS
===============================

Tested on Catalina 10.15.4.
First some stuff from a package manager, here using [Homebrew](https://brew.sh):

```
$ brew install libjpeg libjpeg-turbo jpeg-turbo imagemagick zbar \
               libffi jsmin python3 openssl cmake pango
```

TODO: are those really the only dependencies, no latex for example?
Older instructions suggested `pip3 install tex`: does that really work?

At this point `pip install plom` (or `pip install --user .` from inside
the Plom source tree) should pull in the remaining dependencies.
