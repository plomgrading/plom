# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2022 Andrew Rechnitzer
# Copyright (C) 2020-2025 Colin B. Macdonald
# Copyright (C) 2024 Bryan Tanady

from pathlib import Path
from plom import __version__
import spellchecker

block_cipher = None
dict_path = spellchecker.__path__[0] + '/resources'

# Notes: https://github.com/Ousret/charset_normalizer/issues/253
a = Analysis(['plom/client/__main__.py'],
             pathex=['./'],
             binaries=[(dict_path, 'spellchecker/resources')],
             datas=[
                 ('plom/client/icons/*.svg', 'plom/client/icons'),
                 ('plom/client/icons/*.png', 'plom/client/icons'),
                 ('plom/client/cursors/*.png', 'plom/client/cursors'),
                 ('plom/client/ui_files/*.ui', 'plom/client/ui_files'),
                 ('plom/client/help_img/nav*.png', 'plom/client/help_img'),
                 ('plom/client/help_img/click_drag.gif', 'plom/client/help_img'),
                 ('plom/*keys.toml', 'plom'),
             ],
             hiddenimports=["charset_normalizer.md__mypyc"],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name=f'PlomClient-{__version__}-macOS-x86_64.bin',
          debug=False,
          strip=False,
          onefile=True,
          upx=True,
          runtime_tmpdir=None,
          console=False )

app = BUNDLE(exe,
             name=f'PlomClient-{__version__}-x86_64.app',
             icon=None,
             bundle_identifier='org.plomgrading.PlomClient',
             version=__version__)
