# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Andrew Rechnitzer
# Copyright (C) 2024-2026 Colin B. Macdonald
# Copyright (C) 2026 Aidan Murphy

from django.core.management.base import BaseCommand, CommandParser, CommandError
from django.db import transaction

from django.contrib.auth.models import User, Group

from plom.aliceBob import simple_password
from plom_server.Authentication.services import AuthService


class Command(BaseCommand):
    """Creates admin and manager users if none exist."""

    help = """
        Creates a starting manager and admin account if there aren't any existing
        manager or admin accounts.
        If there are existing manager or admin accounts, logs a message to stder and
        exits with code 0 (no error). In this way, the command is idempotent.
    """

    def add_arguments(self, parser: CommandParser) -> None:
        """Process commandline arguments."""
        a_group = parser.add_mutually_exclusive_group()
        a_group.add_argument(
            "--admin-login",
            nargs=2,
            metavar=("USERNAME", "PASSWORD"),
            help="Login details for the admin.",
        )
        a_group.add_argument(
            "--no-admin-password",
            action="store_true",
            help="""
                Don't generate a password, or reset link, for the admin user.
                Most users won't need the admin user account for their assessments,
                so for security reasons you might make this account inaccessible
                until a password is set via the plom_users Django manage command.
            """,
        )
        a_group.add_argument(
            "--force-admin-password",
            action="store_true",
            help="""
                Set simple passwords and write them to stdout, rather than
                password reset links.
            """,
        )

        m_group = parser.add_mutually_exclusive_group()
        m_group.add_argument(
            "--manager-login",
            nargs=2,
            metavar=("USERNAME", "PASSWORD"),
            help="Login details for the manager.",
        )
        m_group.add_argument(
            "--force-manager-password",
            action="store_true",
            help="""
                Set a simple password and write it to stdout, rather than
                a password reset link.
            """,
        )

        parser.add_argument(
            "--port",
            help="""
                If password links are to be generated, you can specify the
                port number to appear in the links.  Generally the internal
                code will check environment variables or other configuration
                which will override this option.  Still, maybe its useful in
                some cases, such as the demo.
            """,
        )

    def create_admin(self, username: str, password: str | None = None) -> User:
        """Create an admin user."""
        if User.objects.filter(is_superuser=True).count() > 0:
            raise CommandError(
                "Cannot create admin user, they already exist.", returncode=0
            )

        if not Group.objects.filter(name="admin").exists():
            raise CommandError(
                "Cannot create admin-user since the admin group has not been created."
            )

        admin = User.objects.create_superuser(username=username, password=password)
        admin_group = Group.objects.get(name="admin")
        admin.groups.add(admin_group)
        admin.save()
        return admin

    def create_first_manager(
        self, username: str, *, password: str | None = None
    ) -> User:
        """Create a manager user."""
        if User.objects.filter(groups__name="manager").exists():
            raise CommandError(
                "Cannot create manager user, they already exist.", returncode=0
            )
        try:
            return AuthService.create_manager_user(username, password=password)
        except ValueError as e:
            raise CommandError(e) from None

    def _create_user(
        self,
        *,
        kind: str,
        default_username: str,
        force_password: bool,
        login_credentials: tuple[str, str] | None,
        no_password: bool = False,
        port: str = "",
    ) -> str:
        """Create a manager or admin user and return a string with login details."""
        out = f"Make {kind} user\n"
        if kind == "manager":
            _make_user = self.create_first_manager
        elif kind == "admin":
            _make_user = self.create_admin
        else:
            raise CommandError(f'kind "{kind}" is not valid')

        if no_password:
            username = default_username
            _make_user(username)
            out += "v" * 40 + "\n"
            out += f"{kind} username: {username}\n"
            out += f"{kind} password: [NONE]\n"
            out += "^" * 40 + "\n"
        elif login_credentials is None:
            out += f"No {kind} login details provided: autogenerating...\n"
            username = default_username
            if force_password:
                password = simple_password(6)
                _make_user(username, password=password)
            else:
                user_obj = _make_user(username)
                password = AuthService.generate_link(user_obj, port=port)
            out += "v" * 40 + "\n"
            out += f"{kind} username: {username}\n"
            out += f"{kind} password: {password}\n"
            out += "^" * 40 + "\n"
        else:
            username, password = login_credentials
            _make_user(username, password=password)
            out += "v" * 40 + "\n"
            out += f"{kind} username: {username}\n"
            out += f"{kind} password: [as provided on command line]\n"
            out += "^" * 40 + "\n"
        return out

    @transaction.atomic(durable=True)
    def handle(self, *args, **options):
        """Make users for the plom-server."""
        port = options["port"] or ""

        manager_str = self._create_user(
            kind="manager",
            default_username="manager",
            force_password=options["force_manager_password"],
            login_credentials=options["manager_login"],
            port=port,
        )
        admin_str = self._create_user(
            kind="admin",
            default_username="admin",
            force_password=options["force_admin_password"],
            login_credentials=options["admin_login"],
            no_password=options["no_admin_password"],
            port=port,
        )
        self.stdout.write(manager_str)
        self.stdout.write(admin_str)
