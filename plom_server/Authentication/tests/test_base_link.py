# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Aidan Murphy

from django.test import TestCase

from ..services import AuthService


class AuthService__assemble_base_link(TestCase):
    """Test AuthService._assemble_base_link()."""

    def test_scheme_domain(self) -> None:
        """Check scheme and domain inputs."""
        link = AuthService._assemble_base_link(scheme="http", domain="www.example.com")
        self.assertEqual(link, "http://www.example.com/")

    def test_scheme_domain_port(self) -> None:
        """Check port inputs."""
        link = AuthService._assemble_base_link(
            scheme="http", domain="www.example.com", port="8000"
        )
        self.assertEqual(link, "http://www.example.com:8000/")

    def test_scheme_domain_prefix(self) -> None:
        """Check prefix inputs."""
        link = AuthService._assemble_base_link(
            scheme="http", domain="www.example.com", prefix="bluepanda"
        )
        self.assertEqual(link, "http://www.example.com/bluepanda/")

    def test_scheme_domain_prefix_trailing_slash(self) -> None:
        """Check prefix inputs with trailing slash."""
        link = AuthService._assemble_base_link(
            scheme="http", domain="www.example.com", prefix="bluepanda/"
        )
        self.assertEqual(link, "http://www.example.com/bluepanda/")

    def test_scheme_domain_prefix_leading_slash(self) -> None:
        """Check prefix inputs with leading slash."""
        link = AuthService._assemble_base_link(
            scheme="http", domain="www.example.com", prefix="/bluepanda"
        )
        self.assertEqual(link, "http://www.example.com/bluepanda/")

    def test_scheme_domain_port_prefix(self) -> None:
        """Check port and prefix inputs simultaneously."""
        link = AuthService._assemble_base_link(
            scheme="http", domain="www.example.com", port="8000", prefix="bluepanda"
        )
        self.assertEqual(link, "http://www.example.com:8000/bluepanda/")

    def test_trailing_slash(self) -> None:
        """Check that return string always has a trailing slash."""
        link = AuthService._assemble_base_link(scheme="http", domain="www.example.com")
        self.assertEqual(link[-1], "/")
        link = AuthService._assemble_base_link(
            scheme="http", domain="www.example.com", prefix="bluepanda"
        )
        self.assertEqual(link[-1], "/")
        link = AuthService._assemble_base_link(
            scheme="http",
            domain="www.example.com",
            port="8000",
        )
        self.assertEqual(link[-1], "/")
        link = AuthService._assemble_base_link(
            scheme="http", domain="www.example.com", port="8000", prefix="bluepanda"
        )
        self.assertEqual(link[-1], "/")
