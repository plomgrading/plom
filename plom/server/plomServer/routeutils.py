# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2022 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian

"""Misc routing utilities"""

import logging
import functools
from aiohttp import web

log = logging.getLogger("routes")


def validate_required_fields(user_login_info, user_login_required_fields):
    """Check that input dict has (and only has) expected fields.

    Arguments:
        user_login_info (dict): A user's login info.
        user_login_required_fields (iterable): the required fields.

    Returns:
        bool: True iff the fields are present.
    """

    return set(user_login_info.keys()) == set(user_login_required_fields)


def log_request(request_name, request):
    """Logs the requests done by the server.

    Arguments:
        request_name (str): Name of the request function.
        request (aiohttp.web_request.Request): an `aiohttp` request object.
    """
    log.info("{} {} {}".format(request_name, request.method, request.rel_url))


# TODO: try to work the @routes decorator in too
# TODO: does not work if the function to be decorated needs access to `requests`
def authenticate_by_token(f):
    """Decorator for authentication by token, logging and field validation.

    This deals with authentication and logging so your function doesn't
    have too.  This is essentially a way to avoid copy-pasting lots of
    boilerplate code.

    The function under decoration should be a class method with no
    further arguments.

    The request input must contain the fields "user" and "token".  It
    must not contain any other fields: if this is not so, see the
    `@authenticate_by_token_required_fields` decorator instead.

    Arguments:
        f (function): a routing method associated with the Plom server.

    Returns:
        function: the input wrapped with token-based authentication.
    """

    @functools.wraps(f)
    async def wrapped(zelf, request):
        log_request(f.__name__, request)
        data = await request.json()
        fields = ["user", "token"]
        if not validate_required_fields(data, fields):
            log.warning(
                "%s: fields %s do not match expected %s",
                f.__name__,
                list(data.keys()),
                fields,
            )
            raise web.HTTPBadRequest(
                reason=f"fields {list(data.keys())} do not match expected {fields}"
            )
        if not zelf.server.validate(data["user"], data["token"]):
            log.warning(
                '%s user "%s": login token could not be validated',
                f.__name__,
                data["user"],
            )
            return web.HTTPUnauthorized(reason="login token could not be validated")
        log.info('%s authenticated "%s" via token', f.__name__, data["user"])
        return f(zelf)

    return wrapped


def authenticate_by_token_required_fields(fields):
    """Decorator for field validation, authentication by token, and logging.

    The decorated function returns `web.Response(status=400)` if the
    input request does not contain exactly the fields
    `Union(fields, ["user", "token"])`.

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
        f (function): the function to be decorated (TODO: not listed
            above for some reason).
        fields (iterable): The fields for this request.  `user` and
            `token` will be added to this list.

    Returns:
        function: the original function wrapped with authentication.
    """

    fields.extend(["user", "token"])

    def _decorate(f):
        @functools.wraps(f)
        async def wrapped(zelf, request):
            log_request(f.__name__, request)
            data = await request.json()
            log.debug("{} validating fields {}".format(f.__name__, fields))
            if not validate_required_fields(data, fields):
                log.warning(
                    "%s: fields %s do not match expected %s",
                    f.__name__,
                    list(data.keys()),
                    fields,
                )
                raise web.HTTPBadRequest(
                    reason=f"fields {list(data.keys())} do not match expected {fields}"
                )
            if not zelf.server.validate(data["user"], data["token"]):
                log.warning(
                    '%s user "%s": login token could not be validated',
                    f.__name__,
                    data["user"],
                )
                raise web.HTTPUnauthorized(reason="login token could not be validated")
            log.info('%s authenticated "%s" via token', f.__name__, data["user"])
            return f(zelf, data, request)

        return wrapped

    return _decorate


def no_authentication_only_log_request(f):
    """Decorator for logging requests only.

    Arguments:
        f (function): a routing method associated with the Plom server.

    Returns:
        function: the original wrapped with logging.
    """

    @functools.wraps(f)
    def wrapped(zelf, request):
        log_request(f.__name__, request)
        return f(zelf, request)

    return wrapped


def readonly_admin(f):
    """Decorator for requiring the manager account to get something read-only.

    In the future, more than one user might satisfy this via ACL, but for
    now if just checks for the "manager" account.

    Arguments:
        f (function): a routing method associated with the Plom server.

    Returns:
        function: the original wrapped with logging.
    """

    @functools.wraps(f)
    def wrapped(zelf, data, request):
        if data["user"] != "manager":
            log.warning(
                '%s user "%s": tried to connect to admin (read-only) feature',
                f.__name__,
                data["user"],
            )
            raise web.HTTPForbidden(reason="I wanna speak to the manager!")
        log.info('%s we have an admin-read-only user "%s"', f.__name__, data["user"])
        return f(zelf, data, request)

    return wrapped


def write_admin(f):
    """Decorator for requiring the manager account to push or other change something in the state of the server.

    In the future, more than one user might satisfy this via ACL, but for
    now if just checks for the "manager" account.

    Arguments:
        f (function): a routing method associated with the Plom server.

    Returns:
        function: the original wrapped with logging.
    """

    @functools.wraps(f)
    def wrapped(zelf, data, request):
        if data["user"] != "manager":
            log.warning(
                '%s user "%s": tried to connect to admin (write) feature',
                f.__name__,
                data["user"],
            )
            raise web.HTTPForbidden(reason="I wanna speak to the manager!")
        log.info('%s we have an admin-write user "%s"', f.__name__, data["user"])
        return f(zelf, data, request)

    return wrapped
