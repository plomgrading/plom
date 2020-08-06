# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path
# trickery from setup.py to define __version__ without import
with open(os.path.join("plom", "version.py")) as f:
    exec(f.read())

# copy-pasted form client.linux.spec: unfortunate duplication
CursorList = [x.name for x in Path("plom/client/cursors").glob("*.png")]
# filter out some unused ones
CursorList = [x for x in CursorList if not x.startswith("text")]
print("** Hacky cursor list: {}".format(", ".join(CursorList)))

IconList = [x.name for x in Path("plom/client/icons").glob("*.svg")]
# filter out some unused ones
IconList = [x for x in IconList if not x.startswith("manager")]
IconList = [x for x in IconList if not x in ("rectangle.svg", "zoom_in.svg", "zoom_out.svg")]
print("** Hacky icon list: {}".format(", ".join(IconList)))


block_cipher = None


a = Analysis(['plom/scripts/client.py'],
             pathex=['./'],
             binaries=[],
             datas=[(HOMEPATH + '\\PyQt5\\Qt\\bin\*', 'PyQt5\\Qt\\bin')],
             hiddenimports=['pkg_resources.py2_warn'], # https://github.com/pyinstaller/pyinstaller/issues/4672
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

for icon in IconList:
   a.datas += [(icon, 'plom/client/icons/{}'.format(icon), 'DATA')]

for cursor in CursorList:
   a.datas += [(cursor, 'plom/client/cursors/{}'.format(cursor), 'DATA')]


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
