# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2024-2025 Colin B. Macdonald
# Copyright (C) 2024-2025 Andrew Rechnitzer

from django.http import FileResponse

from plom_server.Base.base_group_views import ManagerRequiredView

from ..services import ReassembleService


class StudentReportView(ManagerRequiredView):
    def get(self, request, paper_number):
        """Return the student report pdf of the given paper."""
        pdf_file, filename = ReassembleService.get_single_student_report(paper_number)
        return FileResponse(pdf_file, filename=filename)
