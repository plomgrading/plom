import re
from django.db import transaction
from plom.messenger import Messenger

from Connect.models import CoreServerConnection, CoreManagerLogin


class CoreConnectionService:
    """Handle connecting and communicating with a core Plom server
    
    TODO: Does not verify SSL yet!
    """

    def get_connection(self):
        """Return the server connection object"""
        return CoreServerConnection.load()

    def get_manager(self):
        """Return the manager login details object"""
        return CoreManagerLogin.load()

    def get_client_version(self):
        """Return the server/client version of Core Plom"""
        return self.get_connection().client_version

    def get_server_url(self):
        """Get the URL of the core server"""
        return self.get_connection().server_url

    def get_port_number(self):
        """Get the port number of the core server"""
        return self.get_connection().port_number

    def get_api(self):
        """Return the Core Plom API number"""
        return self.get_connection().api

    def validate_url(self, s: str, port: int):
        """Use the input url to get the core server's API and version"""
        messenger = Messenger(s=s, port=port, verify_ssl=False)
        version_string = messenger.start()
        messenger.stop()
        return version_string

    def get_messenger(self):
        """Get a messenger connected to the core server"""
        url = self.get_server_url()
        port = self.get_port_number()

        if not url or not port:
            raise RuntimeError('Core server not validated yet.')

        return Messenger(s=url, port=port, verify_ssl=False)

    @transaction.atomic
    def save_connection_info(self, s: str, port: int, version_string: str):
        """Save valid connection info to the database"""
        connection_obj = self.get_connection()
        connection_obj.server_url = s
        connection_obj.port_number = port
        
        server_version = re.search(r'\d\.\d\.\d\.(dev)?', version_string).group(0)
        api = re.search('\d+$', version_string).group(0)
        connection_obj.client_version = server_version
        connection_obj.api = api

        connection_obj.save()

    @transaction.atomic
    def authenticate_manager(self, username: str, password: str):
        """Login as the manager, and if successful, store details"""
        messenger = self.get_messenger()
        messenger.start()
        messenger.requestAndSaveToken(username, password)

        manager = None
        if messenger.token:
            manager = self.get_manager()
            manager.manager_username = username
            manager.manager_password = password
            manager.save()

        messenger.clearAuthorisation(username, password)
        messenger.stop()

        return manager
