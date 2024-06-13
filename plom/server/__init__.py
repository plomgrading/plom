# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2024 Colin B. Macdonald

"""This is the legacy Plom Server."""

__copyright__ = "Copyright (C) 2018-2023 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

from pathlib import Path
import logging

from plom import specdir

specdir = Path(specdir)
confdir: Path = Path("serverConfiguration")

from .misc import build_server_directories
from .misc import create_server_config
from .misc import check_server_directories, check_server_fully_configured
from .cert_utils import build_self_signed_SSL_keys
from plom.manage_user_files import build_canned_users

# from plom.server.theServer import Server, launch
from plom.server.theServer import launch

from .background import PlomServer
from .demo import PlomDemoServer, PlomLiteDemoServer

# TODO: code is still changing, not clear yet what we want to expose here
# __all__ = ["launch", "PlomServer", "PlomDemoServer", "PlomLiteDemoServer"]
__all__ = ["launch"]
