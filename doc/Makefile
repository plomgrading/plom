# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Aidan Murphy

# makefile for Sphinx documentation

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=-W -v
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = source
BUILDDIR      = build

MODULES       = plom_server plom
SPHINXAPI     = sphinx-apidoc
SPHINXAPIOPTS =-d 1 -e -f

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

# sphinx-apidoc
.PHONY: autodocs
autodocs: $(MODULES)
$(MODULES):
	@$(SPHINXAPI) -o "$(SOURCEDIR)/$@" "../$@" $(SPHINXAPIOPTS) $(O)


# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
