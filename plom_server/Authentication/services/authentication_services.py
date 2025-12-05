# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2024-2025 Aidan Murphy

import csv
import os
from pathlib import Path

from django.contrib.auth.models import User, Group
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction, IntegrityError
from django.http import HttpRequest
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from random_username.generate import generate_username


class AuthenticationServices:
    """A service class for managing authentication-related tasks."""

    # TODO: is "demo" really a thing?
    plom_user_groups_list = (
        "manager",
        "marker",
        "scanner",
        "demo",
        "lead_marker",
        "identifier",
    )
    # additionally, there is a "admin" group, not user-facing
    all_plom_user_groups_list = (
        "admin",
        "manager",
        "marker",
        "scanner",
        "demo",
        "lead_marker",
        "identifier",
    )

    @classmethod
    @transaction.atomic
    def make_multiple_numbered_users(
        cls, num_users: int, group_name: str, *, basename: str | None = None
    ) -> list[tuple[str, list[str]]]:
        """Generate a list of basic numbered usernames and creates those users.

        Args:
            num_users: The number of users to generate.
            group_name: The name of the group.

        Keyword Args:
            basename: The base part of the username, to which numbers
                will be appended.  If omitted, use the `group_name`
                with a capital letter.

        Returns:
            List of pairs, each being a generated username and its group(s).
        """
        if not basename:
            basename = group_name.capitalize()

        user_list: list[tuple[str, list[str]]] = []
        username_number = 0

        while len(user_list) < num_users:
            username_number += 1
            try:
                username, groups = cls.create_user_and_add_to_group(
                    basename + str(username_number),
                    group_name,
                )
                user_list.append((username, groups))
            except IntegrityError:
                pass

        return user_list

    @staticmethod
    def apply_group_name_implications(group_names_in: list[str]) -> list[str]:
        """Some groups imply others; add any implied groups to the list."""
        group_names = group_names_in.copy()
        if "manager" in group_names:
            if "scanner" not in group_names:
                group_names.append("scanner")
            if "identifier" not in group_names:
                group_names.append("identifier")
        if "lead_marker" in group_names:
            if "marker" not in group_names:
                group_names.append("marker")
            # TODO: in the future, maybe not all lead markers need be identifiers
            if "identifier" not in group_names:
                group_names.append("identifier")
        return group_names

    @classmethod
    @transaction.atomic
    def create_user_and_add_to_groups(
        cls,
        username: str,
        group_names: list[str],
        *,
        email: str | None = None,
        password: str | None = None,
    ) -> tuple[str, list[str]]:
        """Create a user and add them to a group.

        Note that by default that new user will not be active.

        Args:
            username: The username of the user.
            group_names: The names of groups to add this user to.
                These must already exist.

        Keyword Args:
            email: optional email address for the user.
            password: if omitted (default), the user will be inactive.

        Returns:
            The username of the created user, and a list of groups to which
            they were added.  Note this might be a superset of the requested
            groups b/c some groups imply others.

        Raises:
            ObjectDoesNotExist: no such group.
            ValueError: illegal user group received
            IntegrityError: user already exists; or perhaps a nearby one
                does, such as one that differs only in case.

        Note: If a password is supplied, the user will be set active.
        """
        if "admin" in group_names:
            raise ValueError('Cannot create a user belonging to the "admin" group')

        group_names = cls.apply_group_name_implications(group_names)

        # if username that matches in case exists, fail.  Note that doesn't seem
        # to get raises by the call to "create_user" although it DOES get flagged
        # by some form validator stuff.  However, we cannot assume that all our
        # usernames come through the validator: for example the bulk creator
        # See Issue #3643
        if User.objects.filter(username__iexact=username).exists():
            raise IntegrityError(
                f'username "{username}" already exists or differs only in case'
            )

        groups = Group.objects.filter(name__in=group_names)
        # We need one-to-one between the group_names (strs) and the Groups
        # list() so its not a QuerySet
        groups_name_list = list(groups.values_list("name", flat=True))
        for x in group_names:
            if x not in groups_name_list:
                raise ValueError(f'Cannot add user to non-existent Group "{x}"')

        user = User.objects.create_user(
            username=username, email=email, password=password
        )
        user.groups.add(*groups)
        if not password:
            user.is_active = False
        user.save()

        return user.username, groups_name_list

    @classmethod
    @transaction.atomic
    def create_user_and_add_to_group(
        cls, username: str, group_name: str, **kwargs
    ) -> tuple[str, list[str]]:
        """Create a user and add them to a group."""
        return cls.create_user_and_add_to_groups(username, [group_name], **kwargs)

    @classmethod
    def create_manager_user(
        cls, username: str, *, password: str | None = None, email: str | None = None
    ) -> None:
        """Create a manager user.

        Args:
            username: the account username for this manager.

        Keywords:
            password: if omitted, the user will be inactive.
            email: optionally, an email contact address.

        Note: If a password is supplied, the user will be set active.
        """
        group_names = cls.apply_group_name_implications(["manager"])
        with transaction.atomic(durable=True):
            groups = Group.objects.filter(name__in=group_names)
            # We need one-to-one between the group_names (strs) and the Groups
            # list() so its not a QuerySet
            groups_name_list = list(groups.values_list("name", flat=True))
            for x in group_names:
                if x not in groups_name_list:
                    raise ValueError(f'Cannot add user to non-existent Group "{x}"')

            user = User.objects.create_user(
                username=username, email=email, password=password
            )
            if not password:
                user.is_active = False
            user.groups.add(*groups)
            user.save()

    def create_users_from_csv(self, f: Path | str | bytes) -> list[dict[str, str]]:
        """Creates multiple users from a .csv file.

        This is an atomic operation: either all users are created or all fail.

        Args:
            f: a path to the .csv file, or the bytes of a .csv file.

        Returns:
            A list of dicts containing information for each user, each entry
            has keys `username`, `groups`, and `link`.

        Raises:
            KeyError: .csv file is missing required fields: `username`, `usergroup`.
            IntegrityError: attempted to create a user that already exists.
            ObjectDoesNotExist: specified usergroup doesn't exist.
        """
        if isinstance(f, bytes):
            user_list = list(csv.DictReader(f.decode("utf-8").splitlines()))
            _filename = "csv file"
        else:
            _filename = str(f)
            with open(f) as csvfile:
                user_list = list(csv.DictReader(csvfile))

        required_fields = set(["username", "usergroup"])
        if not required_fields.issubset(user_list[0].keys()):
            raise KeyError(
                f"{_filename} is missing required fields,"
                f" it must contain: {required_fields}"
            )

        users_added = []
        # either all succeed or all fail
        with transaction.atomic():
            for idx, user_dict in enumerate(user_list):
                group = user_dict["usergroup"]
                try:
                    u, g = self.create_user_and_add_to_group(
                        user_dict["username"], group
                    )
                except ValueError as e:
                    raise ObjectDoesNotExist(
                        f'Error near row {idx + 1}: Group "{group}" does not exist? {e}'
                    ) from e
                user = User.objects.get(username=user_dict["username"])
                users_added.append(
                    {
                        "username": u,
                        "groups": g,
                        "link": self.generate_link(user),
                    }
                )

        return users_added

    @classmethod
    def make_multiple_funky_named_users(
        cls, num_users: int, group_name: str
    ) -> list[tuple[str, list[str]]]:
        """Generate a list of "funky usernames", create them and add to a group.

        Args:
            num_users: The number of users to generate.
            group_name: The name of the group.

        Returns:
            List of generated usernames.
        """
        funky_username_list = generate_username(num_users)
        user_list = []
        for username in funky_username_list:
            u, g = cls._check_and_create_funky_usernames(
                username=username, group_name=group_name
            )
            user_list.append((u, g))

        return user_list

    @classmethod
    def _check_and_create_funky_usernames(
        cls, username: str, group_name: str
    ) -> tuple[str, list[str]]:
        """Check if a username exists, and if it does, generate a new one recursively.

        Args:
            username: The username to check.
            group_name: The name of the group.

        Returns:
            The username of the created user.
        """
        if User.objects.filter(username=username).exists():
            new_username = generate_username(1)
            return cls._check_and_create_funky_usernames(
                username=new_username, group_name=group_name
            )
        else:
            u, g = cls.create_user_and_add_to_group(username, group_name)
            return (u, g)

    @transaction.atomic
    def generate_password_reset_links_dict(
        self, request: HttpRequest, username_list: list[str]
    ) -> dict[str, str]:
        """Generate a dictionary of password reset links for a list of usernames.

        Args:
            request: The HTTP request object.
            username_list: List of usernames.

        Returns:
            Dictionary of username to password reset link.
        """
        links_dict = {}
        request_domain = get_current_site(request).domain
        for username in username_list:
            user = User.objects.get(username=username)
            links_dict[username] = self.generate_link(user, request_domain)
        return links_dict

    @transaction.atomic
    def generate_link(self, user: User, hostname: str = "") -> str:
        """Generate a password reset link for a user.

        Args:
            user: The user object for whom the password reset link is
                generated.
            hostname: If the server cannot find a domain while constructing
                the link, this variable will be used as the domain.

        Returns:
            The generated password reset link as a string.

        See :method:`get_base_link` for details about how to influence this link.
        """
        baselink = self.get_base_link(default_host=hostname)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        link = baselink + f"reset/{uid}/{token}"

        return link

    @staticmethod
    def get_base_link(*, default_host: str = "") -> str:
        """Generate the base part of the URL to link to this server.

        Keyword Args:
            default_host: if you have a guess at the host (e.g., from a
                request), you can pass it here.  It will be overridden
                by the ``PLOM_HOSTNAME`` environment variable, if that is
                defined, and defaults to "localhost" if omitted.

        Returns:
            A string of with a http or https URL.  It will always
            end with a trailing slash.

        .. note::

            The generated link follows the format:
            `<scheme>://<domain>:<port>/<prefix>/` or
            `<scheme>://<domain>:<port>/`.
            Because you may have proxies between your server and the client, the
            URL can be influenced with the environment variables:

               - PLOM_PUBLIC_FACING_SCHEME
               - PLOM_PUBLIC_FACING_PORT
               - PLOM_PUBLIC_FACING_PREFIX
               - PLOM_HOSTNAME
        """
        scheme = os.environ.get("PLOM_PUBLIC_FACING_SCHEME", "http")
        # TODO: do we need a public facing hostname var too?
        domain = os.environ.get("PLOM_HOSTNAME", default_host)
        if not domain:
            domain = "localhost"
        prefix = os.environ.get("PLOM_PUBLIC_FACING_PREFIX", "")
        if prefix and not prefix.endswith("/"):
            prefix += "/"
        port = os.environ.get("PLOM_PUBLIC_FACING_PORT", "")
        if port:
            port = ":" + port
        return f"{scheme}://{domain}{port}/{prefix}"
