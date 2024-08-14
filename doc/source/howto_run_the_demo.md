<!--
__copyright__ = "Copyright (C) 2023-2024 Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2023-2024 Colin B. Macdonald"
__copyright__ = "Copyright (C) 2023 Edith Coates"
__copyright__ = "Copyright (C) 2023 Natalie Balashov"
__license__ = "AGPL-3.0-or-later"
 -->

# Running the demo

Currently we must run the demo from the `plom_server` directory, by running
```
python3 Launcher/launch_scripts/launch_plom_demo_server.py
```
This runs the entire demo through to reassembling papers.
You should probably run it with a `--wait-after` option:
  * 'users' - will wait after creating demo-users
  * 'spec' - wait after a demo-spec is uploaded
  * 'papers_built' - wait after paper pdfs are built
  * 'rubrics' - wait after bundles are uploaded and system+demo rubrics set up - useful for playing with the client
  * 'randomarker' - wait after papers are marked and ID'd by the rando-marker

To stop the demo type "quit" and press enter.


## Problems

If the demo crashes (or you force quit out of it) then you may have
lingering huey tasks floating about that you'll need to terminate
before running again.  On Unix systems, one way to do this is:
```
pkill -KILL -f manage.py
```
This will terminate **any** user process that includes "manage.py",
which is (basically) all running django related stuff.... not just
those associated with the demo. **Use with care.**


## Databases

The new Plom server needs a database, which must be setup before
launching the server or the demo.

Commands below have been tested with Podman on a Fedora 40 laptop.


### SQLite

Currently not functional.  TODO: document how to try it.


### PostgreSQL

Start a local container:

    docker pull postgres
    docker run --name postgres_cntnr -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres

By default, things seem to want to use a socket instead of TCP/IP to talk
to the database.  For testing, I can connect with `psql -h 127.0.0.1 -U postgres`
To make Django use TCP/IP, I put the "127.0.0.1" as the host in
`settings.py`.

To stop the container:

    docker stop postgre_cntnr
    docker rm postgre_cntnr


### MariaDB / MySQL

TODO: connect this to Plom.

Start a local container:

    docker pull mariadb
    docker run --name mariadb_cntnr -e MYSQL_ROOT_PASSWORD=mypass -p 3306:3306 -d mariadb

Check that we can connect to the server:

    mysql -h localhost -P 3306 --protocol=TCP -u root -p
