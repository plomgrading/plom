.. Plom documentation
   Copyright (C) 2021-2023 Colin B. Macdonald
   Copyright (C) 2024 Aidan Murphy
   SPDX-License-Identifier: AGPL-3.0-or-later

Python modules
==============

The Plom code can be found in one of two places in the project repository:
 - `plom`
 - `plom_server`
The former contains the code used to build the marking client (still in use)
and several tools to run and interact with the "legacy" server.
The latter contains the "current" Plom server, using
`Django <https://www.djangoproject.com>`_.

`plom` itself is a package and can be imported, while `plom_server` is not yet packaged
(though it'd be nice, see issue `#2759 <https://gitlab.com/plom/plom/-/issues/2759>`_).

plom
-----------

.. toctree::
   :maxdepth: 1

   plom/plom.rst

   module-plom-create

   module-plom-scan

   module-plom-solutions

   module-plom-finish

   module-plom-client

   module-plom-legacy-server

   module-plom-db

   module-plom-other

plom_server
-----------

.. toctree::
   :maxdepth: 2

   plom_server/modules.rst
