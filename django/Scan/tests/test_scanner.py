# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates

from pyzbar.pyzbar import decode
from pyzbar.pyzbar import ZBarSymbol
from PIL import Image
from django.test import TestCase

from plom.scan import QRextract
from Scan.services import ScanService


class ScanServiceTests(TestCase):
    def test_read_qr_codes(self):
        codes = QRextract("Scan/tests/test_zbar_fails.png", write_to_file=False)
        self.assertEqual(codes["NE"], [])  # staple
        self.assertEqual(codes["NW"], ["00002806012823730"])
        self.assertEqual(codes["SE"], ["00002806014823730"])
        self.assertEqual(codes["SW"], ["00002806013823730"])

        # codes = QRextract("Scan/tests/page1.png", write_to_file=False)
        # print(codes)
        # self.assertEqual(codes["NW"], [])
        # self.assertEqual(codes["NE"], ["00000101011247218"])
        # self.assertEqual(codes["SW"], ["00000101013247218"])
        # self.assertEqual(codes["SE"], ["00000101014247218"])

        img = Image.open("Scan/tests/page0.png")
        codes = decode(img, symbols=[ZBarSymbol.QRCODE])
        print(codes)
