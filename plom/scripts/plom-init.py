#! /user/bin/env python

from plom import version

print(
    "Running Plom version {} and API version {}".format(
        version.__version__, version.Plom_API_Version
    )
)
