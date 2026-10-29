import json
import os
from pathlib import Path
import uuid
import wave
import numpy as np

class SnapDrag:
    """One mouse gesture: capture once, hold briefly, then allow free movement."""
    def __init__(self,target,capture,escape):
        self.target=target; self.capture=capture; self.escape=escape
        self.snapped=False; self.disabled=False; self.previous=None; self.anchor=None

    def move(self,value):
        crossed=self.previous is not None and (self.previous-self.target)*(value-self.target)<0
        self.previous=value
        if self.disabled: return value
        if self.snapped:
            if abs(value-self.anchor)>self.escape:
                self.snapped=False; self.disabled=True; return value
            return self.target
        if abs(value-self.target)<=self.capture or crossed:
            self.snapped=True; self.anchor=value; return self.target
        return value

def edit_audio(audio,rate,start,end,mode):
    lo=round(start*rate); hi=round(end*rate)
    if mode not in ('keep','delete') or not 0<=lo<hi<=len(audio):
        raise ValueError('请先选择有效的音频片段')
    if mode=='keep': return audio[lo:hi].copy()
    if hi-lo==len(audio): raise ValueError('不能删除整段录音，请保留一部分声音')
    return np.concatenate([audio[:lo],audio[hi:]],axis=0)

def remap_time(value,start,end,mode):
    if mode=='keep': return value-start
    if value<=start: return value
    if value<end: return start
    return value-(end-start)

def atomic_json(path, data):
    path=Path(path)
    tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    os.replace(tmp,path)

class PhraseStore:
    def __init__(self, root):
        self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True)

    def list(self):
        result=[]
        for p in self.root.glob('*.json'):
            if p.name=='session.json': continue
            try:
                m=json.loads(p.read_text(encoding='utf-8'))
                if (self.root/m.get('audio',m['id']+'.wav')).exists(): result.append(m)
            except (ValueError,KeyError,OSError): pass
        return sorted(result,key=lambda x:x['name'])

    def save(self,key,name,audio,rate,settings,replace_audio=False):
        key=key or uuid.uuid4().hex
        meta_path=self.root/(key+'.json')
        old_file=key+'.wav'
        if meta_path.exists():
            old_file=json.loads(meta_path.read_text(encoding='utf-8')).get('audio',old_file)
        path=self.root/old_file
        write_audio=replace_audio or not path.exists()
        if replace_audio: path=self.root/(key+'.'+uuid.uuid4().hex+'.wav')
        if write_audio:
            tmp=path.with_suffix('.wav.tmp')
            pcm=(np.clip(audio,-1,1)*32767).astype('<i2')
            with wave.open(str(tmp),'wb') as w:
                w.setnchannels(pcm.shape[1]); w.setsampwidth(2); w.setframerate(rate); w.writeframes(pcm.tobytes())
            os.replace(tmp,path)
        try:
            atomic_json(meta_path,dict(id=key,name=name.strip() or '未命名乐句',settings=settings,audio=path.name))
        except Exception:
            if write_audio: path.unlink(missing_ok=True)
            raise
        if replace_audio and old_file!=path.name:
            try: (self.root/old_file).unlink(missing_ok=True)
            except OSError: pass
        return key

    def load(self,key):
        meta=json.loads((self.root/(key+'.json')).read_text(encoding='utf-8'))
        with wave.open(str(self.root/meta.get('audio',key+'.wav')),'rb') as w:
            rate=w.getframerate()
            a=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(np.float32).reshape(-1,w.getnchannels())/32767
        return meta,a,rate

    def delete(self,key):
        meta=self.root/(key+'.json')
        if meta.exists():
            data=json.loads(meta.read_text(encoding='utf-8'))
            (self.root/data.get('audio',key+'.wav')).unlink(missing_ok=True)
        meta.unlink(missing_ok=True)

class Mixer:
    def __init__(self,audio,rate,start,end,bpm=120,offset=0,beats=4,audio_volume=1,click_volume=.4,speed=1,prepared_audio=None):
        self.audio=np.asarray(audio,dtype=np.float32)
        if self.audio.ndim==1: self.audio=self.audio[:,None]
        self.rate=rate; self.start=max(0,round(start*rate)); self.end=min(len(audio),round(end*rate))
        if self.end<=self.start or bpm<=0: raise ValueError('请选择有效的循环范围')
        from playback import stretch_loop
        if not np.isfinite(speed) or not .5<=speed<=2: raise ValueError('变速范围为 0.5–2.0 倍')
        self.speed=speed
        self.output_audio=stretch_loop(self.audio[self.start:self.end],rate,speed) if prepared_audio is None else prepared_audio
        self.output_length=len(self.output_audio); self._output_pos=0
        self.source_step=(self.end-self.start)/self.output_length
        self.bpm=bpm; self.offset=offset; self.beats=beats
        self.audio_volume=audio_volume; self.click_volume=click_volume

    @property
    def pos(self): return self._output_pos*self.source_step
    @pos.setter
    def pos(self,value): self._output_pos=round(value/self.source_step)%self.output_length
    @property
    def source_time(self): return (self.start+self.pos)/self.rate
    def seek(self,seconds):
        source_pos=max(0,min(self.end-self.start-1,round(seconds*self.rate)-self.start))
        self._output_pos=min(self.output_length-1,max(0,round(source_pos/self.source_step)))

    def render(self,frames):
        output_ix=(np.arange(frames,dtype=np.int64)+self._output_pos)%self.output_length
        ix=self.start+output_ix*self.source_step
        out=self.output_audio[output_ix]
        if out.shape[1]==1: out=np.repeat(out,2,axis=1)
        else: out=out[:,:2].copy()
        out*=self.audio_volume
        beat=(ix/self.rate-self.offset)*self.bpm/60
        number=np.floor(beat+1e-9)
        elapsed=(beat-number)*60/(self.bpm*self.source_step)
        accent=(number.astype(np.int64)%self.beats)==0
        tone=np.sin(2*np.pi*np.where(accent,1500,1000)*elapsed)*np.exp(-elapsed*100)
        tone*=((elapsed<.045)&(ix/self.rate>=self.offset))*self.click_volume
        out+=tone[:,None]
        self._output_pos=(self._output_pos+frames)%self.output_length
        return np.clip(out,-1,1).astype(np.float32)
