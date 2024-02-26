# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2023 Edith Coates

from django.conf import settings


def get_database_engine():
    """Which database engine are we using?"""
    engine = settings.DATABASES["default"]["ENGINE"]
    if "postgres" in engine:
        return "postgres"
    elif "sqlite" in engine:
        return "sqlite"
    else:
        return "unknown"
    # TODO = get this working with mysql too


def is_there_a_database():
    """Return True if there is already a Plom database."""
    engine = settings.DATABASES["default"]["ENGINE"]
    if "postgres" in engine:
        return _is_there_a_postgres_database()
    elif "sqlite" in engine:
        # TODO = get this working with mysql too
        raise NotImplementedError("TODO: sqlite not yet implemented")
    else:
        raise NotImplementedError(f'Database engine "{engine}" not implemented')


def _is_there_a_postgres_database(*, verbose: bool = True) -> bool:
    """Return True if there is already a Plom database in PostgreSQL."""
    import psycopg2

    host = settings.DATABASES["postgres"]["HOST"]
    user = settings.DATABASES["postgres"]["USER"]
    password = settings.DATABASES["postgres"]["PASSWORD"]
    db_name = settings.DATABASES["default"]["NAME"]
    try:
        conn = psycopg2.connect(user=user, password=password, host=host, dbname=db_name)
    except psycopg2.OperationalError:
        if verbose:
            print(f'Cannot find database "{db_name}"')
        return False
    conn.close()
    return True


def drop_database(*, verbose: bool = True) -> None:
    """Delete the existing database: DESTRUCTIVE!"""
    engine = settings.DATABASES["default"]["ENGINE"]
    if "postgres" in engine:
        return _drop_postgres_database()
    else:
        raise NotImplementedError(f'Database engine "{engine}" not implemented')


def _drop_postgres_database(*, verbose: bool = True) -> None:
    """Delete the existing database."""
    import psycopg2

    # use local "socket" thing
    # conn = psycopg2.connect(user="postgres", password="postgres")
    # use TCP/IP
    host = settings.DATABASES["postgres"]["HOST"]
    user = settings.DATABASES["postgres"]["USER"]
    password = settings.DATABASES["postgres"]["PASSWORD"]
    db_name = settings.DATABASES["default"]["NAME"]
    conn = psycopg2.connect(user=user, password=password, host=host)
    conn.autocommit = True

    if verbose:
        print(f'Removing old database "{db_name}"')
    try:
        with conn.cursor() as curs:
            curs.execute(f"DROP DATABASE {db_name};")
    except psycopg2.errors.InvalidCatalogName:
        if verbose:
            print(f'There was no database "{db_name}"')
    conn.close()


def recreate_postgres_database():
    """Delete the existing database, and create a new one: DESTRUCTIVE!"""
    import psycopg2

    _drop_postgres_database(verbose=True)

    host = settings.DATABASES["postgres"]["HOST"]
    user = settings.DATABASES["postgres"]["USER"]
    password = settings.DATABASES["postgres"]["PASSWORD"]
    db_name = settings.DATABASES["default"]["NAME"]
    conn = psycopg2.connect(user=user, password=password, host=host)
    conn.autocommit = True

    print(f'Creating database "{db_name}"')
    try:
        with conn.cursor() as curs:
            curs.execute(f"CREATE DATABASE {db_name};")
    except psycopg2.errors.DuplicateDatabase:
        raise RuntimeError(
            f'Failed to create database "{db_name}"; perhaps we are racing?'
        )
    conn.close()


def sqlite_set_wal():
    import sqlite3

    print("Setting journal mode WAL for sqlite database")
    conn = sqlite3.connect("db.sqlite3")
    conn.execute("pragma journal_mode=wal")
    conn.close()
