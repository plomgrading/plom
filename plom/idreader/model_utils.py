# # SPDX-License-Identifier: AGPL-3.0-or-later
# # Copyright (C) 2018-2020 Andrew Rechnitzer
# # Copyright (C) 2020 Dryden Wiebe
# # Copyright (C) 2020 Vala Vakilian
# # Copyright (C) 2020-2023 Colin B. Macdonald

# """Utilities to load the digit-prediction model."""

# import gzip
# from pathlib import Path
# import pickle

# import requests
# import sklearn

# from .trainRandomForestModel import train_model


# def load_model(where=Path("model_cache")):
#     """Load the digit-predictor model from disc.

#     Args:
#         where (None/pathlib.Path): where to find the the model, defaults
#             to "model_cache/" under the current working directory.

#     Returns:
#         sklearn.RandomForestClassifier: a model trained to predict
#         digits in bitmaps.
#     """
#     filename = f"RF_ML_model_sklearn{sklearn.__version__}.gz"
#     with gzip.open(where / filename, "rb") as f:
#         return pickle.load(f)


# def is_model_present(where=Path("model_cache")):
#     """Checks if the ML model is available.

#     Args:
#         where (pathlib.Path): where to find the the model, defaults
#             to "model_cache/" under the current working directory.

#     Returns:
#         boolean: True/False, indicating if the model is present.
#     """
#     filename = f"RF_ML_model_sklearn{sklearn.__version__}.gz"
#     return (where / filename).exists()


# def download_model(where=Path("model_cache")):
#     """Try to download the model, respond with False if unsuccessful.

#     Args:
#         where (None/pathlib.Path): where to look for / put the model,
#             defaults to "model_cache/" under the current directory.

#     Returns:
#         boolean: True/False about if the model was successful.
#     """
#     where.mkdir(exist_ok=True)

#     base_url = "https://gitlab.com/plom/plomidreaderdata/-/raw/main/plomBuzzword/"
#     files = [f"RF_ML_model_sklearn{sklearn.__version__}.gz"]
#     for file_name in files:
#         url = base_url + file_name
#         print("Getting {} - ".format(file_name))
#         response = requests.get(url)
#         if response.status_code != 200:
#             print("\tError getting file {}.".format(file_name))
#             return False
#         with open(where / file_name, "wb") as file_header:
#             file_header.write(response.content)
#         print("\tDone Saving")
#     return True


# def download_or_train_model(where=Path("model_cache")):
#     """Download the ID detection model if possible, if not, train it.

#     Args:
#         where (None/pathlib.Path): where to look for / put the model,
#             defaults to "model_cache/" under the current directory.

#     Returns:
#         None

#     Prints messages to stdout as it works.
#     """
#     if is_model_present(where):
#         print("Model is already present; no action required")
#         return

#     print(
#         "Will try to download model and if that fails, then train it locally (which is time-consuming)"
#     )
#     if download_model(where):
#         print("Successfully downloaded sklearn (Random-Forest) model. Good to go.")
#     else:
#         print("Could not download the model, need to train model instead.")
#         print(
#             "This will take some time -- on the order of 2-3 minutes depending on your computer."
#         )
#         train_model()


# # SPDX-License-Identifier: AGPL-3.0-or-later
# # Copyright (C) 2018-2020 Andrew Rechnitzer
# # Copyright (C) 2020 Dryden Wiebe
# # Copyright (C) 2020 Vala Vakilian
# # Copyright (C) 2020-2023 Colin B. Macdonald
# # Copyright (C) 2024-2025 Deep Shah

# """Utilities to load the digit-prediction model."""

# from pathlib import Path
# import torch
# import shutil
# from huggingface_hub import hf_hub_download


# # The filename for the model inside the cache AND on the Hub
# CNN_MODEL_FILENAME = "mnist_emnist_blank_cnn_v1.pt"

# # --- Option A: Hugging Face Hub ---
# HF_REPO_ID = "deepshah23/digit-blank-classifier-cnn" 

# # --- Option B: Local File Path ---
# # This path is relative to the location of this file (model_utils.py)
# CNN_MODEL_SOURCE_PATH = "../../mnist_emnist_blank_cnn_v1.pt"

# # --- Configuration Switch ---
# # Set this to "HUGGINGFACE" to download from the Hub, or "LOCAL" to copy from a local path.
# MODEL_SOURCE_TYPE = "HUGGINGFACE"


# def load_model(where=Path("model_cache")):
#     """Load the digit-predictor TorchScript model from the cache."""
#     filename = where / CNN_MODEL_FILENAME
#     if not filename.exists():
#         raise FileNotFoundError(f"Model file not found at {filename}. Please run the copy/download command.")
        
#     device = torch.device("cpu")
#     try:
#         model = torch.jit.load(filename, map_location=device)
#         model.eval()
#         print(f"PyTorch CNN model '{filename}' loaded successfully on {device}.")
#         return model, device
#     except Exception as e:
#         print(f"Error loading TorchScript model: {e}")
#         raise


# def is_model_present(where=Path("model_cache")):
#     """Checks if the ML model is available in the cache."""
#     return (where / CNN_MODEL_FILENAME).exists()


# def copy_model_to_cache(where=Path("model_cache")):
#     """Copy the local model file to the model_cache directory."""
#     where.mkdir(exist_ok=True)
#     source_file_path = (Path(__file__).resolve().parent / CNN_MODEL_SOURCE_PATH).resolve()
#     destination_file_path = where / CNN_MODEL_FILENAME

#     print(f"Attempting to copy model from: {source_file_path}")
#     if not source_file_path.exists():
#         print(f"\tERROR: Source model file not found at '{source_file_path}'.")
#         return False
#     try:
#         shutil.copy(source_file_path, destination_file_path)
#         print(f"\tSuccessfully copied model to {destination_file_path}")
#     except Exception as e:
#         print(f"\tError copying file: {e}")
#         return False
#     return True


# def download_model_from_hf(where=Path("model_cache")):
#     """Download the model from Hugging Face Hub and place it in our cache."""
#     where.mkdir(exist_ok=True)
#     destination_file_path = where / CNN_MODEL_FILENAME
    
#     print(f"Downloading model from Hugging Face repo: {HF_REPO_ID}")
#     try:
#         # hf_hub_download downloads to its own cache, and returns the path
#         hf_cached_path = hf_hub_download(repo_id=HF_REPO_ID, filename=CNN_MODEL_FILENAME)
#         # We then copy it from the HF cache to our application's cache for consistency
#         shutil.copy(hf_cached_path, destination_file_path)
#         print(f"\tSuccessfully downloaded and cached model to {destination_file_path}")
#     except Exception as e:
#         print(f"\tError downloading from Hugging Face Hub: {e}")
#         return False
#     return True


# def ensure_model_available(where=Path("model_cache")):
#     """
#     Check if model is present in cache, and if not, get it based on MODEL_SOURCE_TYPE.
#     """
#     if is_model_present(where):
#         print("Model is already present in cache; no action required.")
#         return

#     print("Model not found in cache.")

#     if MODEL_SOURCE_TYPE == "HUGGINGFACE":
#         print("Source is Hugging Face. Will try to download.")
#         if download_model_from_hf(where):
#             print("Successfully downloaded model from Hugging Face.")
#         else:
#             print("Could not download the model from Hugging Face.")
    
#     elif MODEL_SOURCE_TYPE == "LOCAL":
#         print("Source is Local Path. Will try to copy.")
#         if copy_model_to_cache(where):
#             print("Successfully copied local model to cache.")
#         else:
#             print("Could not copy the local model.")
            
#     else:
#         print(f"ERROR: Invalid MODEL_SOURCE_TYPE: '{MODEL_SOURCE_TYPE}'. Must be 'HUGGINGFACE' or 'LOCAL'.")





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


# The filename for the model inside the cache AND on the Hub
CNN_MODEL_FILENAME = "mnist_emnist_blank_cnn_v1.onnx"

# --- Option A: Hugging Face Hub ---
HF_REPO_ID = "deepshah23/digit-blank-classifier-cnn" 

# --- Option B: Local File Path ---
# This path is relative to the location of this file (model_utils.py)
CNN_MODEL_SOURCE_PATH = "../../mnist_emnist_blank_cnn_v1.onnx"

# --- Configuration Switch ---
# Set this to "HUGGINGFACE" to download from the Hub, or "LOCAL" to copy from a local path.
MODEL_SOURCE_TYPE = "HUGGINGFACE"


def load_model(where=Path("model_cache")):
    """Load the digit-predictor TorchScript model from the cache."""
    filename = where / CNN_MODEL_FILENAME
    if not filename.exists():
        raise FileNotFoundError(f"Model file not found at {filename}. Please run the copy/download command.")
        
    try:
        session = ort.InferenceSession(
            str(filename),
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"]
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
    source_file_path = (Path(__file__).resolve().parent / CNN_MODEL_SOURCE_PATH).resolve()
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
        # hf_hub_download downloads to its own cache, and returns the path
        hf_cached_path = hf_hub_download(repo_id=HF_REPO_ID, filename=CNN_MODEL_FILENAME)
        # We then copy it from the HF cache to our application's cache for consistency
        shutil.copy(hf_cached_path, destination_file_path)
        print(f"\tSuccessfully downloaded and cached model to {destination_file_path}")
    except Exception as e:
        print(f"\tError downloading from Hugging Face Hub: {e}")
        return False
    return True


def ensure_model_available(where=Path("model_cache")):
    """
    Check if model is present in cache, and if not, get it based on MODEL_SOURCE_TYPE.
    """
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
        print(f"ERROR: Invalid MODEL_SOURCE_TYPE: '{MODEL_SOURCE_TYPE}'. Must be 'HUGGINGFACE' or 'LOCAL'.")