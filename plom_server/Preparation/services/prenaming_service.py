# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald

from django.db import transaction

from ..models import PrenamingSetting


class PrenameSettingService:
    @transaction.atomic
    def get_prenaming_setting(self):
        p_obj = PrenamingSetting.load()
        return p_obj.enabled

    @transaction.atomic
    def set_prenaming_setting(self, enable_disable):
        p_obj = PrenamingSetting.load()
        p_obj.enabled = enable_disable
        p_obj.save()
