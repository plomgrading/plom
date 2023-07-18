from braces.views import GroupRequiredMixin, LoginRequiredMixin
from django.views import View


class ManagerRequiredBaseView(LoginRequiredMixin, GroupRequiredMixin, View):
    login_url = "login"
    group_required = ["manager"]
