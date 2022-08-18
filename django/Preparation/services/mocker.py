import fitz
from plom.create.mergeAndCodePages import create_QR_codes, pdf_page_add_labels_QRs


class ExamMockerService:
    """Take an uploaded source file and stamp dummy QR codes/text"""

    def mock_exam(self, source_version, short_name):
        pass