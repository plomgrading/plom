# -*- mode: python -*-

block_cipher = None

a = Analysis(['client.py'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

for icon in ['cross', 'crossDown', 'delete', 'line', 'move', 'pan', 'pen', 'rectangle', 'redo', 'text', 'tick', 'tickUp', 'undo', 'zoom', 'comment', 'comment_up', 'comment_down']:
  a.datas += [('{}.svg'.format(icon), 'icons/{}.svg'.format(icon), 'DATA')]

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='client',
          debug=False,
          strip=False,
          onefile=True,
          upx=True,
          runtime_tmpdir=None,
          console=True )
