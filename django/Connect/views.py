import traceback
from plom.plom_exceptions import (
    PlomConnectionError,
)

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.template.loader import render_to_string

from Papers.services import SpecificationService
from Preparation.services import (
    PQVMappingService,
    StagingStudentService,
    PrenameSettingService,
)
from Base.base_group_views import ManagerRequiredView

from Connect.services import CoreConnectionService
from Connect.forms import CoreConnectionForm, CoreManagerLoginForm


class ConnectServerManagerView(ManagerRequiredView):
    """Verify the Plom-classic connection details and the manager login."""

    def build_context(self):
        context = super().build_context()
        core = CoreConnectionService()

        url = core.get_server_name()
        port = core.get_port_number()
        form = CoreConnectionForm(
            initial={
                "server_url": url if url else "localhost",
                "port_number": port if port else 41984,
            }
        )

        manager_form = CoreManagerLoginForm(
            initial={"password": core.get_manager_password()}
        )

        context.update(
            {
                "form": form,
                "manager_form": manager_form,
                "is_valid": core.is_there_a_valid_connection(),
                "manager_logged_in": core.is_manager_authenticated(),
            }
        )

        return context

    def get(self, request):
        context = self.build_context()
        return render(request, "Connect/connect-manager-page.html", context)


class ConnectSendInfoToCoreView(ManagerRequiredView):
    """Send the test specification, classlist, and PQV map to Plom-classic"""

    template_name = "Connect/connect-send-info-page.html"

    def build_context(self):
        context = super().build_context()
        spec = SpecificationService()
        core = CoreConnectionService()
        sstu = StagingStudentService()
        pre = PrenameSettingService()
        qvs = PQVMappingService()

        context.update(
            {
                "is_valid": core.is_there_a_valid_connection(),
                "manager_details_available": core.is_manager_authenticated(),
                "spec_valid": spec.is_there_a_spec(),
                "is_spec_sent": core.has_test_spec_been_sent(),
                "classlist_required": pre.get_prenaming_setting(),
                "classlist_exists": sstu.are_there_students(),
                "is_classlist_sent": core.has_classlist_been_sent(),
                "pqvmap_exists": qvs.is_there_a_pqv_map(),
                "db_initialized": core.has_db_been_initialized(),
            }
        )

        return context

    def get(self, request):
        context = self.build_context()
        return render(request, "Connect/connect-send-info-page.html", context)


class AttemptCoreConnectionView(ManagerRequiredView):
    """Ping the core server with the URL, api version, and client version"""

    def post(self, request):
        """If the connection is valid, save core server details"""
        form_data = request.POST
        url = form_data["server_url"]
        port_number = form_data["port_number"]

        core = CoreConnectionService()

        try:
            version_string = core.validate_url(url, port_number)

            if version_string:
                core.save_connection_info(url, port_number, version_string)
                return HttpResponse(
                    f'<p id="result" class="text-success">Connection successful! {version_string}</p>'
                )

        except PlomConnectionError as e:
            print(e)
            return HttpResponse(
                f'<p id="result" style="color: red;">Unable to connect to Plom Classic. Is the server running?</p>'
            )
        except Exception:
            exception_string = traceback.format_exc(chain=False)
            print(exception_string)
            print(type(exception_string))
            return HttpResponse(
                f'<p id="result" style="color: red;">{exception_string}</p>'
            )


class ForgetCoreConnectionView(ManagerRequiredView):
    """Remove the current core server info from the database"""

    def post(self, request):
        core = CoreConnectionService()
        core.forget_connection_info()
        return HttpResponse('<p id="result">Connection details cleared.</p>')


class AttemptCoreManagerLoginView(ManagerRequiredView):
    """Log in as the core server manager account"""

    def post(self, request):
        form_data = request.POST
        password = form_data["password"]

        core = CoreConnectionService()

        try:
            core.authenticate_manager(password)
            return HttpResponse(
                f'<p id="manager_result" class="text-success">Manager login successful!</p>'
            )
        except Exception as e:
            print(e)
            return HttpResponse(f'<p id="manager_result" style="color: red;">{e}</p>')


class ForgetCoreManagerLoginView(ManagerRequiredView):
    """Remove the manager login details from the database"""

    def post(self, request):
        core = CoreConnectionService()
        core.forget_manager()
        return HttpResponse('<p id="manager_result">Manager details cleared.</p>')


class SendTestSpecToCoreView(ManagerRequiredView):
    def post(self, request):
        """Send test specification data to the core server"""
        core = CoreConnectionService()
        spec = SpecificationService()
        spec_dict = spec.get_the_spec()

        try:
            core.send_test_spec(spec_dict)
            context = self.build_context()
            context.update({"attempt": True})
            return render(request, "Connect/connect-test-spec-attempt.html", context)
        except PlomConnectionError as e:
            print(e)
            context = self.build_context()
            context.update(
                {
                    "attempt": False,
                    "exception": "Unable to connect to Plom-classic. Is the server running?",
                }
            )
            return render(request, "Connect/connect-test-spec-attempt.html", context)
        except Exception as e:
            print(e)
            context = self.build_context()
            context.update({"attempt": False, "exception": e})
            return render(request, "Connect/connect-test-spec-attempt.html", context)


class SendClasslistToCoreView(ManagerRequiredView):
    def post(self, request):
        """Send classlist to core server"""
        core = CoreConnectionService()
        sstu = StagingStudentService()

        try:
            classdict = sstu.get_classdict()
            core.send_classlist(classdict)

            context = self.build_context()
            context.update({"attempt": True})
            return render(request, "Connect/connect-classlist-attempt.html", context)
        except PlomConnectionError as e:
            print(e)
            context = self.build_context()
            context.update(
                {
                    "attempt": False,
                    "exception": "Unable to connect to Plom-classic. Is the server running?",
                }
            )
            return render(request, "Connect/connect-classlist-attempt.html", context)
        except Exception as e:
            print(e)
            context = self.build_context()
            context.update({"attempt": False, "exception": e})
            return render(request, "Connect/connect-classlist-attempt.html", context)


class SendPQVInitializeDB(ManagerRequiredView):
    """Initialize the database: send over the PQV map, create database rows, pre-id papers."""

    def post(self, request):
        core = CoreConnectionService()
        qvs = PQVMappingService()
        sstu = StagingStudentService()

        ver_map = qvs.get_pqv_map_dict()
        students = sstu.get_students()
        core.initialise_core_db(ver_map, students)
        return HttpResponseRedirect(reverse("connect_db_status"))

    def get(self, request):
        context = self.build_context()
        qvs = PQVMappingService()
        core = CoreConnectionService()

        n_to_produce = len(qvs.list_of_paper_numbers())
        latest = core.get_latest_init_db_task()
        context.update({"n_to_produce": n_to_produce, "task": latest})
        return render(request, "Connect/connect-vermap-attempt.html", context)


class CoreDBStatusView(ManagerRequiredView):
    """View the progress/status of the Core DB initialisation"""

    def build_context(self):
        context = super().build_context()
        core = CoreConnectionService()

        db_init_task = core.get_latest_init_db_task()
        db_row_tasks = core.get_db_row_status()
        pre_id_task = core.get_latest_preID_task()

        n_complete = db_row_tasks["n_complete"]
        if db_init_task.status == "complete":
            n_complete += 1
        if pre_id_task.status == "complete":
            n_complete += 1
        n_total = db_row_tasks["n_total"] + 2
        percent_complete = n_complete / n_total * 100

        context.update(
            {
                "db_init_task": db_init_task,
                "db_row_tasks": db_row_tasks,
                "pre_id_task": pre_id_task,
                "percent_complete": f"{percent_complete:.0f}%",
            }
        )
        return context

    def get(self, request):
        context = self.build_context()
        fragment = render_to_string(
            "Connect/fragments/vermap-status.html", context, request=request
        )
        context.update({"fragment": fragment})
        return render(request, "Connect/connect-vermap-attempt.html", context)


class CoreDBRefreshStatus(CoreDBStatusView):
    """Refresh progress of the Core DB initialisation"""

    def get(self, request):
        context = self.build_context()
        complete = context["pre_id_task"].status == "complete"

        status = 200
        if complete:
            status = 286

        return render(
            request, "Connect/fragments/vermap-status.html", context, status=status
        )
