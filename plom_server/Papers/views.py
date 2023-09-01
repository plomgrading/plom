# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov

from django.urls import reverse
from django.http import HttpResponse
from django_htmx.http import HttpResponseClientRefresh

from Base.base_group_views import ManagerRequiredView
from Papers.services import (
    PaperCreatorService,
    PaperInfoService,
    SpecificationService,
)
from Papers.models import CreatePaperTask
from Preparation.services import PQVMappingService, StagingStudentService
from BuildPaperPDF.services import BuildPapersService
from Finish.services import ReassembleService


class CreateTestPapers(ManagerRequiredView):
    """Create test-papers in the database, using the test spec, classlist, and question-version map.

    Also create the associated pdf build tasks.
    """

    def post(self, request):
        print("v" * 40)
        pcs = PaperCreatorService()
        qvs = PQVMappingService()

        qvmap = qvs.get_pqv_map_dict()
        username = request.user.username
        # by default we do not create the papers in background
        status, err = pcs.add_all_papers_in_qv_map(qvmap, username, background=False)
        # TODO - if we want to do this in the background, then we
        # cannot build pdf tasks at the same time, since they need the
        # classlist...  else we have to pass required classlist info
        # to the pdf task builder one at a time.

        if not status:
            print(err)
        # note that adding the papers does not automatically create the associated pdf build tasks
        # for that we need the classlist, hence the following.
        classdict = StagingStudentService().get_classdict()
        BuildPapersService().stage_all_pdf_jobs(classdict=classdict)
        # also create all the reassemble tasks
        ReassembleService().create_all_reassembly_tasks()

        progress_url = reverse("papers_progress")
        return HttpResponse(
            f'<p class="card-text" hx-get="{progress_url}" hx-trigger="every 0.5s">Creating test-papers...</p>'
        )

    def delete(self, request):
        """For testing purposes: delete all papers from the database, and the associated build tasks."""
        PaperCreatorService().remove_all_papers_from_db()
        # note - when a paper is deleted, the associated pdf-build task is deleted as well via a signal.
        return HttpResponseClientRefresh()


class TestPaperProgress(ManagerRequiredView):
    """Get the database creation progress."""

    def get(self, request):
        n_to_produce = PQVMappingService().get_pqv_map_length()
        pinfo = PaperInfoService()
        papers_in_database = pinfo.how_many_papers_in_database()

        if papers_in_database == n_to_produce:
            return HttpResponseClientRefresh()
        else:
            percent_complete = papers_in_database / n_to_produce * 100
            progress_url = reverse("papers_progress")
            return HttpResponse(
                f"""
                <p class=\"card-text\" hx-get=\"{progress_url}\" hx-trigger=\"every 0.5s\">
                    {papers_in_database} papers complete out of {n_to_produce}
                    ({int(percent_complete)}%)
                </p>"""
            )
