"""Bundled FFmpeg import to a consistent stereo float sample format."""
from pathlib import Path
import subprocess
import tempfile
import numpy as np
import imageio_ffmpeg

AUDIO_FILTER='音乐文件 (*.wav *.mp3 *.flac *.m4a *.aac *.ogg *.opus *.wma *.aif *.aiff *.aifc *.ape *.alac *.mp4 *.webm);;所有文件 (*)'
MAX_IMPORT_SECONDS=15*60

def load_audio(path):
    path=Path(path)
    if not path.is_file(): raise ValueError('找不到要导入的音频文件')
    command=[imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-nostdin','-i',str(path),'-map','0:a:0','-vn','-t',str(MAX_IMPORT_SECONDS+.1),'-ac','2','-ar','48000','-f','f32le','pipe:1']
    with tempfile.TemporaryFile() as decoded:
        try:
            result=subprocess.run(command,stdout=decoded,stderr=subprocess.PIPE,timeout=180,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        except subprocess.TimeoutExpired as e: raise ValueError('音频解码超时，请尝试更短的文件') from e
        size=decoded.tell()
        if result.returncode or size<8: raise ValueError('无法读取此音频：文件可能已损坏、加密或没有音轨')
        if size>MAX_IMPORT_SECONDS*48000*8: raise ValueError('音频时长超过导入上限（15 分钟），请先截取练习片段')
        decoded.seek(0); audio=np.fromfile(decoded,dtype='<f4').reshape(-1,2)
    if not np.isfinite(audio).all(): raise ValueError('音频包含无效采样数据')
    return audio,48000
