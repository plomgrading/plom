# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2020-2022 Colin B. Macdonald

import gzip
from pathlib import Path
import pickle

import sklearn


def load_model():
    """Load the model from disc."""
    filename = f"RF_ML_model_sklearn{sklearn.__version__}.gz"
    with gzip.open(Path("model_cache") / filename, "rb") as f:
        prediction_model = pickle.load(f)

    return prediction_model
