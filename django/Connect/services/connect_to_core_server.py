import re
from typing import final
from django.db import transaction
from django.contrib.auth.hashers import make_password, check_password
from plom.messenger import Messenger, ManagerMessenger
from plom.plom_exceptions import (
    PlomConnectionError, 
    PlomConflict, 
    PlomSeriousException, 
    PlomServerNotReady, 
    PlomAuthenticationException,
)

from Connect.models import CoreServerConnection, CoreManagerLogin


class CoreConnectionService:
    """Handle connecting and communicating with a core Plom server
    
    TODO: Does not verify SSL yet!
    """

    def __init__(self):
        self.client_version = self.get_connection().client_version
        self.api = self.get_connection().api_number
        self.manager_username = 'manager'

    def get_connection(self):
        """Return the server connection object"""
        return CoreServerConnection.load()

    def get_manager(self):
        """Return the manager login details object"""
        return CoreManagerLogin.load()

    def get_manager_password(self):
        """Return the password of the manager account"""
        return self.get_manager().password

    def get_server_version(self):
        """Return the server/client version of Core Plom and the API number of the server"""
        return self.get_connection().server_details

    def get_server_name(self):
        """Get the name of the core server"""
        return self.get_connection().server_name

    def get_port_number(self):
        """Get the port number of the core server"""
        return self.get_connection().port_number

    def validate_url(self, s: str, port: int):
        """Use the input url to get the core server's API and version"""
        messenger = Messenger(s=s, port=port, verify_ssl=False)
        version_string = messenger.start()
        messenger.stop()
        return version_string

    def is_there_a_valid_connection(self):
        """Return True if the messenger has successfully connected to a core server - if so,
        the server version and API are stored in the database
        """
        try:
            name = self.get_server_name()
            port = self.get_port_number()
            version_string = self.validate_url(name, port)
            return version_string != ""
        except PlomConnectionError as e:
            return False

    def is_manager_authenticated(self):
        """Return True if there is valid manager login information stored in the database"""
        manager_details = self.get_manager()
        return manager_details.password != ""

    def get_messenger(self):
        """Get a messenger connected to the core server"""
        url = self.get_server_name()
        port = self.get_port_number()

        if not url or not port:
            raise RuntimeError('Unable to find classic server details. Please test the server connection first.')

        return Messenger(s=url, port=port, verify_ssl=False)

    def get_manager_messenger(self):
        """Get a manager messenger connected to the core server"""
        url = self.get_server_name()
        port = self.get_port_number()

        if not url or not port:
            raise RuntimeError('Unable to find classic server details. Please test the server connection first.')

        return ManagerMessenger(s=url, port=port, verify_ssl=False)

    def has_test_spec_been_sent(self):
        """Return True if the core server is reachable and has an uploaded test spec"""    
        messenger = None
        try:
            messenger = self.get_messenger()
            messenger.start()
            spec = messenger.get_spec()
            messenger.stop()
            return True
        except (PlomServerNotReady, PlomConnectionError, RuntimeError):
            return False
        finally:
            if messenger:
                messenger.stop()

    def has_classlist_been_sent(self):
        """Return True if core server is reachable and has an uploaded classlist"""
        messenger = None
        try:
            messenger = self.get_messenger()
            messenger.start()
            
            messenger.requestAndSaveToken(self.manager_username, self.get_manager_password())
            if not messenger.token:
                return False

            classlist = messenger.IDrequestClasslist()
            return True
        except (PlomServerNotReady, PlomConnectionError, RuntimeError):
            return False
        finally:
            if messenger:
                if messenger.token:
                    messenger.clearAuthorisation(self.manager_username, self.get_manager_password())
                messenger.stop()

    def has_db_been_initialized(self):
        """Return True if a classlist is present in the core server, and therefore the database has been initialized"""
        messenger = None
        try:
            messenger = self.get_messenger()
            messenger.start()

            messenger.requestAndSaveToken(self.manager_username, self.get_manager_password())
            if not messenger.token:
                return False

            qvmap = messenger.getGlobalQuestionVersionMap()
            print('QVMAP:', qvmap)
            return qvmap != {}
        except (PlomAuthenticationException, PlomConnectionError, RuntimeError):
            return False
        finally:
            if messenger:
                if messenger.token:
                    messenger.clearAuthorisation(self.manager_username, self.get_manager_password())
                messenger.stop()

    @transaction.atomic
    def save_connection_info(self, s: str, port: int, version_string: str):
        """Save valid connection info to the database"""
        connection_obj = self.get_connection()
        connection_obj.server_name = s
        connection_obj.port_number = port
        connection_obj.server_details = version_string
        connection_obj.save()

    @transaction.atomic
    def forget_connection_info(self):
        """Wipe connection info from the database"""
        connection_obj = self.get_connection()
        connection_obj.server_name = ""
        connection_obj.port_number = 0
        connection_obj.save()

    @transaction.atomic
    def authenticate_manager(self, manager_password: str):
        """Login as the manager, and if successful, store details"""
        messenger = self.get_messenger()
        messenger.start()

        try:
            messenger.requestAndSaveToken(self.manager_username, manager_password)

            manager = None
            if messenger.token:
                manager = self.get_manager()
                manager.password = manager_password
                manager.save()

        finally:
            messenger.clearAuthorisation(self.manager_username, manager_password)
            messenger.stop()

        return manager

    @transaction.atomic
    def forget_manager(self):
        """Wipe manager login info from the database"""
        manager = self.get_manager()
        manager.password = ""
        manager.save()

    def send_test_spec(self, spec: dict):
        """Send a test specification to the core server"""
        messenger = self.get_manager_messenger()
        messenger.start()

        manager = self.get_manager()
        password = manager.password

        try:
            messenger.requestAndSaveToken(self.manager_username, password)
            if not messenger.token:
                raise RuntimeError("Unable to authenticate manager.")
            messenger.upload_spec(spec)
        finally:
            messenger.clearAuthorisation(self.manager_username, password)
            messenger.stop()

    def send_classlist(self, classdict: list):
        """Send a classlist to the core server"""
        messenger = self.get_manager_messenger()
        messenger.start()

        manager = self.get_manager()
        password = manager.password

        try:
            messenger.requestAndSaveToken(self.manager_username, password)
            if not messenger.token:
                raise RuntimeError("Unable to authenticate manager.")
            messenger.upload_classlist(classdict)
        finally:
            messenger.clearAuthorisation(self.manager_username, password)
            messenger.stop()

    def initialize_core_db(self, version_map: dict):
        """Initialize the core server database and send a PQV map"""
        messenger = self.get_manager_messenger()
        messenger.start()

        manager = self.get_manager()
        password = manager.password

        try:
            messenger.requestAndSaveToken(self.manager_username, password)
            if not messenger.token:
                raise RuntimeError("Unable to authenticate manager.")
            vmap = messenger.InitialiseDB(version_map=version_map)
            print(vmap)
        finally:
            messenger.clearAuthorisation(self.manager_username, password)
            messenger.stop()
