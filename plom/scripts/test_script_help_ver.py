# Copyright (C) 2020, 2025 Colin B. Macdonald
# SPDX-License-Identifier: AGPL-3.0-or-later

import importlib.metadata
import subprocess


from plom.common import __version__


def find_my_console_scripts(package_name):
    # Note I think this gets what is installed rather than the dev-tree
    entrypoints = (
        ep.name
        for ep in importlib.metadata.entry_points(group="console_scripts")
        if ep.name.startswith(package_name) and not ep.name.startswith("plom-client")
    )
    return entrypoints


scripts = list(find_my_console_scripts("plom"))


def test_scripts_have_hyphen_version():
    for s in scripts:
        assert __version__ in subprocess.check_output([s, "--version"]).decode()


def test_scripts_have_hyphen_help():
    for s in scripts:
        subprocess.check_call([s, "--help"])
        subprocess.check_call([s, "-h"])


def test_scripts_nonsense_cmdline():
    for s in scripts:
        assert subprocess.call([s, "--TheCatHasAlreadyBeenFed"]) != 0
