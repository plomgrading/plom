# Running the demo

Roughly `python -m demo`, but for details see
https://gitlab.com/plom/plom/-/issues/2604


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
