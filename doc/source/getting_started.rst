.. Plom documentation
   Copyright 2021 Colin B. Macdonald
   SPDX-License-Identifier: AGPL-3.0-or-later

Getting started with Plom
=========================

So you want to use Plom to grade some papers?
You probably want to start with the Plom Client, which can be
obtained in several ways:

* GNU/Linux users can install `from Flathub`_.
* Compiled binaries are available from our `releases page`_.
* Install from source or using `pip`.

.. _from Flathub: https://flathub.org/apps/details/org.plomgrading.PlomClient
.. _releases page: https://gitlab.com/plom/plom/-/releases/


macOS binary
------------

The macOS client ships as a .zip file.
* Open the .zip file and drag the .app bundle out onto your desktop or into your Applications folder. You can then delete the .zip file if you wish.
* Unfortunately the .app is not “signed” which means you will likely get a security warning preventing you from opening it. If that happens you may need to change something in “Privacy & Security” in “System Preferences”, see `Issue #1676`_ for details.

.. _Issue #1676: https://gitlab.com/plom/plom/-/issues/1676 for details.


Windows binary
--------------

Locate the .exe file on your computer and double-click on it.


Linux binary
------------

You’ll need to change the permissions on the binary before you can run it: open a terminal and go to the directory where you saved the binary::

  chmod u+x PlomClient-x.y.z-linux-centos7.bin
  ./PlomClient-x.y.z-linux-centos7.bin


Running your own server
-----------------------

Plom consists of several components.  One of these is the Plom server, used both for preparing new tests and for coordinating grading.



