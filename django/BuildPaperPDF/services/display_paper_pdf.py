import re


class RenamePDFFile:

    def get_PDF_name(self, file_path: str):
        return re.sub(r'^.*?/papersToPrint/', '', file_path)
