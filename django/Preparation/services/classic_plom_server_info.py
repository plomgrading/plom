from django.db import transaction

from Preparation.models import ClassicPlomServerInformation


class ClassicPlomServerInformationService:
    @transaction.atomic
    def get_server_info(self):
        s_obj = ClassicPlomServerInformation.load()
        return s_obj.__dict__

    @transaction.atomic
    def is_server_info_valid(self):
        s_obj = ClassicPlomServerInformation.load()
        if s_obj.server_name and s_obj.server_port:
            return True
        else:
            return False

    @transaction.atomic
    def is_password_valid(self):
        s_obj = ClassicPlomServerInformation.load()
        if s_obj.server_manager_password:
            return True
        else:
            return False

    @transaction.atomic
    def validate_server_info(self, server_name, server_port):
        s_obj = ClassicPlomServerInformation.load()

        # DO REQUESTS STUFF HERE.
        # set the validated field

        if False:
            s_obj.server_name = server_name
            s_obj.server_port = server_port
            s_obj.save()
        return False

    @transaction.atomic
    def validate_password_info(self, manager_password):
        s_obj = ClassicPlomServerInformation.load()

        if not s_obj.server_name or not s_obj.server_port:
            s_obj.save()
            return False

        # DO REQUESTS STUFF HERE.
        # set the validated field

        if False:
            s_obj.server_manager_password = manager_password
            s_obj.save()
        return False
