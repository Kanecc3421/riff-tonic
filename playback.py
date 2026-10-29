"""Pitch-preserving offline preparation; audio output remains sample-clock driven."""
import numpy as np

def stretch_loop(audio,rate,speed):
    if not np.isfinite(speed) or not .5<=speed<=2:
        raise ValueError('变速范围为 0.5–2.0 倍')
    if speed==1: return np.asarray(audio,dtype=np.float32)
    from pedalboard import time_stretch
    a=np.asarray(audio,dtype=np.float32)
    stretched=time_stretch(np.ascontiguousarray(a.T),rate,stretch_factor=speed,
                           pitch_shift_in_semitones=0,high_quality=True)
    result=np.asarray(stretched,dtype=np.float32).reshape(a.shape[1],-1).T
    target=max(1,round(len(a)/speed))
    if len(result)<target: result=np.pad(result,((0,target-len(result)),(0,0)))
    return np.ascontiguousarray(result[:target])
