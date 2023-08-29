<!--
__copyright__ = "Copyright (C) 2023 Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2023 Colin B. Macdonald"
__copyright__ = "Copyright (C) 2023 Edith Coates"
__copyright__ = "Copyright (C) 2023 Natalie Balashov"
__license__ = "AGPL-3.0-or-later"
 -->

# Running the demo

Roughly `python3 manage.py plom_demo` from inside the `plom_server/` directory,
but for details see https://gitlab.com/plom/plom/-/issues/2604

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


## notes on DB installs

Colin did all these with Podman on a Fedora 37 laptop.

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

I also had to convince ``psycopg2`` by using the ``host`` kwarg: likely that is
changing Real Soon Now to respect the `settings.py`

To stop the container::

    docker stop postgre_cntnr
    docker rm postgre_cntnr.


### MariaDB / MySQL

Start a local container:

    docker pull mariadb
    docker run --name mariadb_cntnr -e MYSQL_ROOT_PASSWORD=mypass -p 3306:3306 -d mariadb

Check that we can connect to the server::

    mysql -h localhost -P 3306 --protocol=TCP -u root -p

TODO: connect this to Plom
