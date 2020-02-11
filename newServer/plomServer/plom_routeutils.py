# -*- coding: utf-8 -*-

"""Misc routing utilities"""

__author__ = "Colin B. Macdonald"
__copyright__ = "Copyright (C) 2020"
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import functools


def validFields(d, fields):
    """Check that input dict has (and only has) expected fields."""
    return set(d.keys()) == set(fields)


# TODO: try to work the @routes decorator in too
def tokenauth(origf=None, *, fields=[]):
    """Decorator for authentication by token, logging and field validation.

    Used as `@tokenauth`, this deals with authenication and logging so
    your function doesn't have too.  This is essentially a way to
    avoid copy-pasting lots of boilerplate code.

    Example
    -------
    ```
    @tokenauth
    def foo(self, data):
        return ...
    ```
    Here `data` is the result of `requestions.json()`.

    You can instead use `@tokenauth(fields=<list>)` to pass any fields
    that must be present in the request.

    Implemenation is complicated [because `fields` is optional][1].

    References
    ----------
    [1] https://stackoverflow.com/questions/3888158/making-decorators-with-optional-arguments
    """

    def _decorate(f):
        # @functools.wrap(f)
        async def wrapped(zelf, request):
            print("INFO: {}: {} {}".format(f.__name__, request.method, request.rel_url))
            data = await request.json()
            fields.extend(["user", "token"])
            print("DEBUG: validating fields {}".format(fields))
            if not validFields(data, fields):
                return web.Response(status=400)
            if not zelf.server.validate(data["user"], data["token"]):
                return web.Response(status=401)
            print('DEBUG: authenticated "{}" via token'.format(data["user"]))
            return f(zelf, data)

        return wrapped

    if origf:
        return _decorate(origf)
    return _decorate

