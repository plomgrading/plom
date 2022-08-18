import fitz
import shutil
from plom.create.mergeAndCodePages import create_QR_codes, pdf_page_add_labels_QRs
from django.conf import settings


class ExamMockerService:
    """Take an uploaded source file and stamp dummy QR codes/text"""

    def mock_exam(self, source_version, short_name):
        sources_dir = settings.BASE_DIR / 'sources'
        qr_code_temp_dir = sources_dir / 'qr_temp'
        if qr_code_temp_dir.exists():
            shutil.rmtree(qr_code_temp_dir)
        qr_code_temp_dir.mkdir()

        qr_codes = create_QR_codes(1, 1, 1, 111111, qr_code_temp_dir)  # dummy values

        print(qr_codes)
        shutil.rmtree(qr_code_temp_dir)

        return f"Mocking time for {short_name} {source_version}!!"