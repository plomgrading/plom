import re

from plom.messenger import Messenger

from Connect.models import CoreServerConnection


class CoreConnectionService:
    """Handle connecting and communicating with a core Plom server
    
    TODO: Does not verify SSL yet!
    """

    def get_connection(self):
        """Return the server connection object"""
        return CoreServerConnection.load()

    def get_client_version(self):
        """Return the server/client version of Core Plom"""
        return self.get_connection().client_version

    def get_api(self):
        """Return the Core Plom API number"""
        return self.get_connection().api

    def validate_url(self, s: str, port: int):
        """Use the input url to get the core server's API and version"""
        messenger = Messenger(s=s, port=port, verify_ssl=False)
        version_string = messenger.start()
        messenger.stop()
        return version_string

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