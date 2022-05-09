.. Plom documentation
   Copyright 2020-2022 Colin B. Macdonald
   Copyright 2020 Andrew Rechnitzer
   SPDX-License-Identifier: AGPL-3.0-or-later

Installing the Plom Server
==========================

The instructions here are for the installation of a Plom server.
This **not** required by your markers; they only need to
:doc:`install the Plom client <install-client>`.

You can either use containers to run a server or install Plom from source.


Container images
----------------

Use either `Podman` or `Docker` to download the latest container image and
launch it::

    docker pull plomgrading/server
    docker run -it --rm -p 41984:41984 plomgrading/server

By default, this will launch the demo server.

.. TODO
   document the demo?
   also: fix references to plom-build -> plom-create

The data for the test is in `/exam` inside the Docker image.  You can use your
own local directory with `-v`::

    mkdir my_test
    docker run -it --rm -P -v $PWD/my_test:/exam plomgrading/server

(here `-P` will use a random high port on the host).

You can override the default command, for example::

    docker run -it --rm -v $PWD/my_test:/exam plomgrading/server plom-build new --demo
    docker run -it --rm -v $PWD/my_test:/exam plomgrading/server plom-server init
    docker run -it --rm -v $PWD/my_test:/exam plomgrading/server plom-server users --demo
    docker run -it --rm -P -v $PWD/my_test:/exam plomgrading/server plom-server launch

Alternatively you can get a shell and work inside the image::

    docker run -it --rm plomgrading/server /bin/bash
    plom-build new --demo


You can also connect a shell to a *running image* using `exec`::

    docker exec -it <name> /bin/bash

where `<name>` can found using ``docker ps``; its something like
`ornery_colin`.


Installation using ``pip``
--------------------------

In theory this should be simply::

    pip install plom

but in practice, there are some caveats:

* you may need to upgrade your `pip`, especially if your system
  if a few years old.  Try ``python3 -m pip install --upgrade pip``.
* your system may need additional dependencies from your system
  package manager (``dnf``, ``apt``, etc).

.. note::

   **TODO**: it would be good to document this better!
   For now, see :doc:`install-from-source`.
   It may also be useful to `examine the Containerfile in the source
   code <https://gitlab.com/plom/plom/-/blob/main/Dockerfile>`_.


After installing, you should be able to run the various Plom commands.
Try running `plom-server` and you should see something like::

    $ plom-server --version
    plom-server 0.8.11