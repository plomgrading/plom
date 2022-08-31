from django.db import transaction
from django.contrib.auth.hashers import make_password, check_password
from django_huey import db_task, get_queue
from huey.signals import SIGNAL_EXECUTING, SIGNAL_ERROR, SIGNAL_COMPLETE
from plom.messenger import Messenger, ManagerMessenger
from plom.plom_exceptions import (
    PlomConnectionError, 
    PlomConflict, 
    PlomExistingLoginException, 
    PlomServerNotReady, 
    PlomAuthenticationException,
)

from Connect.models import (
    CoreServerConnection, 
    CoreManagerLogin,
    CoreDBinitialiseTask,
)


class CoreConnectionService:
    """Handle connecting and communicating with a core Plom server
    
    TODO: Does not verify SSL yet!
    """

    queue = get_queue('tasks')

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
        except (PlomServerNotReady, PlomConnectionError, PlomExistingLoginException, RuntimeError):
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
        except (PlomServerNotReady, PlomConnectionError, PlomExistingLoginException, RuntimeError):
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
            return qvmap != {}
        except (PlomAuthenticationException, PlomConnectionError, PlomExistingLoginException, RuntimeError):
            return False
        finally:
            if messenger:
                if messenger.token:
                    messenger.clearAuthorisation(self.manager_username, self.get_manager_password())
                messenger.stop()

    def get_core_spec(self):
        """Get the test specification from the core server, including a public code"""
        messenger = None
        try:
            messenger = self.get_messenger()
            messenger.start()
            return messenger.get_spec()
        finally:
            if messenger:
                messenger.stop()

    @transaction.atomic
    def save_connection_info(self, s: str, port: int, version_string: str):
        """Save valid connection info to the database"""
        connection_obj = self.get_connection()
        connection_obj.server_name = s
        connection_obj.port_number = port
        connection_obj.server_details = version_string
        connection_obj.save()

        old_db_tasks = CoreDBinitialiseTask.objects.all()
        old_db_tasks.delete()

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

    def create_core_db_task(self, huey_id):
        """Save a huey task to the database"""
        task = CoreDBinitialiseTask(
            status = 'todo',
            huey_id = huey_id
        )
        task.save()
        return task

    def initialise_core_db(self, version_map: dict):
        db_task = self._initialise_core_db(self, version_map)
        task_obj = self.create_core_db_task(db_task.id)
        task_obj.status = 'queued'
        task_obj.save()
        return task_obj

    @db_task(queue='tasks')
    def _initialise_core_db(ccs, version_map: dict):
        """Initialise the core server database and send a PQV map"""
        messenger = ccs.get_manager_messenger()
        messenger.start()

        try:
            messenger.requestAndSaveToken(ccs.manager_username, ccs.get_manager_password())
            if not messenger.token:
                raise RuntimeError("Unable to authenticate manager.")
            vmap = messenger.InitialiseDB()
            for i in range(1,len(vmap)+1):
                status = messenger.appendTestToDB(i, vmap[i])
                print(status)
        finally:
            messenger.clearAuthorisation(ccs.manager_username, ccs.get_manager_password())
            messenger.stop()

    def get_latest_init_db_task(self, sense_core_db=True):
        """Get the latest Init DB task
        
        TODO: for now, there's a crude way to tell the difference between the latest task for the current
        server, and one from a previous server
        """
        tasks = CoreDBinitialiseTask.objects.all().order_by('created')
        if len(tasks) > 0:
            latest_task = tasks[0]
            if sense_core_db and latest_task.status == 'complete' and not self.has_db_been_initialized():
                return None
            return tasks[0]
