__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai"]
__license__ = "AGPLv3"

import uuid
from passlib.context import CryptContext


class Authority:
    """A class to do all our authentication
    - user list, passwords and tokens.
    """

    def __init__(self):
        """Set up cryptocontext, userlist and tokenlist"""
        self.ctx = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")

    def checkPassword(self, user, password, passwordHash):
        """Check the password against the hashed one."""
        return self.ctx.verify(password, passwordHash)

    def createToken(self):
        """Create a token for a validated user"""
        return uuid.uuid4().hex
