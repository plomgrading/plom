.. Plom documentation
   Copyright (C) 2021-2023 Colin B. Macdonald
   Copyright (C) 2024 Bryan
   SPDX-License-Identifier: AGPL-3.0-or-later

Installing the Plom Client
==========================

If you just need to use Plom to grade some papers then you only need the Plom Client.
This can be obtained in several ways:

* GNU/Linux users can install `from Flathub`_.
* Compiled binaries are available from our `releases page`_.
* Install from source or using `pip`.

.. _from Flathub: https://flathub.org/apps/org.plomgrading.PlomClient
.. _releases page: https://gitlab.com/plom/plom/-/releases/


For macOS
---------

Download the appropriate "Compiled client" for your version of macOS
from our `releases page`_.

The macOS client ships as a ``.zip`` file.  Open it and drag the ``.app``
bundle out onto your desktop or into your Applications folder.  You can
then delete the ``.zip`` file if you wish.

.. note::

    Unfortunately the .app is not “signed” which means you will likely
    get a security warning preventing you from opening it.  You may
    need to change something in “Privacy & Security” in “System
    Preferences”, see `Issue #1676`_ for details.

    .. _Issue #1676: https://gitlab.com/plom/plom/-/issues/1676


For Windows
-----------

Download the "Compiled client for Windows" from our `releases page`_.

Locate the ``.exe`` file on your computer and double-click on it.

(You may get warnings about unsigned files, but it should be possible to
continue.  You can check the md5sums in our `releases page`_ if you
want to verify your download.)


For GNU/Linux
-------------

Users of various distributions can install `from Flathub`_.

.. _from Flathub: https://flathub.org/apps/org.plomgrading.PlomClient

Another option is to download the "AppImage" from our `releases page`_.

You may need to change the permissions on the binary to make it executable.
Open a terminal and go to the directory where you saved the binary::

  chmod +x PlomClient-x.y.z-x86_64.AppImage
  ./PlomClient-x.y.z-x86_64.AppImage


For ChromeOS (Chromebook)
-------------------------

In theory, installing via Flathub should work, but in practice it does
not (`Issue #3131`_).

It is still possible to install Plom Client by first
`enabling the Linux container <https://support.google.com/chromebook/answer/9145439?hl=en>`_
on your Chromebook.
Then we install some of the dependencies manually in the terminal::

  apt install python3-pyqt6 python3-pyqt6.qtsvg pyqt6-dev-tools \
      python3-platformdirs python3-packaging python3-requests-toolbelt \
      python3-tomlkit python3-tqdm python3-arrow


.. note::

    It is important to install ``PyQt6`` using ``apt``, rather than with
    ``pip``: the latter will hit (as of Nov 2024) the same
    `Issue #3131`_ mentioned above.

    .. _Issue #3131: https://gitlab.com/plom/plom/-/issues/3131

Next we install some dependencies that are not available in Debian 12.8, again
using the terminal:
``pip --break-system-packages install pyspellchecker``
(yes that looks scary: feel free to learn about ``venv`` instead if you wish).

Finally you can type ``pip install --no-deps --break-system-packages
plom``.  The reason for ``--no-deps`` is because we want to avoid
installing all the dependencies for the Plom Server.  In the future,
we intend to decouple the client and server packages.

To launch Plom Client, open the terminal and type::

  ./local/bin/plom-client

or::

  python3 -m plom.client
