from Connect.services import CoreConnectionService


class CoreUsersService(CoreConnectionService):
    """
    Handle messaging a Plom-classic instance for everything related to
    core server accounts
    """

    def create_core_user(self, someuser, password):
        """Create a user on the core server"""
        if not self.is_there_a_valid_connection():
            print("Cannot create user on Plom-classic - no connection found.")
            return

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
        if not self.is_there_a_valid_connection():
            print("Cannot enable user on Plom-classic - no connection found.")
            return

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
        if not self.is_there_a_valid_connection():
            print("Cannot disable user on Plom-classic - no connection found.")
            return

        msgr = self.get_manager_messenger()
        msgr.start()

        try:
            msgr.requestAndSaveToken(self.manager_username, self.get_manager_password())
            msgr.disableUser(someuser)
        finally:
            if msgr.token:
                msgr.clearAuthorisation(self.manager_username, self.get_manager_password())
            msgr.stop()

    def get_user_details(self):
        """
        Get details about all of the plom-classic users

        Returns:
            a dict of lists of the form `username: [enabled?, logged in?, date created, last action, papers IDd, questions marked]`
        
        """
        if not self.is_there_a_valid_connection():
            print("Cannot get user details from Plom-classic - no connection found.")
            return

        msgr = self.get_manager_messenger()
        msgr.start()

        try:
            msgr.requestAndSaveToken(self.manager_username, self.get_manager_password())
            user_details = msgr.getUserDetails()
            return user_details
        finally:
            if msgr.token:
                msgr.clearAuthorisation(self.manager_username, self.get_manager_password())
            msgr.stop()