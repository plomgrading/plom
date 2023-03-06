.. Plom documentation
   Copyright 2020-2023 Colin B. Macdonald
   Copyright 2020 Andrew Rechnitzer
   SPDX-License-Identifier: AGPL-3.0-or-later

Getting the source code
=======================

Plom is Free Software under the AGPLv3 license: you can help us make
it better!
Many `people already have <https://gitlab.com/plom/plom/-/blob/main/CONTRIBUTORS>`_.

You can get the source code by typing::

    git clone https://gitlab.com/plom/plom/


Plom Development hints
----------------------

So you wanna help?  Awesome.  This document will try to collect some
hints to get started.  See something wrong here?  Help us fix it!

Dev FAQ list
^^^^^^^^^^^^

How do I change the GUI?
........................

You need `qtcreator`.  If we want to modify the ``plom-manager`` tool,
we use `qtcreator` to edit the ``plom/client/ui_files/ui_manager.ui`` file.


I've changed the code, how do I install it?
...........................................

From the root of your git clone (i.e., the directory containing README.md, CONTRIBUTORS.md, etc), do::

    pip install .

Now ``plom-server --version`` should report something like `0.9.0.dev`.
