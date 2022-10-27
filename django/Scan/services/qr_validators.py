# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu

from Papers.services import SpecificationService

class QRErrorService:

    def check_qr_codes(self, page_data):
        spec_service = SpecificationService()
        spec_dictionary = spec_service.get_the_spec()
        serialized_top_three_qr = self.serialize_qr_code(page_data, "top_3")
        serialized_all_qr = self.serialize_qr_code(page_data, "all")
        serialized_public_code = self.serialize_qr_code(page_data, "public_code")
        self.check_TPV_code(serialized_all_qr)
        self.check_qr_numbers(page_data)
        self.check_qr_matching(serialized_top_three_qr)
        self.check_public_code(serialized_public_code, spec_dictionary)

    def serialize_qr_code(self, page_data, tpv_type):
        qr_code_list = []
        for q in page_data:
            paper_id = list(page_data[q].values())[0]
            page_num = list(page_data[q].values())[1]
            version_num = list(page_data[q].values())[2]
            quadrant = list(page_data[q].values())[3]
            public_code = list(page_data[q].values())[4]

            if tpv_type == "top_3":
                qr_code_list.append(paper_id + page_num + version_num)
            elif tpv_type == "all":
                qr_code_list.append(paper_id + page_num + version_num + quadrant + public_code)
            elif tpv_type == "public_code":
                qr_code_list.append(public_code)
            else:
                raise ValueError("No specific TPV type.")
        return qr_code_list

    def check_TPV_code(self, qr_list):
        """
        Check if TPV codes are 17 digits long.
        """
        for indx in qr_list:
            if len(indx) != len("TTTTTPPPVVVOCCCCC"):
                raise ValueError("Invalid QR code.")

    def check_qr_numbers(self, page_data):
        """
        Check number of QR codes in a given page.
        """
        if len(page_data) == 0:
            raise ValueError("Unable to read QR codes.")
        elif len(page_data) <= 2:
            raise ValueError("Detect less than 3 QR codes.")
        elif len(page_data) == 3:
            pass
        else:
            raise ValueError("Detected more than 3 QR codes.")

    def check_qr_matching(self, qr_list):
        """
        Check if QR codes matches. 
        This is to check if a page is folded.
        """
        for indx in range(1, len(qr_list)):
            if qr_list[indx] == qr_list[indx-1]:
                pass
            else:
                raise ValueError("QR codes do not match.")
                break
    
    def check_public_code(self, public_codes, spec_dictionary):
        """
        Check if the paper public QR code matches with spec public code.
        """
        spec_public_code = spec_dictionary['publicCode']
        for public_code in public_codes:
            if public_code == str(spec_public_code):
                pass
            else:
                raise ValueError(f"Magic code {public_code} did not match spec {spec_public_code}. Did you scan the wrong test?")
            
