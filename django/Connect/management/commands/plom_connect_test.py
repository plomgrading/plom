import getpass

from django.core.management.base import BaseCommand
from plom.plom_exceptions import PlomConnectionError

from Connect.services import CoreConnectionService


class Command(BaseCommand):
    help = "Display the connection status of a Plom-classic server. Alternatively, set server name, port number, and manager login details."

    def try_server_connection(self, server_name, port_number):
        core = CoreConnectionService()

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

    def try_manager_details(self, password):
        core = CoreConnectionService()

        if not core.is_there_a_valid_connection():
            self.stderr.write(
                "Unable to validate manager login - valid Plom-classic connection not found."
            )
        else:
            manager = core.authenticate_manager(password)
            self.stdout.write("Manager login successful.")

    def add_arguments(self, parser):
        sub = parser.add_subparsers(
            dest="command",
            description="Test server connection and manager login details."
        )

        sp_server = sub.add_parser("server", help="Test Plom-classic server details.")
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

        sp_manager = sub.add_parser("manager", help="Test Plom-classic manager password.")

    def handle(self, *args, **options):
        if options['command'] == 'server':
            self.stdout.write('Testing Plom-classic server connection...')

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
                    "No port numer provided, defaulting to 41984."
                )

            self.try_server_connection(name, port)

        elif options['command'] == 'manager':
            self.stdout.write("Testing Plom-classic manager details...")
            password = getpass.getpass()
            self.try_manager_details(password)

        else:
            self.print_help("manage.py", "plom_connect_test")