from passlib.context import CryptContext
import uuid


class Authority:
    def __init__(self, userList):
        self.ctx = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")
        self.userList = userList
        self.tokenList = {}

    def addUser(self, user, password):
        if user not in self.tokenList:
            self.userList[user] = password

    def checkPassword(self, user, password):
        if user not in self.userList:
            return False
        if self.ctx.verify(password, self.userList[user]):
            return True
        else:
            return False

    def allocateToken(self, user):
        self.tokenList[user] = uuid.uuid4().hex

    def getToken(self, user):
        return self.tokenList[user]

    def authoriseUser(self, user, password):
        if self.checkPassword(user, password):
            self.allocateToken(user)
            return True
        else:
            return False

    def detoken(self, user):
        if user in self.tokenList:
            del self.tokenList[user]

    def validateToken(self, user, token):
        if user in self.tokenList:
            if token == self.tokenList[user]:
                return True
        return False
