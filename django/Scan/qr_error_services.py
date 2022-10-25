class QRErrorService:
    def check_number_qr_codes(page_data):
        if not page_data:
            raise ValueError("Unable to read QR codes.")
        return 'error'
