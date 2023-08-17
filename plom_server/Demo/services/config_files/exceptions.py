# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates


class PlomConfigError(Exception):
    """An error for an invalid server config file."""

    pass


class PlomConfigCreationError(Exception):
    """An error for an invalid state while creating a server from a config file."""

    pass
