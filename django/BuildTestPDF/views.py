from django.shortcuts import render
from django.views.generic import View
from braces.views import LoginRequiredMixin, GroupRequiredMixin
from BuildTestPDF.forms import BuildNumberOfPDFsForm
from django.http import FileResponse

from .services import generate_pdf
from .models import Task

from django.http import HttpResponse


# Create your views here.


class BuildTestPDFs(LoginRequiredMixin, GroupRequiredMixin, View):
    template_name = 'BuildTestPDF/build_test_pdfs.html'
    login_url = "login"
    group_required = ["manager"]
    navbar_colour = "#AD9CFF"
    form = BuildNumberOfPDFsForm()

    def get(self, request):
        context = {'navbar_colour': self.navbar_colour, 'user_group': self.group_required[0],
                   'form': self.form}
        return render(request, self.template_name, context)

    def post(self, request):
        form = BuildNumberOfPDFsForm(request.POST)
        if form.is_valid():
            number_of_pdfs = int(request.POST.get('pdfs'))
            user = request.user.username

            buffer = generate_pdf(number_of_pdfs)
            buffer.seek(0)

            return FileResponse(buffer, filename='test.pdf')
        # context = {'navbar_colour': self.navbar_colour, 'user_group': self.group_required[0],
        #            'form': self.form}
        # return render(request, self.template_name, context)
