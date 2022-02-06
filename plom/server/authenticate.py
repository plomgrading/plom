# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2020-2022 Colin B. Macdonald

import logging
import uuid

from passlib.context import CryptContext


def basic_username_check(username):
    """Sanity check for potential usernames.

    Arguments:
        username (str)

    Returns:
        tuple: (True, "") if valid, (False, msg) otherwise, where msg
            is a string explaining why not.
    """
    if len(username) < 3:
        return False, "Username too short, should be at least 3 chars"
    if not (username.isalnum() and username[0].isalpha()):
        return False, "Username should be alphanumeric and start with a letter"
    return True, ""


def basic_username_password_check(username, password):
    """Sanity check for potential usernames and passwords.

    Arguments:
        username (str)
        password (str)

    Returns:
        tuple: (True, "") if valid, (False, msg) otherwise, where msg
            is a string explaining why not.

    This does only very basic checking of passwords: not too short
    and not identically equal the username.  You may want additional
    checks!
    """
    r = basic_username_check(username)
    if not r[0]:
        return r
    if len(password) < 4:
        return False, "Password too short, should be at least 4 chars"
    if password == username:
        return False, "Password is too close to the username"
    return True, ""


class SimpleAuthorityHasher:
    """A dumbed down version of Authority, only can hash passwords.

    Note some duplication of code here but at least its all in this one source file.
    """

    def __init__(self):
        self.ctx = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")

    def create_password_hash(self, password):
        """Creates a hash of a string password.

        Arguments:
            password (str)

        Returns:
            str: Hashed password.
        """
        return self.ctx.hash(password)


class Authority:
    """A class to do all our authentication - passwords and tokens."""

    def __init__(self, masterToken):
        """Set up cryptocontext, userlist and tokenlist"""
        self.ctx = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")
        # set master token, being careful of what user supplies
        # is hex string of uuid4
        self.masterToken = self.build_master_token(masterToken)
        # convert it to int - is base 16
        self.mti = int(self.masterToken, 16)
        # we need this for xor-ing.

    def build_master_token(self, token):
        """Creates a new masterToken or validates existing masterToken.

        Arguments:
            token (str): Current masterToken, if None, a new one is created.

        Returns:
            str: a valid masterToken.

        Raises:
            ValueError: invalid token.
        """
        log = logging.getLogger("auth")
        if token is None:
            masterToken = uuid.uuid4().hex
            log.info("No master token given, creating one")
        else:
            try:
                masterToken = uuid.UUID(token).hex
                log.info("Supplied master token is valid, using it.")
            except ValueError as e:
                raise ValueError(f"Supplied master token not valid UUID: {e}") from None
        return masterToken

    def get_master_token(self):
        """Getter for the masterToken"""
        return self.masterToken

    def check_password(self, password, expected_hash):
        """Check the password against expected hashed password.

        Arguments:
            password (str): password to check.
            expected_hash (str): hashed password on file or None
                if we have no such user on file.

        Returns:
            bool: True on match, False otherwise.
        """
        if not isinstance(password, str):
            password = ""
        return self.ctx.verify(password, expected_hash)

    def create_token(self):
        """Create a token for a validated user, return that token as hex and int-xor'd version for storage.

        Returns:
            list -- Client and storage tokens in the form [clientToken, storageToken].
        """
        clientToken = uuid.uuid4().hex
        storageToken = hex(int(clientToken, 16) ^ self.mti)
        return [clientToken, storageToken]

    def validate_token(self, clientToken, stored_token):
        """Validates a given token against the storageToken.

        Arguments:
            clientToken (str): The token, a hex string provided by the
                client.  This may be untrusted unsanitized input.
            stored_token (str/None): The token we are checking against.
                Can be None, e.g., when no token is stored.

        Returns:
            bool/None: True if validated, False/None otherwise.  False
                indicates an invalid (non-matching) token, including the
                case when the stored token is None.  A return of None
                indicates a malformed token.  This bool/None tristate
                means `if validate_token(...):` works.
        """
        if not isinstance(clientToken, str):
            return None
        # should not be significantly longer than UUID's 32 hex digits
        if len(clientToken) > 64:
            return None
        try:
            clientTokenInt = int(clientToken, 16)
        except ValueError:
            return None
        if hex(clientTokenInt ^ self.mti) == stored_token:
            return True
        return False

    def check_string_is_UUID(self, tau):
        """Checks that a given string is a valid UUID.

        Arguments:
            tau (str): string to check

        Returns:
            bool: True if input is a valid universally unique identifier.
        """
        try:
            _ = uuid.UUID(tau)
        except ValueError:
            return False
        return True

    def basic_username_check(self, username):
        return basic_username_check(username)

    def basic_username_password_check(self, username, password):
        return basic_username_password_check(username, password)

    def create_password_hash(self, password):
        """Creates a hash of a string password.

        Arguments:
            password (str)

        Returns:
            str: Hashed password.
        """
        return self.ctx.hash(password)
