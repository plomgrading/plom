# -*- coding: utf-8 -*-

"""Misc routing utilities"""

__author__ = "Colin B. Macdonald"
__copyright__ = "Copyright (C) 2020"
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import functools
from aiohttp import web

log = logging.getLogger("routes")


def validate_required_fields(user_login_info, user_login_required_fields):
    """Check that input dict has (and only has) expected fields.

    Arguments:
        user_login_info {dict} -- A user's login info.
        user_login_required_fields {list} -- Required login fields.

    Returns:
        bool -- True/False.
    """

    return set(user_login_info.keys()) == set(user_login_required_fields)


def log_request(request_name, request):
    """Logs the requests done by the server.

    Arguments:
        request_name {Str} -- Name of the request function.
        request {aiohttp.web_request.Request} -- The aiohttp request object.
    """
    log.info("{} {} {}".format(request_name, request.method, request.rel_url))


# TODO: try to work the @routes decorator in too
def authenticate_by_token(function):
    """Decorator for authentication by token, logging and field validation.

    This deals with authenication and logging so your function doesn't
    have too.  This is essentially a way to avoid copy-pasting lots of
    boilerplate code.

    The function under decoration should be a class method with no
    further arugments.

    The request input must contain the fields "user" and "token".  It
    must not contain any other fields: if this is not so, see the
    `@authenticate_by_token_required_fields` decorator.

    Arguments:
        function {function} -- A function primarily from ManagerMessenger, IDHandler, TotalHandler, etc 
                               that required authentication in order to operate.

    Returns:
        class 'function' -- TODO: Not sure but I believe this is a the input function wrapped
                            into an authentication function.
    """

    @functools.wraps(function)
    async def wrapped(zelf, request):
        """Wrapper function used for authentication.

        Arguments:
            request {aiohttp.web_request.Request} -- The aiohttp request object.
                                                     The data in request must have the user and token
                                                     fields.

        Returns:
            class 'function' -- TODO: Not sure but I believe this is a the input function wrapped
                                into an authentication function.
        """
        log_request(function.__name__, request)
        data = await request.json()
        if not validate_required_fields(data, ["user", "token"]):
            return web.Response(status=400)
        if not zelf.server.validate(data["user"], data["token"]):
            return web.Response(status=401)
        log.debug('{} authenticated "{}" via token'.format(function.__name__, data["user"]))
        return function(zelf)

    return wrapped


def authenticate_by_token_required_fields(fields):
    """Decorator for field validation, authentication by token, and logging.

    Return `web.Response(status=400)` if the input request does not
    contain exactly the fields `Union(fields, ["user", "token"])`.

    Example
    -------
    ```
    @authenticate_by_token_required_fields(["bar", "baz"])
    def foo(zelf, data, request):
        return ...
    ```
    Here `data` is the result of `request.json()` and `request` is the
    original request (don't try to take data from it again!)

    Arguments:
        fields {list} -- A list of the fields for this request.
                         Remember we must also add `user`, `token`.

    Returns:
        class 'function' -- TODO: Not sure but I believe this is a the input function wrapped
                            into an authentication function.
    """

    fields.extend(["user", "token"])

    def _decorate(function):
        @functools.wraps(function)
        async def wrapped(zelf, request):
            """Wrapper function used for authentication.

            Arguments:
                request {aiohttp.web_request.Request} -- The aiohttp request object.
                                                         The data in request must have the user and token
                                                         fields.

            Returns:
                class 'function' -- TODO: Not sure but I believe this is a the input function wrapped
                                    into an authentication function.
            """
            log_request(function.__name__, request)
            data = await request.json()
            log.debug("{} validating fields {}".format(function.__name__, fields))
            if not validate_required_fields(data, fields):
                return web.Response(status=400)
            if not zelf.server.validate(data["user"], data["token"]):
                return web.Response(status=401)
            log.debug('{} authenticated "{}" via token'.format(function.__name__, data["user"]))
            return function(zelf, data, request)

        return wrapped

    return _decorate


def no_authentication_only_log_request(function):
    """Decorator for logging requests only.

    Arguments:
        function {function} -- A function primarily from UserInitHandler etc 
                               that required authentication in order to operate.

    Returns:
        class 'function' -- TODO: Not sure but I believe this is a the input function wrapped
                            into an authentication function.
    """

    @functools.wraps(function)
    def wrapped(zelf, request):
        """Wrapper function used for authentication.

        Arguments:
            request {aiohttp.web_request.Request} -- The aiohttp request object.
                                                         The data in request must have the user and token
                                                         fields.

        Returns:
            class 'function' -- TODO: Not sure but I believe this is a the input function wrapped
                                into an authentication function.
        """
        log_request(function.__name__, request)
        return function(zelf, request)
    return wrapped
