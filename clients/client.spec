# -*- mode: python -*-

block_cipher = None

# added paths to datas as per https://github.com/pyinstaller/pyinstaller/issues/4293#issuecomment-516265192
# hopefully fixes dll include issue on windows #325

a = Analysis(['client.py'],
             pathex=['../'],
             binaries=[],
             datas=[(HOMEPATH + '\\PyQt5\\Qt\\bin\*', 'PyQt5\\Qt\\bin')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

for icon in ['cross', 'delete', 'line', 'move', 'pan', 'pen', 'rectangle', 'redo', 'text', 'tick', 'undo', 'zoom', 'comment', 'comment_up', 'comment_down']:
  a.datas += [('{}.svg'.format(icon), 'icons/{}.svg'.format(icon), 'DATA')]

for cursor in ['box', 'cross', 'delete', 'line', 'pen', 'tick',]:
    a.datas += [('{}.png'.format(cursor), 'cursors/{}.png'.format(cursor), 'DATA')]

a.datas += [('../resources/version.py', '../resources/version.py', 'DATA')]

# to fix duplication of "version.py" warning
# from here https://stackoverflow.com/questions/19055089/pyinstaller-onefile-warning-pyconfig-h-when-importing-scipy-or-scipy-signal
for d in a.datas:
   if 'version.py' in d[0]:
       a.datas.remove(d)
       break


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
