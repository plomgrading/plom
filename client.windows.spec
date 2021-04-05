# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path
# trickery from setup.py to define __version__ without import
with open(os.path.join("plom", "version.py")) as f:
    exec(f.read())

block_cipher = None

a = Analysis(['plom/scripts/client.py'],
             pathex=['./'],
             binaries=[],
             datas=[
                 (HOMEPATH + '\\PyQt5\\Qt\\bin\*', 'PyQt5\\Qt\\bin'),
                 ('plom/client/icons/*.svg', 'plom/client/icons'),
                 ('plom/client/cursors/*.png', 'plom/client/cursors'),
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
