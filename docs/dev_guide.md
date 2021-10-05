# Plom Development hints

So you wanna help?  Awesome.  This document will try to collect some hints to get started.  See something wrong here?  Help us fix it!

## FAQ list

### How do I change the GUI?

You need two tools `qtcreator` and `pyuic5`.

1. Use qtcreator to edit the `qtCreatorFiles/ui_foo.ui` file.
2. Command line: `pyuic5 ui_foo.ui > client/uiFiles/ui_foo.py`
