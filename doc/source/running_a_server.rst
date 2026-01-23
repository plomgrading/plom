.. Plom documentation
   Copyright (C) 2022-2024 Colin B. Macdonald
   Copyright (C) 2023 Philip D. Loewen
   Copyright (C) 2026 Aidan Murphy
   SPDX-License-Identifier: AGPL-3.0-or-later

Running your own server
=======================

Plom has several components.  One of these is the Plom server,
used both for preparing new assessments and for coordinating grading.

This page details running a publicly exposed server for production use
with **live data**. If you are interested in running a server for
non-production use, please see
:doc:`Installing the Plom Server <install-server>`.

Though the source code for Plom is open and can be used freely by
.. note::
    We're not experts on hosting services.  The following are some
    suggestions and things Plom server admins should keep in mind,
    based on our experience.  Your mileage may vary!

Containerisation
----------------
Each Plom container requires its own database.  Currently these are 
limited to PostgreSQL.  One can either run one PostgreSQL server container
per Plom container, or share a PostgreSQL server between multiple Plom
containers.
Each Plom server release is documented on
`gitlab <https://gitlab.com/plom/plom/-/releases>`_, and container images
are available and currently hosted on DockerHub.

Security
--------
While the Plom container contains some security measures, it
would be unsafe (and irresponsible) to expose the minimally viable
plom+postgres containers on a public network without a reverse-proxy.
`Nginx <https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/>`_,
and `Apache <https://httpd.apache.org/docs/2.4/howto/reverse_proxy.html>`_
are both good options for a reverse proxy.

Backups
-------
Make them. An idealised Plom container is stateless, but the current
iteration unfortunately carries some state: you
should backup the container volumes for both the Plom container and the
backend database.

OrcaSequestration
-----------------
The Plom project provides some scripts for deploying and managing production
servers, contained in the
`OrcaSequestration <https://gitlab.com/plom/orcasequestration>`_.
repository.

These orca scripts are designed to be easy to use and broadly applicable,
These orca scripts are designed to be easy to use and broadly applicable
at the cost of some efficiency (e.g., it's not necessary for each
plom container to have a separate nginx reverse-proxy, but this simplifies
deployment for the admin).  This approach is subject to change and patches are welcome.
