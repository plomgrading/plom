# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Aidan Murphy

import os
from importlib import resources
from logging import Logger
from pathlib import Path
from typing import Any
import plom_server as _plom_server_base

import yaml

# The locations of the .yaml config files relative to this file
PROD_CONFIG_FILE = "log_config_prod.yaml"
DEV_CONFIG_FILE = "log_config_dev.yaml"


def get_logging_config_dict(
    *,
    dev: bool = False,
    log_dir: Path | str = Path("./"),
    log_filename: str = "plom_server.log",
) -> dict[str, Any]:
    """Read project logging configuration.

    Note "log_dir" and "log_filename" are only relevant if "dev" is false.

    Keyword Args:
        dev: Whether the dev or production logging config should be read.
        log_dir: a default for where the logfile should be placed if
            the PLOM_BASE_DIR env var is not set.
        log_filename: a name for the log file.

    Returns:
        A dictionary to be consumed by logging.dictConfig.
    """
    # read .yaml file into dict
    relative_log_config_path = DEV_CONFIG_FILE if dev else PROD_CONFIG_FILE
    log_config_file = resources.files(_plom_server_base) / relative_log_config_path
    with log_config_file.open("r") as f:
        log_config_dict = yaml.safe_load(f)

    # substitute file location
    if not dev:
        log_dir = Path(os.environ.get("PLOM_BASE_DIR", log_dir))
        log_config_dict["handlers"]["file"]["filename"] = str(log_dir / log_filename)

    return log_config_dict


# Source - https://stackoverflow.com/a/21978778
# Posted by jfs, modified by community. See post 'Timeline' for change history
# Retrieved 2026-05-26, License - CC BY-SA 3.0
def log_subprocess_output(pipe_bytes: bytes, log: Logger) -> None:
    """Log the output of a subprocess.

    Args:
        pipe_bytes: the output of a subprocess.
        log: the logger to use.
    """
    pipe = pipe_bytes.decode("utf-8")
    for line in iter(pipe.splitlines()):  # b'\n'-separated lines
        log.info("%r", line)
