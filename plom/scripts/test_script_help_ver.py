# Copyright (C) 2020 Colin B. Macdonald
# SPDX-License-Identifier: AGPL-3.0-or-later

import subprocess
import pkg_resources
from plom import __version__


def find_my_console_scripts(package_name):
    # Get list of console scripts
    # https://stackoverflow.com/questions/35275787/create-a-list-of-console-scripts-defined-in-a-python-package
    entrypoints = (
        ep.name
        for ep in pkg_resources.iter_entry_points("console_scripts")
        if ep.module_name.startswith(package_name)
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
