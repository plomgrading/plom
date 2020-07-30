# -*- mode: python ; coding: utf-8 -*-

import os
# trickery from setup.py to define __version__ without import
with open(os.path.join("plom", "version.py")) as f:
    exec(f.read())

block_cipher = None


a = Analysis(['plom/scripts/client.py'],
             pathex=['./'],
             binaries=[],
             datas=[],
             hiddenimports=['pkg_resources.py2_warn'], # https://github.com/pyinstaller/pyinstaller/issues/4672
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

for icon in ['cross', 'delete', 'line', 'move', 'pan', 'pen', 'rectangle_highlight', 'redo', 'text', 'tick', 'undo', 'zoom', 'comment', 'comment_up', 'comment_down', 'delta']:
   a.datas += [('{}.svg'.format(icon), 'plom/client/icons/{}.svg'.format(icon), 'DATA')]

for cursor in ['arrow', 'box', 'cross', 'delete', 'double_arrow', 'ellipse', 'highlighter', 'line', 'pen', 'question_mark', 'tick',]:
   a.datas += [('{}.png'.format(cursor), 'plom/client/cursors/{}.png'.format(cursor), 'DATA')]


exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='PlomClient-{}-linux.bin'.format(__version__),
          debug=False,
          strip=False,
          onefile=True,
          upx=True,
          runtime_tmpdir=None,
          console=True )
