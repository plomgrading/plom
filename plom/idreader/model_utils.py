# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2020-2023 Colin B. Macdonald
# Copyright (C) 2024-2025 Deep Shah

"""Utilities to load the digit-prediction model."""

from pathlib import Path

# import torch
import shutil
from huggingface_hub import hf_hub_download
import onnxruntime as ort


CNN_MODEL_FILENAME = "mnist_emnist_blank_cnn_v1.onnx"

HF_REPO_ID = "deepshah23/digit-blank-classifier-cnn"

CNN_MODEL_SOURCE_PATH = "../../mnist_emnist_blank_cnn_v1.onnx"

# Set this to "HUGGINGFACE" to download from the Hub, or "LOCAL" to copy from a local path.
MODEL_SOURCE_TYPE = "HUGGINGFACE"


def load_model(where=Path("model_cache")):
    """Load the digit-predictor TorchScript model from the cache."""
    filename = where / CNN_MODEL_FILENAME
    if not filename.exists():
        raise FileNotFoundError(
            f"Model file not found at {filename}. Please run the copy/download command."
        )

    try:
        session = ort.InferenceSession(
            str(filename), providers=["CUDAExecutionProvider", "CPUExecutionProvider"]
        )
        print(f"ONNX model '{filename}' loaded successfully into ONNX Runtime.")

        return session, "cpu"
    except Exception as e:
        print(f"Error loading ONNX model: {e}")
        raise


def is_model_present(where=Path("model_cache")):
    """Checks if the ML model is available in the cache."""
    return (where / CNN_MODEL_FILENAME).exists()


def copy_model_to_cache(where=Path("model_cache")):
    """Copy the local model file to the model_cache directory."""
    where.mkdir(exist_ok=True)
    source_file_path = (
        Path(__file__).resolve().parent / CNN_MODEL_SOURCE_PATH
    ).resolve()
    destination_file_path = where / CNN_MODEL_FILENAME

    print(f"Attempting to copy model from: {source_file_path}")
    if not source_file_path.exists():
        print(f"\tERROR: Source model file not found at '{source_file_path}'.")
        return False
    try:
        shutil.copy(source_file_path, destination_file_path)
        print(f"\tSuccessfully copied model to {destination_file_path}")
    except Exception as e:
        print(f"\tError copying file: {e}")
        return False
    return True


def download_model_from_hf(where=Path("model_cache")):
    """Download the model from Hugging Face Hub and place it in our cache."""
    where.mkdir(exist_ok=True)
    destination_file_path = where / CNN_MODEL_FILENAME

    print(f"Downloading model from Hugging Face repo: {HF_REPO_ID}")
    try:

        hf_cached_path = hf_hub_download(
            repo_id=HF_REPO_ID, filename=CNN_MODEL_FILENAME
        )
        shutil.copy(hf_cached_path, destination_file_path)
        print(f"\tSuccessfully downloaded and cached model to {destination_file_path}")
    except Exception as e:
        print(f"\tError downloading from Hugging Face Hub: {e}")
        return False
    return True


def ensure_model_available(where=Path("model_cache")):
    """Check if model is present in cache, and if not, get it based on MODEL_SOURCE_TYPE."""
    if is_model_present(where):
        print("Model is already present in cache; no action required.")
        return

    print("Model not found in cache.")

    if MODEL_SOURCE_TYPE == "HUGGINGFACE":
        print("Source is Hugging Face. Will try to download.")
        if download_model_from_hf(where):
            print("Successfully downloaded model from Hugging Face.")
        else:
            print("Could not download the model from Hugging Face.")

    elif MODEL_SOURCE_TYPE == "LOCAL":
        print("Source is Local Path. Will try to copy.")
        if copy_model_to_cache(where):
            print("Successfully copied local model to cache.")
        else:
            print("Could not copy the local model.")

    else:
        print(
            f"ERROR: Invalid MODEL_SOURCE_TYPE: '{MODEL_SOURCE_TYPE}'. Must be 'HUGGINGFACE' or 'LOCAL'."
        )
