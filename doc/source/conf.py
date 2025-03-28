# SPDX-License-Identifier: FSFAP
# Copyright (C) 2020-2025 Colin B. Macdonald
# Copyright (C) 2024 Aidan Murphy

# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
from django import setup as django_setup

# we need access to the `plom` module:
sys.path.insert(0, os.path.abspath("../../"))
# setup django env
os.environ["DJANGO_SETTINGS_MODULE"] = "plom_server.settings"
django_setup()


# -- Project information -----------------------------------------------------

project = "Plom"
copyright = "2018-2025 Andrew Rechnitzer, Colin B. Macdonald, et al"
author = "Andrew Rechnitzer, Colin B. Macdonald, and others"

from plom import __version__

release = __version__


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.doctest",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "myst_parser",
    "sphinxarg.ext",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

autoclass_content = "both"

# List of patterns, relative to source directory, that match files and
# directories to include and ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
# By default include everything in source directory.
include_patterns = ["**"]
exclude_patterns = []

# TODO: remove suppressions after issue[s] have been resolved:
suppress_warnings = [
    # https://github.com/sphinx-doc/sphinx/issues/4961
    "ref.python",
]

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

html_theme_options = {
    "display_version": True,
    "flyout_display": "hidden",
    "version_selector": True,
}

# -- Options for LaTeX output ------------------------------------------------

with open("_latex/preamble.tex", "r+") as f:
    PREAMBLE = f.read()

latex_elements = {"preamble": PREAMBLE}
latex_additional_files = ["_latex/common-unicode.sty"]
# -- Extension configuration -------------------------------------------------
