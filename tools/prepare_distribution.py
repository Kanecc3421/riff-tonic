"""Curate source-only GitHub upload + local portable app + social materials."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage,QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

ROOT=Path(__file__).resolve().parents[1]

def copy_file(relative,destination):
    source=ROOT/relative; target=destination/relative
    target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(source,target)

def archive(path,files):
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for source,name in files: z.write(source,name)
    with zipfile.ZipFile(path) as z: assert z.testzip() is None

def main():
    qtapp=QApplication.instance() or QApplication([])
    publication=ROOT/'publication'; ready=publication/'github-ready'; ready.mkdir(parents=True,exist_ok=True)
    dest=ROOT/'deliverables'; dest.mkdir(exist_ok=True)
    image=QImage(1260,594,QImage.Format.Format_ARGB32); image.fill(Qt.GlobalColor.transparent)
    p=QPainter(image); QSvgRenderer(str(ROOT/'assets/branding/wordmark.svg')).render(p); p.end()
    image.save(str(publication/'images'/'wordmark.png'))
    shutil.copy2(ROOT/'assets/branding/wordmark.svg',publication/'images/wordmark.svg')
    shutil.copy2(ROOT/'assets/branding/riff-tonic-desktop.png',publication/'images/icon.png')
    files=['app.py','audio.py','core.py','output.py','playback.py','piano.py','media.py','i18n.py','branding.py',
           'requirements.txt','requirements.lock.txt','desktop.spec','.gitignore','launch.bat',
           'README.md','README.zh-CN.md','LICENSE','THIRD_PARTY_NOTICES.md',
           'assets/branding/riff-tonic-desktop.png','assets/branding/riff-tonic-desktop.ico','assets/branding/wordmark.svg',
           'publication/index.html','tools/render_publication.py','tools/build_windows.ps1','tools/prepare_distribution.py']
    for folder in ('tests','.github','publication/text','publication/images'):
        for file in (ROOT/folder).rglob('*'):
            if file.is_file() and '__pycache__' not in file.parts: files.append(file.relative_to(ROOT).as_posix())
    for relative in sorted(set(files)): copy_file(relative,ready)
    source_zip=dest/'RiffTonic-GitHub-source-v0.8.zip'
    archive(source_zip,[(ready/f,'RiffTonic-source/'+f) for f in sorted(set(files))])
    app=ROOT/'release-v08'/'RiffTonic'; assert (app/'RiffTonic.exe').is_file()
    for name in ('LICENSE','THIRD_PARTY_NOTICES.md','README.md','README.zh-CN.md','requirements.lock.txt'):
        shutil.copy2(ROOT/name,app/name)
    for relative in ('publication/text/upload-checklist.md','publication/images/github-hero.png','publication/images/app-en.png','publication/images/app-zh.png'):
        copy_file(relative,app)
    (app/'Start English.bat').write_text('@echo off\r\nstart "" "%~dp0RiffTonic.exe" --lang en\r\n',encoding='ascii',newline='')
    (app/'Start Chinese.bat').write_text('@echo off\r\nstart "" "%~dp0RiffTonic.exe" --lang zh\r\n',encoding='ascii',newline='')
    (app/'READ-ME-FIRST.txt').write_text('Riff Tonic 0.8 — local testing build\n\nRun RiffTonic.exe and keep all accompanying files.\nEnglish / Chinese can be selected in the left sidebar or with the launchers.\nYour phrases stay in %LOCALAPPDATA%\\RiffLoop\\phrases.\n\nThis local ZIP is not a claim that all public binary redistribution obligations are complete. See THIRD_PARTY_NOTICES.md and publication/text/upload-checklist.md in the source bundle before publishing binaries.\n',encoding='utf-8')
    site=ROOT/'.venv/Lib/site-packages'
    for file in site.glob('*.dist-info/**/*'):
        if file.is_file() and any(token in file.name.upper() for token in ('LICENSE','COPYING','NOTICE')):
            relative=file.relative_to(site); target=app/'licenses'/relative
            target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(file,target)
    windows_zip=dest/'RiffTonic-Windows-v0.8-local.zip'
    archive(windows_zip,[(f,'RiffTonic/'+f.relative_to(app).as_posix()) for f in app.rglob('*') if f.is_file()])
    social_zip=dest/'RiffTonic-Social-Kit-v0.8.zip'
    social_files=[publication/'index.html']
    for folder in ('images','text'): social_files.extend(f for f in (publication/folder).rglob('*') if f.is_file())
    archive(social_zip,[(f,'RiffTonic-Social-Kit/'+f.relative_to(publication).as_posix()) for f in social_files])
    sums=[]
    for file in (source_zip,windows_zip,social_zip):
        with file.open('rb') as content: digest=hashlib.file_digest(content,'sha256').hexdigest()
        sums.append(digest+'  '+file.name)
    (dest/'SHA256SUMS.txt').write_text('\n'.join(sums)+'\n',encoding='ascii')
    (dest/'MANIFEST.json').write_text(json.dumps({'version':'0.8','source_files':len(set(files)),'images':len(list((publication/'images').glob('*.png'))),'published':False,'archives':[x.name for x in (source_zip,windows_zip,social_zip)]},indent=2),encoding='utf-8')
    print('Prepared three verified ZIP archives and source-only GitHub directory.')

if __name__=='__main__': main()
