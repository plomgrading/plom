from django.views.generic import View
from braces.views import LoginRequiredMixin, GroupRequiredMixin


# Create your views here.
class ManagerRequiredView(LoginRequiredMixin, GroupRequiredMixin, View):
    """A base class view for managers"""
    group_required = ["manager"]
    login_url = "login"
    navbar_colour = "#AD9CFF"

    def build_context(self):
        context = {
            'navbar_colour': self.navbar_colour,
            'user_group': self.group_required[0],
        }

        return context
