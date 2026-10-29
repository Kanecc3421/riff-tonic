import unittest
import numpy as np
from core import Mixer

class SpeedTests(unittest.TestCase):
    def test_pitch_preserved_slow_and_fast(self):
        rate=16000; t=np.arange(rate*2)/rate
        source=(.3*np.sin(2*np.pi*440*t))[:,None].astype(np.float32)
        for speed in (.5,1.5):
            m=Mixer(source,rate,0,2,speed=speed,click_volume=0)
            y=m.render(round(rate*2/speed))[:,0]
            middle=y[rate//4:-rate//4]
            f=np.fft.rfftfreq(len(middle),1/rate)[np.argmax(np.abs(np.fft.rfft(middle)))]
            self.assertAlmostEqual(f,440,delta=2)
            self.assertAlmostEqual(m.output_length,rate*2/speed,delta=2)

    def test_metronome_shares_speed_and_phase(self):
        for speed in (.5,1.5):
            m=Mixer(np.zeros((32000,2),np.float32),16000,0,2,bpm=120,offset=.25,speed=speed)
            y=np.max(np.abs(m.render(round(16000*1.8/speed))),axis=1)
            starts=np.flatnonzero((y[1:]>.02)&(y[:-1]<=.02))+1
            # Envelope has multiple zero crossings: inspect each known beat onset.
            for beat in (.25,.75,1.25,1.75):
                pos=round(beat/speed*16000)
                self.assertLess(float(y[max(0,pos-100):max(1,pos-30)].max()),.005)
                self.assertGreater(float(y[pos:pos+120].max()),.1)

    def test_seek_preserves_bounds_and_wraps(self):
        m=Mixer(np.zeros((16000,2),np.float32),8000,.25,1.75,speed=.5)
        m.seek(1.5)
        self.assertAlmostEqual(m.source_time,1.5,delta=.001)
        m.render(8000)
        self.assertAlmostEqual(m.source_time,.5,delta=.001)
        self.assertEqual((m.start,m.end),(2000,14000))

    def test_invalid_speed_rejected(self):
        for speed in (0,-1,float('nan'),3):
            with self.assertRaises(ValueError): Mixer(np.zeros((100,2)),100,0,1,speed=speed)

    def test_seek_end_at_double_speed_stays_near_end(self):
        m=Mixer(np.zeros((16000,2),np.float32),8000,.25,1.75,speed=2)
        m.seek(1.75)
        self.assertGreater(m.source_time,1.749)
        self.assertLess(m.source_time,1.75)

if __name__=='__main__': unittest.main()
