# -*- coding: utf-8 -*-

"""Misc routing utilities"""

__author__ = "Colin B. Macdonald"
__copyright__ = "Copyright (C) 2020"
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import functools
from aiohttp import web


def validFields(d, fields):
    """Check that input dict has (and only has) expected fields."""
    return set(d.keys()) == set(fields)


def logRequest(name, request):
    print("INFO: {}: {} {}".format(name, request.method, request.rel_url))


# TODO: try to work the @routes decorator in too
def authByToken(f):
    """Decorator for authentication by token, logging and field validation.

    This deals with authenication and logging so your function doesn't
    have too.  This is essentially a way to avoid copy-pasting lots of
    boilerplate code.

    The function under decoration should be a class method with no
    further arugments.

    The request input must contain the fields "user" and "token".  It
    must not contain any other fields: if this is not so, see the
    `@authByToken_validFields` decorator.
    """

    @functools.wraps(f)
    async def wrapped(zelf, request):
        logRequest(f.__name__, request)
        data = await request.json()
        if not validFields(data, ["user", "token"]):
            return web.Response(status=400)
        if not zelf.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        print('DEBUG: authenticated "{}" via token'.format(data["user"]))
        return f(zelf)

    return wrapped


def authByToken_validFields(fields):
    """Decorator for field validation, authentication by token, and logging.

    Return `web.Response(status=400)` if the input request does not
    contain exactly the fields `Union(fields, ["user", "token"])`.

    Example
    -------
    ```
    @authByToken_validFields(["bar", "baz"])
    def foo(self, data, request):
        return ...
    ```
    Here `data` is the result of `request.json()` and `request` is the
    original request (don't try to take data from it again!)
    """
    fields.extend(["user", "token"])

    def _decorate(f):
        @functools.wraps(f)
        async def wrapped(zelf, request):
            logRequest(f.__name__, request)
            data = await request.json()
            print("DEBUG: validating fields {}".format(fields))
            if not validFields(data, fields):
                return web.Response(status=400)
            if not zelf.server.validate(data["user"], data["token"]):
                return web.Response(status=401)
            print('DEBUG: authenticated "{}" via token'.format(data["user"]))
            return f(zelf, data, request)

        return wrapped

    return _decorate


def noAuthOnlyLog(f):
    """Decorator for logging requests."""
    @functools.wraps(f)
    def wrapped(self, request):
        logRequest(f.__name__, request)
        return f(self, request)
    return wrapped
