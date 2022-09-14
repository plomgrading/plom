from Connect.services import CoreConnectionService


class CoreUsersService(CoreConnectionService):
    """
    Handle messaging a Plom-classic instance for everything related to
    core server accounts
    """

    def create_core_user(self, someuser, password):
        """Create a user on the core server"""
        msgr = self.get_manager_messenger()
        msgr.start()

        try:
            msgr.requestAndSaveToken(self.manager_username, self.get_manager_password())
            msgr.createModifyUser(someuser, password)
        finally:
            if msgr.token:
                msgr.clearAuthorisation(self.manager_username, self.get_manager_password())
            msgr.stop()

    def enable_core_user(self, someuser):
        """Enable a user in the core server"""
        msgr = self.get_manager_messenger()
        msgr.start()

        try:
            msgr.requestAndSaveToken(self.manager_username, self.get_manager_password())
            msgr.enableUser(someuser)
        finally:
            if msgr.token:
                msgr.clearAuthorisation(self.manager_username, self.get_manager_password())
            msgr.stop()

    def disable_core_user(self, someuser):
        """Disable a user in the core server"""
        msgr = self.get_manager_messenger()
        msgr.start()

        try:
            msgr.requestAndSaveToken(self.manager_username, self.get_manager_password())
            msgr.disableUser(someuser)
        finally:
            if msgr.token:
                msgr.clearAuthorisation(self.manager_username, self.get_manager_password())
            msgr.stop()