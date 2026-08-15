# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Deep Shah

import os
from unittest.mock import call, patch

from plom_server.scripts.launch_plom_demo_server import run_the_auto_id_reader


@patch("plom_server.scripts.launch_plom_demo_server.run_django_manage_command")
def test_auto_id_reader_is_skipped_without_digit_service(run_command) -> None:
    with patch.dict(os.environ, {"PLOM_ML_SERVICE_URL": "   "}):
        run_the_auto_id_reader()

    run_command.assert_not_called()


@patch("plom_server.scripts.launch_plom_demo_server.run_django_manage_command")
def test_auto_id_reader_runs_with_digit_service(run_command) -> None:
    with patch.dict(os.environ, {"PLOM_ML_SERVICE_URL": "https://digits.example"}):
        run_the_auto_id_reader()

    assert run_command.call_args_list == [
        call("plom_run_id_reader --run"),
        call("plom_run_id_reader --wait"),
    ]
