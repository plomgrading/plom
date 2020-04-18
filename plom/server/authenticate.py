__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai"]
__license__ = "AGPLv3"

import uuid
from passlib.context import CryptContext


class Authority:
    """
    A class to do all our authentication - passwords and tokens.
    """

    def __init__(self, masterToken):
        """Set up cryptocontext, userlist and tokenlist"""
        self.ctx = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")
        # set master token, being careful of what user supplies
        # is hex string of uuid4
        self.masterToken = self.buildMasterToken(masterToken)
        # convert it to int - is base 16
        self.mti = int(self.masterToken, 16)
        # we need this for xor-ing.

    def buildMasterToken(self, token):
        if token is None:
            masterToken = uuid.uuid4().hex
            print("No masterToken given, creating one")
        else:
            try:
                masterToken = uuid.UUID(token).hex
                print("Supplied masterToken is valid. Using that.")
            except ValueError:
                masterToken = uuid.uuid4().hex
                print(
                    "Supplied masterToken is not a valid UUID. Creating new masterToken."
                )
        return masterToken

    def getMasterToken(self):
        return self.masterToken

    def checkPassword(self, password, passwordHash):
        """Check the password against the hashed one."""
        if passwordHash is None:  # if there is no hash, then always fail.
            return False
        return self.ctx.verify(password, passwordHash)

    def createToken(self):
        """Create a token for a validated user, return that token as hex and int-xor'd version for storage."""
        clientToken = uuid.uuid4().hex
        storageToken = hex(int(clientToken, 16) ^ self.mti)
        return [clientToken, storageToken]

    def validateToken(self, clientToken, storageToken):
        if hex(int(clientToken, 16) ^ self.mti) == storageToken:
            return True
        else:
            return False

    def checkStringIsUUID(self, tau):
        try:
            token = uuid.UUID(tau)
        except ValueError:
            return False
        return True

    def basicUserPasswordCheck(self, user, password):
        # username must be length 4 and alphanumeric
        if not (len(user) >= 4 and user.isalnum()):
            return False
        # password must be length 4 and not contain username.
        if (len(password) < 4) or (user in password):
            return False
        return True

    def createPasswordHash(self, password):
        return self.ctx.hash(password)
