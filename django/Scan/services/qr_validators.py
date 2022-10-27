# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu


class QRErrorService:

    def check_TPV_code(self, page_data):
        temp_list = []
        for q in page_data:
            paper_id = list(page_data[q].values())[0]
            page_num = list(page_data[q].values())[1]
            version_num = list(page_data[q].values())[2]
            quadrant = list(page_data[q].values())[3]
            public_code = list(page_data[q].values())[4]
            temp_list.append(paper_id + page_num + version_num + quadrant + public_code)
        
        for indx in templist:
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

    def check_qr_matching(self, page_data):
        """
        Check if QR codes matches. 
        This is to check if a page is folded.
        """
        temp_list = []
        for quadrant in page_data:
            paper_id = list(page_data[quadrant].values())[0]
            page_num = list(page_data[quadrant].values())[1]
            version_num = list(page_data[quadrant].values())[2]
            temp_list.append(paper_id + page_num + version_num)
        
        for indx in range(1, len(temp_list)):
            if temp_list[indx] == temp_list[indx-1]:
                pass
            else:
                raise ValueError("QR codes do not match.")
                break
    
    def check_public_code(self, page_data):
        pass
