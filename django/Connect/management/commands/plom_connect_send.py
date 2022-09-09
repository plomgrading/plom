from django.core.management.base import BaseCommand

from Connect.services import CoreConnectionService
from TestCreator.services import TestSpecService, TestSpecGenerateService
from Preparation.services import StagingStudentService, PQVMappingService


class Command(BaseCommand):
    help = "Send test specification or classlist to a Plom-classic server. Or, send a QV-map and initialize the database."

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
        self.stdout.write("Sending test specification...")
        spec = self.send_test_spec()
        if not spec:
            return

        sstu = StagingStudentService()
        if sstu.are_there_students():
            self.stdout.write("Sending classlist...")
            classlist = self.send_classlist()
            if not classlist:
                return

        self.stdout.write("Setting up Plom-classic database...")
        qvmap = self.init_db()
        return qvmap

    def add_arguments(self, parser):
        sub = parser.add_subparsers(
            dest="command",
            description="Send information to Plom-classic server."
        )

        sp_testspec = sub.add_parser("test_spec", help="Send test specification to Plom-classic.")
        sp_classlist = sub.add_parser("classlist", help="Send classlist to Plom-classic.")
        sp_initdb = sub.add_parser(
            "init_db", 
            help="In one step, send question-version map to Plom-classic, pre-ID test papers, and initialise the Plom-classic database."
        )
        sp_all = sub.add_parser("all", help="Send all the required information to Plom-Classic and initialise the database.")

    def handle(self, *args, **options):
        if options['command'] == "test_spec":
            self.stdout.write(
                "Sending test specification to Plom-classic..."
            )
            spec = self.send_test_spec()
            if spec:
                self.stdout.write(
                    "Specification sent!"
                )
        elif options['command'] == "classlist":
            self.stdout.write(
                "Sending classlist to Plom-classic..."
            )
            classlist = self.send_classlist()
            if classlist:
                self.stdout.write(
                    "Classlist sent!"
                )
        elif options['command'] == "init_db":
            self.stdout.write(
                "Setting up Plom-classic database..."
            )
            qvmap = self.init_db()
            if qvmap:
                self.stdout.write(
                    "Database initialised!"
                )
        elif options['command'] == 'all':
            self.stdout.write(
                "Sending everything to Plom-classic..."
            )
            qvmap = self.send_all()
            if qvmap:
                self.stdout.write(
                    "Database initialised!"
                )
        else:
            self.print_help("manage.py", "plom_connect_send")