.. Plom documentation
   Copyright 2022 Colin B. Macdonald
   SPDX-License-Identifier: AGPL-3.0-or-later

Database: ``plom.db`` module
============================

The Plom database uses the `Peewee ORM
<https://pypi.org/project/peewee>`_ as a front-end to its database.
The database itself is an `SQLite <https://www.sqlite.org>`_ database,
stored on disc in a file.

The database frontend ``plom.db.PlomDB`` has many methods.  These are
generally connected to API calls in the :doc:`module-plom-server` module.
TODO: link to the API list...
There is a rough convention:

* methods that start with ``ID`` or ``ID_`` are related to
  :doc:`identifying_papers`.
* methods that start with ``M`` are related to marking.
* methods that start with ``R`` are for reporting.
* Everything else that does not fit these (loose) conventions.


Module docs
-----------

.. automodule:: plom.db
   :members:
