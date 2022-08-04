from braces.views import GroupRequiredMixin
from django import forms
from django.shortcuts import render
from django.views import View

from django_htmx.http import HttpResponseClientRedirect


from Classlist.services import ClasslistCSVService, ClasslistService


class ClasslistUploadForm(forms.Form):
    classlist_file = forms.FileField(
        label="Classlist csv file",
        widget=forms.FileInput(attrs={"accept": ".csv"}),
    )


class ClasslistView(View):
    # group_required = [u"manager"]

    def get(self, request, everyone=None):
        cls = ClasslistService()

        form = ClasslistUploadForm()

        context = {
            "form": form,
            "classlist": cls.get_students(),
        }
        return render(request, "Classlist/classlist_show.html", context)

    def post(self, request):
        form = ClasslistUploadForm(request.POST, request.FILES)
        if form.is_valid():
            clcsvs = ClasslistCSVService()
            success, warn_err = clcsvs.take_classlist_from_upload(
                request.FILES["classlist_file"]
            )
            context = {"form": form, "success": success, "warn_err": warn_err}
            return render(request, "Classlist/classlist_attempt.html", context)
        else:
            return HttpResponseClientRedirect("/classlist")

    def delete(self, request, everyone=None):
        clcsvs = ClasslistCSVService()
        clcsvs.delete_classlist_csv()
        return HttpResponseClientRedirect("/classlist")
