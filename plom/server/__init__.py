# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2022 Colin B. Macdonald

"""The Plom Server"""

__copyright__ = "Copyright (C) 2018-2022 Andrew Rechnitzer, Colin B. Macdonald et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

from pathlib import Path
import logging

from plom import specdir

specdir = Path(specdir)
confdir = Path("serverConfiguration")

from .misc import build_server_directories
from .misc import create_server_config, create_blank_predictions
from .misc import check_server_directories, check_server_fully_configured
from .cert_utils import build_self_signed_SSL_keys
from .manageUserFiles import build_canned_users

from .background import PlomServer
from .demo import PlomDemoServer, PlomLiteDemoServer
