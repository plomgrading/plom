from django.db import transaction

from Preparation.models import ClassicPlomServerInformation


class ClassicPlomServerInformationService:
    @transaction.atomic
    def get_prenaming_setting(self):
        s_obj = ClassicPlomServerInformation.load()
        return s_obj.__dict__

    @transaction.atomic
    def is_server_info_valid(self):
        s_obj = ClassicPlomServerInformation.load()
        return s_obj.server_validated

    @transaction.atomic
    def is_password_valid(self):
        s_obj = ClassicPlomServerInformation.load()
        return s_obj.password_validated

    @transaction.atomic
    def validate_server_info(self, server_name, server_port):
        s_obj = ClassicPlomServerInformation.load()
        s_obj.server_name = server_name
        s_obj.server_port = server_port
        s_obj.server_validated = False

        # DO REQUESTS STUFF HERE.
        # set the validated field

        s_obj.save()
        return False

    @transaction.atomic
    def validate_password_info(self, manager_password):
        s_obj = ClassicPlomServerInformation.load()
        s_obj.manager_password = manager_password
        s_obj.password_validated = False

        if not s_obj.server_validated:
            s_obj.save()
            return False

        # DO REQUESTS STUFF HERE.
        # set the validated field

        s_obj.save()
        return False
