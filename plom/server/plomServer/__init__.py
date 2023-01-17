# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020, 2022-2023 Colin B. Macdonald

"""Routes and server details for the Plom server.

Many of these routes have a corresponding server method to do non-HTTP
stuff, but this separation is not perfect.  In many cases the server
bit just makes the same call to the database code in :doc:`module-plom-db`.
"""

__copyright__ = "Copyright (C) 2018-2023 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

from .routesID import IDHandler
from .routesMark import MarkHandler
from .routesRubric import RubricHandler
from .routesReport import ReportHandler
from .routesSolution import SolutionHandler
from .routesUpload import UploadHandler
from .routesUserInit import UserInitHandler

__all__ = [
    "IDHandler",
    "MarkHandler",
    "ReportHandler",
    "RubricHandler",
    "SolutionHandler",
    "UploadHandler",
    "UserInitHandler",
]
