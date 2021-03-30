.. Plom documentation master file
   Copyright 2020 Colin B. Macdonald
   SPDX-License-Identifier: AGPL-3.0-or-later

Welcome to Plom's documentation!
================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   getting_started.rst

   install.rst

   code.rst


.. automodule:: plom


The Plom code is organized into several main modules.

  * `plom.client`

    .. automodule:: plom.client
        :members:

  * `plom.server`

    .. automodule:: plom.server

  * Tools for producing papers, scanning papers, and finishing the grading process.

    .. automodule:: plom.produce

    .. automodule:: plom.finish

    .. automodule:: plom.finish

  * Other supporting code

    .. automodule:: plom.db
    .. automodule:: plom.manager


TeX Tools
---------

.. automodule:: plom.textools
    :members:


Plom Build
----------

.. automodule:: plom.produce
    :members:

.. automodule:: plom.produce.faketools
    :members:

TODO: our modules don't seem to have enough of their contents in the
actual modules so `automodule` doesn't pick up much...


Plom client
-----------

.. automodule:: plom.client
    :members:
.. automodule:: plom.client.annotator
    :members:


TODO: new sphinx deps
=====================

Fedora: `dnf install python3-recommonmark python3-sphinx`, others


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
