# Windows 10/11 ships the system ICU API used by Qt. Do not bundle a
# third-party ICU found on PATH: its versioned exports are incompatible.
from PyInstaller.utils.hooks import collect_data_files
from pathlib import PurePath
a = Analysis(['app.py'], pathex=[], binaries=[],
             datas=collect_data_files('soundcard')+collect_data_files('imageio_ffmpeg')+[('assets/branding/riff-tonic-desktop.png','assets/branding'),('assets/branding/wordmark.svg','assets/branding')], hiddenimports=[],
             hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[],
             noarchive=False, optimize=0)
a.binaries = [entry for entry in a.binaries
              if PurePath(entry[0]).name.lower() not in {'icuuc.dll','icudt78.dll'}]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='RiffTonic',icon='assets/branding/riff-tonic-desktop.ico',
          debug=False, bootloader_ignore_signals=False, strip=False,
          upx=False, console=False, disable_windowed_traceback=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='RiffTonic')
