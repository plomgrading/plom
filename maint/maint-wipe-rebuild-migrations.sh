#!/bin/bash

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2025 Colin B. Macdonald

# Run this script from the project root (where pyproject.toml is)
#   ./maint/maint-wipe-rebuild-migrations.sh
#
# As of 2025-03 we do not use "layered" migrations: we change the
# database design only between major versions, and we rebuild from
# scratch.  You can run this script after database edits, or perhaps
# after Django-upgrades to regenerate the migration files that are
# used to initialize the database.

python3 plom_server/scripts/wipe_migrations.py

PYTHONPATH=. python3 manage.py makemigrations --no-header
