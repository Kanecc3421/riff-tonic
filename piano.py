"""Small synthesized reference piano, independent of practice playback speed."""
import threading
import numpy as np
from PySide6.QtCore import Qt,QRectF,Signal,QEvent
from PySide6.QtGui import QColor,QPainter,QLinearGradient,QPen
from PySide6.QtWidgets import QWidget

def note_frequency(note): return 440*2**((note-69)/12)
def note_name(note): return ('C','C♯','D','D♯','E','F','F♯','G','G♯','A','A♯','B')[note%12]+str(note//12-1)

class PianoSynth:
    def __init__(self,rate=48000): self.rate=rate; self.voices={}; self.lock=threading.Lock(); self.release_seconds=1.2
    def note_on(self,note):
        with self.lock: self.voices[note]=[0,None]
    def note_off(self,note):
        with self.lock:
            if note in self.voices: self.voices[note][1]=max(self.voices[note][0],round(self.rate*.14))
    def release_all(self):
        with self.lock:
            for voice in self.voices.values(): voice[1]=voice[0]
    def render(self,frames):
        y=np.zeros(frames,np.float64)
        with self.lock:
            for note,(age,released) in list(self.voices.items()):
                t=(age+np.arange(frames))/self.rate; f=note_frequency(note)
                tone=np.sin(2*np.pi*f*t)
                for harmonic,gain in ((2,.28),(3,.12),(4,.06),(6,.025)):
                    tone+=gain*np.sin(2*np.pi*f*harmonic*t)*np.exp(-t*harmonic*.35)
                envelope=(1-np.exp(-t*250))*(.25+.75*np.exp(-t*1.8))
                if released is not None:
                    envelope*=np.exp(-np.maximum(0,(age+np.arange(frames)-released)/self.rate)*np.log(1000)/self.release_seconds)
                y+=.16*tone*envelope
                self.voices[note][0]+=frames
                if released is not None and age+frames-released>self.rate*self.release_seconds: del self.voices[note]
        return np.repeat(np.clip(y,-.9,.9).astype(np.float32)[:,None],2,axis=1)

class PianoOutput:
    def __init__(self): self.synth=PianoSynth(); self.stream=None; self.device=None; self.gain=.8; self.last_error=None; self.last_peak=0.
    def render(self,frames): return np.clip(self.synth.render(frames)*self.gain,-.95,.95)
    def note_on(self,note):
        if self.stream is None:
            import sounddevice as sd
            from output import stream_options
            def callback(out,frames,time,status):
                try:
                    out[:]=self.render(frames); self.last_peak=float(np.max(np.abs(out)))
                except Exception as e: out.fill(0); self.last_error=str(e)
            self.last_error=None
            self.stream=sd.OutputStream(samplerate=self.synth.rate,channels=2,dtype='float32',callback=callback,**stream_options(self.device))
            try: self.stream.start()
            except Exception: self.stream.close(); self.stream=None; raise
        self.synth.note_on(note)
    def note_off(self,note): self.synth.note_off(note)
    def close(self):
        if self.stream:
            self.stream.stop(); self.stream.close(); self.stream=None
        self.synth.voices.clear()

class PianoKeyboard(QWidget):
    noteOn=Signal(int)
    noteOff=Signal(int)
    panChanged=Signal(int)
    def __init__(self):
        super().__init__(); self.setFixedHeight(116); self.pressed=None
        self.whites=[n for n in range(36,73) if n%12 not in (1,3,6,8,10)]
        self.blacks=[n for n in range(36,73) if n%12 in (1,3,6,8,10)]
        self.pan=0.; self.pan_anchor=None
        self.setMouseTracking(True)
    def key_rect(self,note):
        width=self.width()/15
        if note in self.whites: return QRectF((self.whites.index(note)-self.pan)*width+1,2,width-2,self.height()-5)
        previous=max(n for n in self.whites if n<note)
        return QRectF((self.whites.index(previous)+1-self.pan)*width-width*.3,2,width*.6,self.height()*.6)
    def set_pan(self,value):
        self.switch_note(None); self.pan=max(0,min(7.,value/100)); self.panChanged.emit(round(self.pan*100)); self.update()
    def pan_to(self,note): self.set_pan((self.whites.index(note)-7)*100)
    def note_at(self,point):
        for note in self.blacks+self.whites:
            if self.key_rect(note).contains(point): return note
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        for note in self.whites+self.blacks:
            rect=self.key_rect(note); black=note in self.blacks; active=note==self.pressed
            gradient=QLinearGradient(rect.topLeft(),rect.bottomRight())
            colors=('#e5c5a0','#c99865') if active else ('#44423f','#181817') if black else ('#fffef8','#e6dfd2')
            gradient.setColorAt(0,QColor(colors[0])); gradient.setColorAt(.8,QColor(colors[0])); gradient.setColorAt(1,QColor(colors[1]))
            p.setPen(QPen(QColor('#24221f' if black else '#c8bdad'),1)); p.setBrush(gradient); p.drawRoundedRect(rect,4,4)
            p.setPen(QColor('#686057' if not black else '#e1dacf'))
            if not black:
                p.drawLine(int(rect.left()+4),int(rect.bottom()-5),int(rect.right()-4),int(rect.bottom()-5))
                p.drawText(QRectF(rect.left(),rect.bottom()-28,rect.width(),22),Qt.AlignmentFlag.AlignCenter,note_name(note))
            if note==48:
                p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor('#c28c58')); p.drawEllipse(rect.center().x()-2,rect.bottom()-32,4,4)
    def switch_note(self,note):
        if note==self.pressed: return
        if self.pressed is not None: self.noteOff.emit(self.pressed)
        self.pressed=note
        if note is not None: self.noteOn.emit(note)
        self.update()
    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton: self.switch_note(self.note_at(event.position()))
        elif event.button() in (Qt.MouseButton.MiddleButton,Qt.MouseButton.RightButton):
            self.pan_anchor=(event.position().x(),self.pan); self.setCursor(Qt.CursorShape.ClosedHandCursor)
    def mouseMoveEvent(self,event):
        if self.pan_anchor:
            x,pan=self.pan_anchor; self.set_pan((pan+(x-event.position().x())/(self.width()/15))*100)
        elif event.buttons()&Qt.MouseButton.LeftButton: self.switch_note(self.note_at(event.position()))
    def mouseReleaseEvent(self,event): self.switch_note(None); self.pan_anchor=None; self.unsetCursor()
    def wheelEvent(self,event):
        delta=event.angleDelta().x() or event.angleDelta().y()
        self.set_pan(self.pan*100-delta/120*100); event.accept()
    def hideEvent(self,event): self.switch_note(None); super().hideEvent(event)
    def event(self,event):
        if event.type() in (QEvent.Type.WindowDeactivate,QEvent.Type.UngrabMouse):
            self.switch_note(None); self.pan_anchor=None; self.unsetCursor()
        return super().event(event)
