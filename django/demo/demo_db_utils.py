# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Edith Coates

from pathlib import Path


def remove_old_migration_files():
    print("Avoid perplexing errors by removing autogen migration droppings")

    for path in Path(".").glob("*/migrations/*.py"):
        if path.name == "__init__.py":
            continue
        else:
            print(f"Removing {path}")
            path.unlink(missing_ok=True)
