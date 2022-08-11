from braces.views import GroupRequiredMixin
from django.shortcuts import render
from django.views import View

from django.http import HttpResponseRedirect, HttpResponse
from django_htmx.http import HttpResponseClientRedirect

from Preparation.services import (
    PQVMappingService,
    PrenameSettingService,
    StagingStudentService,
)


from Preparation.services.temp_functions import (
    how_many_test_versions,
    how_many_questions,
)


class PQVMappingUploadView(View):
    # group_required = [u"manager"]
    def post(self, request):        
        context = {}
        return render(request, "Preparation/pqv_mapping_attempt.html", context)


class PQVMappingDownloadView(View):
    # group_required = [u"manager"]
    def get(self, request):
        pqvs = PQVMappingService()
        pqvs_csv_txt = pqvs.get_pqv_map_as_csv()
        return HttpResponse(pqvs_csv_txt, content_type="text/plain")


class PQVMappingDeleteView(View):
    # group_required = [u"manager"]
    def delete(self, request):
        pqvs = PQVMappingService()
        pqvs.remove_pqv_map()
        return HttpResponseClientRedirect(".")


class PQVMappingView(View):
    # group_required = [u"manager"]
    def build_context(self):
        pqvs = PQVMappingService()
        pss = PrenameSettingService()
        sss = StagingStudentService()

        context = {
            "number_of_questions": how_many_questions(),
            "question_list": range(1, 1 + how_many_questions()),
            "prenaming": pss.get_prenaming_setting(),
            "pqv_mapping_present": pqvs.is_there_a_pqv_map(),
            "number_of_students": sss.how_many_students(),
            "student_list_present": sss.are_there_students(),
        }
        fpp, lpp = sss.get_first_last_prenamed_paper()
        context.update({"first_prenamed_paper": fpp, "last_prenamed_paper": lpp})

        # TODO - this logic should be put somewhere more central
        min_number_to_produce = max(
            context["number_of_students"] * 1.1, context["number_of_students"] + 20
        )
        if lpp is not None:
            if lpp > min_number_to_produce:
                min_number_to_produce = lpp + 10
        context["min_number_to_produce"] = min_number_to_produce

        if context["pqv_mapping_present"]:
            context["pqv_table"] = pqvs.get_pqv_map_as_table(
                prenaming=context["prenaming"]
            )

        return context

    def get(self, request):
        context = self.build_context()
        return render(request, "Preparation/pqv_mapping_manage.html", context)

    def post(self, request):
        ntp = request.POST.get("number_to_produce", None)
        if not ntp:
            return HttpResponseRedirect(".")
        try:
            number_to_produce = int(ntp)
        except ValueError:
            return HttpResponseRedirect(".")

        pqvs = PQVMappingService()
        pqvs.generate_and_set_pqvmap(number_to_produce)
        return HttpResponseRedirect(".")
