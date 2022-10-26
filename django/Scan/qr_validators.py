# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu


class QRErrorService:
    def check_qr_numbers(self, page_data):
        if len(page_data) == 0:
            raise ValueError("Unable to read QR codes.")
        elif len(page_data) <= 2:
            raise ValueError("Detect less than 3 QR codes.")
        elif len(page_data) == 3:
            pass
        else:
            raise ValueError("Detected more than 3 QR codes.")

    def check_qr_matching(self, page_data):
        temp_list = [page_data[i][0:11] for i in page_data]
        for indx in range(len(temp_list)):
            if temp_list[indx] == temp_list[indx-1]:
                pass
            else:
                raise ValueError("QR codes do not match.")
