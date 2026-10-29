import tempfile
import unittest
import numpy as np
from core import Mixer, PhraseStore

class CoreTests(unittest.TestCase):
    def test_wrap(self):
        m = Mixer(np.arange(10, dtype=np.float32)[:,None]/10, 10, 0.2, 0.5, click_volume=0)
        np.testing.assert_allclose(m.render(8)[:,0], [.2,.3,.4,.2,.3,.4,.2,.3])

    def test_click_phase_repeats_at_loop(self):
        m = Mixer(np.zeros((8000,2),np.float32), 8000, 0, .5, bpm=120, offset=.1)
        x=m.render(8000)
        np.testing.assert_array_equal(x[:4000], x[4000:])
        self.assertEqual(float(x[:800].max()),0)
        self.assertGreater(float(np.abs(x[800:1200]).max()), .1)

    def test_invalid_selection(self):
        with self.assertRaises(ValueError):
            Mixer(np.zeros((10,2)),10,.5,.5)

    def test_output_block_boundaries_do_not_change_timing(self):
        a=np.zeros((16000,2),np.float32)
        one=Mixer(a,8000,.1,1.3,bpm=97,offset=-.2).render(20000)
        m=Mixer(a,8000,.1,1.3,bpm=97,offset=-.2)
        split=np.concatenate([m.render(127),m.render(4096),m.render(15777)])
        np.testing.assert_array_equal(one,split)

    def test_mute_and_clipping(self):
        a=np.ones((8000,2),np.float32)
        silent=Mixer(a,8000,0,1,audio_volume=0,click_volume=0).render(100)
        self.assertEqual(float(np.abs(silent).max()),0)
        loud=Mixer(a,8000,0,1,audio_volume=1,click_volume=1).render(8000)
        self.assertLessEqual(float(np.abs(loud).max()),1)

    def test_save_load_preserves_audio_and_settings(self):
        with tempfile.TemporaryDirectory() as d:
            s=PhraseStore(d)
            a=np.array([[.25,-.5],[.1,.2]],np.float32)
            key=s.save(None,'乐句一',a,48000,{'start':0,'end':2/48000,'bpm':97,'offset':-.1})
            meta,b,rate=s.load(key)
            self.assertEqual(meta['name'],'乐句一')
            self.assertEqual(meta['settings']['bpm'],97)
            self.assertEqual(rate,48000)
            np.testing.assert_allclose(a,b,atol=1/32768)
            s.save(key,'改名',a,48000,meta['settings'])
            self.assertEqual(len(s.list()),1)

if __name__=='__main__': unittest.main()
