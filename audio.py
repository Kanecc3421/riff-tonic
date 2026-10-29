import threading
import numpy as np
from PySide6.QtCore import QThread, Signal

class Recorder(QThread):
    captured=Signal(object,int)
    failed=Signal(str)
    elapsed=Signal(float)

    def __init__(self):
        super().__init__(); self.stopping=threading.Event()

    def run(self):
        try:
            import soundcard as sc
            speaker=sc.default_speaker()
            if speaker is None: raise RuntimeError('未找到 Windows 播放设备')
            mic=sc.get_microphone(speaker.id,include_loopback=True)
            chunks=[]; count=0; rate=48000
            with mic.recorder(samplerate=rate,channels=2,blocksize=2048) as r:
                while not self.stopping.is_set() and count<rate*600:
                    data=r.record(numframes=2048)
                    chunks.append(data); count+=len(data); self.elapsed.emit(count/rate)
            if chunks: self.captured.emit(np.concatenate(chunks).astype(np.float32),rate)
        except Exception as e: self.failed.emit(str(e))

class Player:
    def __init__(self): self.stream=None; self.mixer=None; self.device=None
    def play(self,mixer):
        import sounddevice as sd
        self.stop(); self.mixer=mixer
        def callback(outdata,frames,time,status): outdata[:]=mixer.render(frames)
        from output import stream_options
        self.stream=sd.OutputStream(samplerate=mixer.rate,channels=2,dtype='float32',callback=callback,**stream_options(self.device))
        self.stream.start()
    def stop(self):
        if self.stream:
            self.stream.stop(); self.stream.close(); self.stream=None

class PrepareLoop(QThread):
    def __init__(self,key,audio,rate,speed):
        super().__init__(); self.key=key; self.audio=audio; self.rate=rate; self.speed=speed
        self.buffer=None; self.error=None
    def run(self):
        try:
            from playback import stretch_loop
            self.buffer=stretch_loop(self.audio,self.rate,self.speed)
        except Exception as e: self.error=str(e)

class ImportFile(QThread):
    def __init__(self,path):
        super().__init__(); self.path=path; self.audio=None; self.rate=None; self.error=None
    def run(self):
        try:
            from media import load_audio
            self.audio,self.rate=load_audio(self.path)
        except Exception as e: self.error=str(e)
