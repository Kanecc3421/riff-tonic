import subprocess
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
import numpy as np
import imageio_ffmpeg
from media import load_audio

class MediaTests(unittest.TestCase):
    def test_real_common_format_decoding(self):
        with tempfile.TemporaryDirectory() as d:
            exe=imageio_ffmpeg.get_ffmpeg_exe()
            for suffix,codec in (('wav','pcm_s24le'),('mp3','libmp3lame'),('flac','flac'),('m4a','aac'),('aac','aac'),('ogg','libvorbis'),('aiff','pcm_s16be'),('wma','wmav2')):
                with self.subTest(suffix=suffix):
                    path=Path(d)/('测试音.'+suffix)
                    subprocess.run([exe,'-v','error','-f','lavfi','-i','sine=frequency=440:sample_rate=44100:duration=0.4','-c:a',codec,str(path)],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
                    a,rate=load_audio(path)
                    self.assertEqual(rate,48000); self.assertEqual(a.shape[1],2)
                    self.assertGreater(len(a),15000); self.assertGreater(float(np.abs(a).max()),.03)
                    f=np.fft.rfftfreq(len(a),1/rate)[np.argmax(np.abs(np.fft.rfft(a[:,0])))]
                    self.assertAlmostEqual(f,440,delta=4)
    def test_invalid_audio_has_actionable_error(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.mp3'; p.write_bytes(b'not music')
            with self.assertRaises(ValueError): load_audio(p)

    def test_oversized_duration_is_rejected_without_silent_truncation(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'long.wav'
            subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-f','lavfi','-i','sine=frequency=440:duration=2',str(path)],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
            with patch('media.MAX_IMPORT_SECONDS',1):
                with self.assertRaisesRegex(ValueError,'超过'): load_audio(path)

if __name__=='__main__': unittest.main()
