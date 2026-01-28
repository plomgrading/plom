# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023-2026 Colin B. Macdonald
# Copyright (C) 2023 Edith Coates

from pathlib import Path
import sqlite3

from django.conf import settings

from plom_server import __version__, Plom_DB_Version


def get_database_engine() -> str:
    """Which database engine are we using?"""
    engine = settings.DATABASES["default"]["ENGINE"]
    if "postgres" in engine:
        return "postgres"
    elif "sqlite" in engine:
        return "sqlite"
    else:
        return "unknown"
    # TODO = get this working with mysql too


def is_there_a_database() -> bool:
    """Return True if there is already a Plom database."""
    engine = settings.DATABASES["default"]["ENGINE"]
    if "postgres" in engine:
        return _is_there_a_postgres_database()
    elif "sqlite" in engine:
        return _is_there_a_sqlite_database()
    else:
        raise NotImplementedError(f'Database engine "{engine}" not implemented')


def _is_there_a_postgres_database(*, verbose: bool = True) -> bool:
    """Return True if there is already a Plom database in PostgreSQL."""
    import psycopg

    host = settings.DATABASES["postgres"]["HOST"]
    user = settings.DATABASES["postgres"]["USER"]
    password = settings.DATABASES["postgres"]["PASSWORD"]
    db_name = settings.DATABASES["default"]["NAME"]
    try:
        conn = psycopg.connect(user=user, password=password, host=host, dbname=db_name)
    except psycopg.OperationalError:
        if verbose:
            print(f'Cannot find database "{db_name}"')
        return False
    conn.close()
    return True


def _is_there_a_sqlite_database(*, verbose: bool = True) -> bool:
    db_name = settings.DATABASES["default"]["NAME"]
    r = Path(db_name).exists()
    if verbose and not r:
        print(f"Cannot find database {db_name}")
    return r


def get_database_metadata() -> dict[str, str]:
    # local import b/c other functions in this file don't need Django DB access
    from plom_server.Base.services import Settings

    d = {
        key: Settings.key_value_store_get_or_none(key)
        for key in (
            "database-created-by-plom-version",
            "database-last-used-by-plom-version",
            "database-version-integer",
        )
    }
    for k, v in d.items():
        d[k] = "" if v is None else v
    d.update(
        {
            "database-engine": get_database_engine(),
            "database-name": settings.DATABASES["default"]["NAME"],
        }
    )
    return d


def get_database_version() -> int:
    """An integer for the version of the database, or -1 if no such thing."""
    # local import b/c other functions in this file don't need Django DB access
    from plom_server.Base.services import Settings

    ver = Settings.key_value_store_get_or_none("database-version-integer")
    if ver is None:
        return -1
    return int(ver)


def created_record_plom_version() -> None:
    # local import b/c other functions in this file don't need Django DB access
    from plom_server.Base.services import Settings

    Settings.key_value_store_set("database-created-by-plom-version", __version__)
    Settings.key_value_store_set("database-last-used-by-plom-version", __version__)
    Settings.key_value_store_set("database-version-integer", str(Plom_DB_Version))


def update_last_used_plom_version() -> None:
    # local import b/c other functions in this file don't need Django DB access
    from plom_server.Base.services import Settings

    Settings.key_value_store_set("database-last-used-by-plom-version", __version__)


def drop_database(*, verbose: bool = True) -> None:
    """Delete the existing database: DESTRUCTIVE!"""
    engine = settings.DATABASES["default"]["ENGINE"]
    if "postgres" in engine:
        return _drop_postgres_database()
    elif "sqlite" in engine:
        return sqlite_delete_database()
    else:
        raise NotImplementedError(f'Database engine "{engine}" not implemented')


def _drop_postgres_database(*, verbose: bool = True) -> None:
    """Delete the existing database."""
    import psycopg

    # use local "socket" thing
    # conn = psycopg.connect(user="postgres", password="postgres")
    # use TCP/IP
    host = settings.DATABASES["postgres"]["HOST"]
    user = settings.DATABASES["postgres"]["USER"]
    password = settings.DATABASES["postgres"]["PASSWORD"]
    db_name = settings.DATABASES["default"]["NAME"]
    conn = psycopg.connect(user=user, password=password, host=host)
    conn.autocommit = True

    if verbose:
        print(f'Removing old database "{db_name}"')
    try:
        with conn.cursor() as curs:
            curs.execute(f"DROP DATABASE {db_name};")
    except psycopg.errors.InvalidCatalogName:
        if verbose:
            print(f'There was no database "{db_name}"')
    conn.close()


def create_database() -> None:
    """Create a new database.

    Raises:
        ValueError: there is already a database.
    """
    engine = settings.DATABASES["default"]["ENGINE"]
    if "postgres" in engine:
        return _create_postgres_database()
    elif "sqlite" in engine:
        return _create_sqlite_database()
    else:
        raise NotImplementedError(f'Database engine "{engine}" not implemented')


def _create_postgres_database(*, verbose: bool = True) -> None:
    import psycopg

    host = settings.DATABASES["postgres"]["HOST"]
    user = settings.DATABASES["postgres"]["USER"]
    password = settings.DATABASES["postgres"]["PASSWORD"]
    db_name = settings.DATABASES["default"]["NAME"]
    conn = psycopg.connect(user=user, password=password, host=host)
    conn.autocommit = True

    if verbose:
        print(f'Creating database "{db_name}"')
    try:
        with conn.cursor() as curs:
            curs.execute(f"CREATE DATABASE {db_name};")
    except psycopg.errors.DuplicateDatabase as e:
        raise ValueError(f'Failed to create database "{db_name}": {e}') from e
    finally:
        conn.close()


def _create_sqlite_database(*, verbose: bool = True) -> None:
    db_name = settings.DATABASES["default"]["NAME"]

    if _is_there_a_sqlite_database(verbose=False):
        raise ValueError(f"Database already exists: {db_name}")

    if verbose:
        print(f'Creating database "{db_name}"')
    _sqlite_set_wal()
    conn = sqlite3.connect(db_name)
    conn.close()


def _sqlite_set_wal() -> None:
    db_name = settings.DATABASES["default"]["NAME"]
    print(f"Setting journal mode WAL for sqlite database: {db_name}")
    conn = sqlite3.connect(db_name)
    conn.execute("pragma journal_mode=wal")
    conn.close()


def sqlite_delete_database() -> None:
    db_name = settings.DATABASES["default"]["NAME"]
    print(f"Deleting sqlite database: {db_name}")
    Path(db_name).unlink(missing_ok=True)
