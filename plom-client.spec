# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['plom/scripts/plom-client'],
             pathex=['/home/andrew/Projects/MLP'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher
             )
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

for icon in ['cross', 'delete', 'line', 'move', 'pan', 'pen', 'rectangle', 'redo', 'text', 'tick', 'undo', 'zoom', 'comment', 'comment_up', 'comment_down', 'delta']:
  a.datas += [('{}.svg'.format(icon), 'plom/client/icons/{}.svg'.format(icon), 'DATA')]

for cursor in ['box', 'cross', 'delete', 'line', 'pen', 'tick',]:
  a.datas += [('{}.png'.format(cursor), 'plom/client/cursors/{}.png'.format(cursor), 'DATA')]

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          a.scripts,
          name='plom-client',
          debug=False,
          bootloader_ignore_signals=False,
          runtime_tmpdir=None,
          strip=False,
          upx=True,
          onefile=True,
          windowed=True,
          )
