import getpass

from django.core.management.base import BaseCommand
from plom.plom_exceptions import PlomConnectionError

from TestCreator.services import TestSpecService, TestSpecGenerateService
from Preparation.services import StagingStudentService, PQVMappingService, PrenameSettingService
from Connect.services import CoreConnectionService


class Command(BaseCommand):
    """A command-line tool for connecting a Plom-classic server.
    
    To use:
        `python3 manage.py plom_connec server --name [server_name] --port [port_number]` 
            will ping a plom-classic server at the URL http://[server_name]:[port_number]
        `python3 manage.py plom_connect manager` will prompt for the manager password and 
            attempt to sign in to the plom-classic manager account

        After connection + authentication:
        `python3 manage.py plom_connect send test_spec` sends a test specification to a connected server
        `python3 manage.py plom_connect send classlist` sends a classlist to a connected server
        `python3 manage.py plom_connect send init_db` sends a qv-map and initialises the classic database
        `python3 manage.py plom_connect send all` performs the above three steps in one go
    """

    help = "Tools for connecting to a Plom-classic server, logging in to the manager account, and sending information from WebPlom."

    def connect_to_server(self, server_name, port_number):
        core = CoreConnectionService()

        version_string = None
        try:
            version_string = core.validate_url(server_name, port_number)
        except PlomConnectionError:
            self.stderr.write(
                "Unable to connect to Plom-classic. Is the server running?"
            )
        
        if version_string:
            self.stdout.write(
                f"Connection established! {version_string}"
            )
            core.save_connection_info(server_name, port_number, version_string)

    def login_manager(self, password):
        core = CoreConnectionService()

        if not core.is_there_a_valid_connection():
            self.stderr.write(
                "Unable to validate manager login - valid Plom-classic connection not found."
            )
        else:
            manager = core.authenticate_manager(password)
            self.stdout.write("Manager login successful.")

    def send_test_spec(self):
        spec = TestSpecService()
        if not spec.is_specification_valid():
            self.stderr.write(
                "Valid test specification not found. Please upload one using plom_preparation_test_spec."
            )
            return

        spec_dict = TestSpecGenerateService(spec).generate_spec_dict()

        core = CoreConnectionService()
        if not core.is_there_a_valid_connection():
            self.stderr.write(
                "Valid Plom-classic connection not found. Please test with plom_connect_test."
            )
            return

        core.send_test_spec(spec_dict)
        return spec_dict

    def send_classlist(self):
        sstu = StagingStudentService()
        if not sstu.are_there_students():
            self.stderr.write(
                "No students found. Please upload a classlist using plom_preparation_classlist."
            )
            return

        classdict = sstu.get_classdict()

        core = CoreConnectionService()
        if not core.is_there_a_valid_connection():
            self.stderr.write(
                "Valid Plom-classic connection not found. Please test with plom_connect_test."
            )
            return

        core.send_classlist(classdict)
        return classdict
    
    def init_db(self):
        qvs = PQVMappingService()
        if not qvs.is_there_a_pqv_map():
            self.stderr.write(
                "No question-version map found. Please upload one using plom_preparation_qvmap."
            )
            return
        
        qvmap = qvs.get_pqv_map_dict()

        core = CoreConnectionService()
        if not core.is_there_a_valid_connection():
            self.stderr.write(
                "Valid Plom-classic connection not found. Please test with plom_connect_test."
            )
            return

        pre = PrenameSettingService()
        if pre.get_prenaming_setting() and not core.has_classlist_been_sent():
            self.stderr.write(
                "Prenaming is enabled, but a classlist has not been detected in Plom-classic. Please upload one using plom_preparation_classlist."
            )
            return

        # use call_local to run huey task functions in the foreground.
        self.stdout.write("Initialising the database...")
        core._initialise_core_db.call_local(core, qvmap)

        self.stdout.write("Adding test-papers to database...")
        n_to_produce = len(qvmap)
        for i in range(1, n_to_produce+1):
            core._add_db_row.call_local(core, i, qvmap[i])

        sstu = StagingStudentService()
        if sstu.are_there_students():
            self.stdout.write("Classlist detected - pre-IDing papers...")
            students = sstu.get_students()
            core._preID_papers.call_local(core, students)

        return qvmap

    def send_all(self):
        self.stdout.write("Checking if all information is present...")
        spec = TestSpecService()
        if not spec.is_specification_valid():
            self.stderr.write(
                "Valid test specification not found. Please upload one using plom_preparation_test_spec."
            )
            return

        pre = PrenameSettingService()
        sstu = StagingStudentService()
        if pre.get_prenaming_setting() and not sstu.are_there_students():
            self.stderr.write(
                "Prenaming enabled, but classlist not found. Please upload one using plom_preparation_classlist."
            )
            return

        qvs = PQVMappingService()
        if not qvs.is_there_a_pqv_map():
            self.stderr.write(
                "No question-version map found. Please upload one using plom_preparation_qvmap."
            )
            return

        self.stdout.write("Sending test specification...")
        the_spec = self.send_test_spec()
        if not the_spec:
            return

        if sstu.are_there_students():
            self.stdout.write("Sending classlist...")
            the_classlist = self.send_classlist()
            if not the_classlist:
                return

        self.stdout.write("Sending question-version map and initializing the database...")
        the_qvmap = self.init_db()
        if not the_qvmap:
            return

        return True

    def add_arguments(self, parser):
        sub = parser.add_subparsers(
            dest="command",
            description="Connect to a server, authenticate manager, and send information.."
        )

        sp_server = sub.add_parser("server", help="Connect to a Plom-classic server.")
        sp_server.add_argument(
            "--name",
            type=str,
            help="Server name - if not present, defaults to localhost.",
        )
        sp_server.add_argument(
            "--port",
            type=int,
            help="Server port - if not present, defaults to 41984.",
        )

        sp_manager = sub.add_parser("manager", help="Log in to the Plom-classic manager account.")

        sp_send = sub.add_parser("send", help="Send information to a connected Plom-classic server.")
        sp_send.add_argument(
            "info_to_send",
            choices=["test_spec", "classlist", "init_db", "all"],
            help="Information to send: test specification, classlist, qv-map/database initialization, or everything at once."
        )

    def handle(self, *args, **options):
        if options['command'] == 'server':
            self.stdout.write('Connecting to a Plom-classic server...')

            name = 'localhost'
            if options['name']:
                name = options['name']
            else:
                self.stdout.write(
                    "No server name provided, defaulting to 'localhost'"
                )
            
            port = 41984
            if options['port']:
                port = options['port']
            else:
                self.stdout.write(
                    "No port number provided, defaulting to 41984."
                )

            self.connect_to_server(name, port)

        elif options['command'] == 'manager':
            self.stdout.write("Testing Plom-classic manager details...")
            password = getpass.getpass()
            self.login_manager(password)

        elif options['command'] == 'send':
            if options["info_to_send"] == "test_spec":
                self.stdout.write("Sending test specification...")
                the_spec = self.send_test_spec()
                if the_spec:
                    self.stdout.write("Test specification sent to Plom-classic server.")
            elif options["info_to_send"] == "classlist":
                self.stdout.write("Sending classlist...")
                the_classlist = self.send_classlist()
                if the_classlist:
                    self.stdout.write("Classlist sent to Plom-classic server.")
            elif options["info_to_send"] == "init_db":
                self.stdout.write(
                    "Sending question-version map and initialising the Plom-classic database..."
                )
                the_qvmap = self.init_db()
                if the_qvmap:
                    self.stdout.write("QV-map sent and classic database initialised.")
            else:
                self.stdout.write("Sending everything to Plom-classic server...")
                the_qvmap = self.send_all()
                if the_qvmap:
                    self.stdout.write("Plom-classic server initialised.")

        else:
            self.print_help("manage.py", "plom_connect_test")