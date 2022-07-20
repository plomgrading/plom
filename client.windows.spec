# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2022 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald

from pathlib import Path
# trickery from setup.py to define __version__ without import
with open(Path("plom") / "version.py") as f:
    exec(f.read())

block_cipher = None

a = Analysis(['plom/client/__main__.py'],
             pathex=['./'],
             binaries=[],
             datas=[
                 ('plom/client/*.svg', 'plom/client'),
                 ('plom/client/*.png', 'plom/client'),
                 ('plom/client/icons/*.svg', 'plom/client/icons'),
                 ('plom/client/cursors/*.png', 'plom/client/cursors'),
                 ('plom/client/help_img/nav*.png', 'plom/client/help_img'),
             ],
             hiddenimports=[],
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
          name='PlomClient-{}.exe'.format(__version__),
          debug=False,
          strip=False,
          onefile=True,
          upx=True,
          runtime_tmpdir=None,
          console=True )
