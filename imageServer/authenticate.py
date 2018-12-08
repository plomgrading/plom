import uuid
from passlib.context import CryptContext


class Authority:
    """A class to do all our authentication
    - user list, passwords and tokens.
    """
    def __init__(self, userList):
        """Set up cryptocontext, userlist and tokenlist"""
        self.ctx = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"],
                                deprecated="auto")
        self.userList = userList
        self.tokenList = {}

    def addUser(self, user, password):
        """Add a user/password to the list if not already there."""
        if user not in self.tokenList:
            self.userList[user] = password

    def checkPassword(self, user, password):
        """Check the password against the hashed one stored."""
        if user not in self.userList:
            return False
        return self.ctx.verify(password, self.userList[user])

    def allocateToken(self, user):
        """Create a token for a validated user"""
        self.tokenList[user] = uuid.uuid4().hex

    def getToken(self, user):
        return self.tokenList[user]

    def authoriseUser(self, user, password):
        """Check the user's password against list.
        If successful allocate a token and return true.
        """
        if self.checkPassword(user, password):
            self.allocateToken(user)
            return True
        else:
            return False

    def detoken(self, user):
        """Remove given user's token from list"""
        if user in self.tokenList:
            del self.tokenList[user]

    def validateToken(self, user, token):
        """Check user's token against list"""
        if user in self.tokenList:
            if token == self.tokenList[user]:
                return True
        return False
