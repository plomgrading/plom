.. Plom documentation
   Copyright (C) 2021-2023, 2025 Colin B. Macdonald
   Copyright (C) 2024 Aidan Murphy
   SPDX-License-Identifier: AGPL-3.0-or-later

Python modules
==============

Most Plom code can be found in one of two directories in the
`project repository <https://gitlab.com/plom/plom>`_:

  * ``plom/``
  * ``plom_server/``

The former is currently (2025 March) "in-flux" as the marking client has
moved to a separate `Plom-Client repo <https://gitlab.com/plom/plom-client>`_
and the legacy server has been deprecated and subsequently removed.

The ``plom_server`` module contains the "current" (non-legacy) Plom server.



plom
----

.. toctree::
   :maxdepth: 1

   module-plom-create

   module-plom-scan

   module-plom-solutions

   module-plom-finish

   module-plom-other


plom_server
-----------

.. toctree::
   :maxdepth: 2

   plom_server/modules.rst
