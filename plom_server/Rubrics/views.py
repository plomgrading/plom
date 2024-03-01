# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Divy Patel
# Copyright (C) 2024 Colin B. Macdonald

from django.http import HttpRequest, HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect, reverse
from django.contrib.auth.models import User

from Base.base_group_views import ManagerRequiredView
from Papers.services import SpecificationService
from .services import RubricService
from .forms import RubricAdminForm, RubricWipeForm
from .forms import RubricFilterForm, RubricEditForm


class RubricAdminPageView(ManagerRequiredView):
    """Initializing rubrics, maybe other features in the future."""

    def get(self, request: HttpRequest) -> HttpResponse:
        template_name = "Rubrics/rubrics_admin.html"
        form = RubricAdminForm(request.GET)
        context = self.build_context()
        rubrics = RubricService().get_all_rubrics()
        context.update(
            {
                "rubrics": rubrics,
                "rubric_admin_form": form,
            }
        )
        return render(request, template_name, context=context)

    def post(self, request: HttpRequest) -> HttpResponse:
        template_name = "Rubrics/rubrics_admin.html"
        form = RubricAdminForm(request.POST)
        context = self.build_context()
        if form.is_valid():
            # TODO: not necessarily the one who logged in; does it matter?
            any_manager = User.objects.filter(groups__name="manager").first()
            RubricService().init_rubrics(any_manager.username)
        # and if not valid, this just kinda DTRT (?)
        rubrics = RubricService().get_all_rubrics()
        context.update(
            {
                "rubrics": rubrics,
                "rubric_admin_form": form,
            }
        )
        return render(request, template_name, context=context)


class RubricWipePageView(ManagerRequiredView):
    """Confirm before wiping rubrics."""

    def get(self, request: HttpRequest) -> HttpResponse:
        template_name = "Rubrics/rubrics_wipe.html"
        context = self.build_context()
        form = RubricWipeForm()
        # TODO: what is supposed to happen if we don't have a shortname yet?
        # TODO: do we need a `get_shortname_or_None`?  Related to Issue #2996
        context.update(
            {
                "rubric_wipe_form": form,
                "short_name": SpecificationService.get_shortname(),
                "long_name": SpecificationService.get_longname(),
                "n_rubrics": len(RubricService().get_all_rubrics()),
            }
        )
        return render(request, template_name, context=context)

    def post(self, request: HttpRequest) -> HttpResponse:
        template_name = "Rubrics/rubrics_wipe.html"
        context = self.build_context()
        form = RubricWipeForm(request.POST)
        short_name = SpecificationService.get_shortname()
        _confirm_field = "confirm_by_typing_the_short_name"
        if form.is_valid():
            if form.cleaned_data[_confirm_field] == short_name:
                RubricService().erase_all_rubrics()
                return HttpResponseRedirect(reverse("rubrics_landing"))
            form.add_error(_confirm_field, "Short name did not match")
        context.update(
            {
                "rubric_wipe_form": form,
                "short_name": SpecificationService.get_shortname(),
                "long_name": SpecificationService.get_longname(),
                "n_rubrics": len(RubricService().get_all_rubrics()),
            }
        )
        return render(request, template_name, context=context)


# helper function
def _checks_from_anyone_no_one(anyone, no_one):
    if anyone and no_one:
        raise RuntimeError('Should not be possible to set both "anyone" and "no one"')
    elif anyone:
        return (True, False, False)
    elif no_one:
        return (False, False, True)
    else:
        return (False, True, False)


class RubricAccessPageView(ManagerRequiredView):
    """Highlevel control of who can modify/create rubrics."""

    def get(self, request: HttpRequest) -> HttpResponse:
        template_name = "Rubrics/rubrics_access.html"
        # TODO: move this to Base?
        from Preparation.models import PapersPrintedSettingModel as SettingsModel

        s = SettingsModel.load()

        create_checked = _checks_from_anyone_no_one(
            s.anyone_can_create_rubrics, s.no_one_can_create_rubrics
        )
        modify_checked = _checks_from_anyone_no_one(
            s.anyone_can_modify_rubrics, s.no_one_can_modify_rubrics
        )

        context = self.build_context()
        context.update(
            {
                "successful_post": False,
                "create0_checked": create_checked[0],
                "create1_checked": create_checked[1],
                "create2_checked": create_checked[2],
                "modify0_checked": modify_checked[0],
                "modify1_checked": modify_checked[1],
                "modify2_checked": modify_checked[2],
            }
        )
        return render(request, template_name, context=context)

    def post(self, request: HttpRequest) -> HttpResponse:
        template_name = "Rubrics/rubrics_access.html"
        # todo: error handling for int conversion?
        create = request.POST.get("create", None)
        modify = request.POST.get("modify", None)

        from Preparation.models import PapersPrintedSettingModel as SettingsModel

        s = SettingsModel.load()

        if create == "permissive":
            s.anyone_can_create_rubrics = True
            s.no_one_can_create_rubrics = False
            s.save()
        elif create == "default":
            s.anyone_can_create_rubrics = False
            s.no_one_can_create_rubrics = False
            s.save()
        elif create == "locked":
            s.anyone_can_create_rubrics = False
            s.no_one_can_create_rubrics = True
            s.save()
        else:
            # TODO: 406?
            raise ValueError(f"create={create} is invalid")

        create_checked = _checks_from_anyone_no_one(
            s.anyone_can_create_rubrics, s.no_one_can_create_rubrics
        )

        if modify == "permissive":
            s.anyone_can_modify_rubrics = True
            s.no_one_can_modify_rubrics = False
            s.save()
        elif modify == "default":
            s.anyone_can_modify_rubrics = False
            s.no_one_can_modify_rubrics = False
            s.save()
        elif modify == "lockdown":
            s.anyone_can_modify_rubrics = False
            s.no_one_can_modify_rubrics = True
            s.save()
        else:
            # TODO: 406?
            raise ValueError(f"modify={modify} is invalid")

        modify_checked = _checks_from_anyone_no_one(
            s.anyone_can_modify_rubrics, s.no_one_can_modify_rubrics
        )

        context = self.build_context()
        context.update(
            {
                "successful_post": True,
                "create0_checked": create_checked[0],
                "create1_checked": create_checked[1],
                "create2_checked": create_checked[2],
                "modify0_checked": modify_checked[0],
                "modify1_checked": modify_checked[1],
                "modify2_checked": modify_checked[2],
            }
        )
        return render(request, template_name, context=context)


class RubricLandingPageView(ManagerRequiredView):
    """A landing page for displaying and analyzing rubrics."""

    def get(self, request):
        template_name = "Rubrics/rubrics_landing.html"
        rs = RubricService()
        rubric_filter_form = RubricFilterForm

        context = self.build_context()

        filter_form = rubric_filter_form(request.GET)
        rubrics = rs.get_all_rubrics()

        if filter_form.is_valid():
            question_filter = filter_form.cleaned_data["question_filter"]
            kind_filter = filter_form.cleaned_data["kind_filter"]

            if question_filter:
                rubrics = rubrics.filter(question=question_filter)

            if kind_filter:
                rubrics = rubrics.filter(kind=kind_filter)

        context.update(
            {
                "rubrics": rubrics,
                "rubric_filter_form": filter_form,
            }
        )

        return render(request, template_name, context=context)


class RubricItemView(ManagerRequiredView):
    """A page for displaying a single rubric and its annotations."""

    def get(self, request, rubric_key):
        template_name = "Rubrics/rubric_item.html"
        rs = RubricService()
        form = RubricEditForm

        context = self.build_context()

        # we need to pad the number with zeros on the left since if the keystarts
        # with a zero, it will be interpreted as a 11 digit key, which result in an error
        rubric_key = str(rubric_key).zfill(12)
        rubric = rs.get_all_rubrics().get(key=rubric_key)
        marking_tasks = rs.get_marking_tasks_with_rubric_in_latest_annotation(rubric)

        rubric_as_html = rs.get_rubric_as_html(rubric)
        context.update(
            {
                "rubric": rubric,
                "form": form(instance=rubric),
                "marking_tasks": marking_tasks,
                "rubric_as_html": rubric_as_html,
            }
        )

        return render(request, template_name, context=context)

    @staticmethod
    def post(request, rubric_key):
        form = RubricEditForm(request.POST)

        # we need to pad the number with zeros on the left since if the keystarts
        # with a zero, it will be interpreted as a 11 digit key, which result in an error
        rubric_key = str(rubric_key).zfill(12)

        if form.is_valid():
            rs = RubricService()
            rubric = rs.get_all_rubrics().get(key=rubric_key)
            for key, value in form.cleaned_data.items():
                rubric.__setattr__(key, value)
            rubric.save()
        return redirect("rubric_item", rubric_key=rubric_key)


class AnnotationItemView(ManagerRequiredView):
    """A page for displaying a single annotation."""

    def get(self, request, annotation_key):
        template_name = "Rubrics/annotation_item.html"
        rs = RubricService()

        context = self.build_context()

        annotation = rs.get_all_annotations().get(pk=annotation_key)
        rubrics = rs.get_rubrics_from_annotation(annotation)
        context.update({"annotation": annotation, "rubrics": rubrics})

        return render(request, template_name, context=context)
