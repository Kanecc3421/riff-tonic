import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
import numpy as np
from piano import PianoSynth,PianoKeyboard,PianoOutput,note_frequency
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QEvent

class PianoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app=QApplication.instance() or QApplication([])
    def test_c3_is_geometric_center_and_black_hit_has_priority(self):
        w=PianoKeyboard(); w.resize(840,116)
        rect=w.key_rect(48)
        self.assertAlmostEqual(rect.center().x(),w.width()/2,delta=1)
        black=w.key_rect(49)
        self.assertEqual(w.note_at(black.center()),49)
        self.assertAlmostEqual(note_frequency(48),130.8128,places=3)
    def test_synth_pitch_and_release(self):
        synth=PianoSynth(rate=16000); synth.note_on(48)
        y=synth.render(16000)[:,0]
        freq=np.fft.rfftfreq(len(y),1/16000)[np.argmax(np.abs(np.fft.rfft(y)))]
        self.assertAlmostEqual(freq,131,delta=2)
        self.assertGreater(np.max(np.abs(y)),.03)
        synth.note_off(48); tail=synth.render(32000)
        self.assertLess(np.max(np.abs(tail[-1000:])),.0001)
        self.assertTrue(np.isfinite(y).all())

    def test_focus_or_grab_loss_releases_note(self):
        for kind in (QEvent.Type.WindowDeactivate,QEvent.Type.UngrabMouse):
            w=PianoKeyboard(); released=[]; w.noteOff.connect(released.append)
            w.pan_anchor=(50,0); w.switch_note(48); self.app.sendEvent(w,QEvent(kind))
            self.assertIsNone(w.pressed); self.assertEqual(released,[48])
            self.assertIsNone(w.pan_anchor)

    def test_short_click_has_audible_minimum_gate(self):
        s=PianoSynth(rate=16000); s.note_on(48); s.note_off(48)
        y=s.render(3200)[:,0]
        self.assertGreater(float(np.max(np.abs(y[1000:1900]))),.04)
        s.render(32000); self.assertFalse(s.voices)

    def test_default_release_is_longer_and_duration_adjustable(self):
        s=PianoSynth(rate=16000); s.note_on(48); s.note_off(48)
        y=s.render(16000)[:,0]
        self.assertGreater(float(np.max(np.abs(y[5000:8000]))),.003)
        short=PianoSynth(rate=16000); short.release_seconds=.3; short.note_on(48); short.note_off(48)
        long=PianoSynth(rate=16000); long.release_seconds=2; long.note_on(48); long.note_off(48)
        a=short.render(16000)[:,0]; b=long.render(16000)[:,0]
        self.assertLess(np.max(np.abs(a[10000:])),.0001)
        self.assertGreater(np.max(np.abs(b[10000:])),.003)
        long.render(48000); self.assertFalse(long.voices)

    def test_keyboard_can_pan_to_c5_and_back_to_c2(self):
        w=PianoKeyboard(); w.resize(840,116)
        self.assertIn(72,w.whites)
        w.pan_to(72)
        self.assertTrue(w.rect().contains(w.key_rect(72).center().toPoint()))
        w.pan_to(36)
        self.assertTrue(w.rect().contains(w.key_rect(36).center().toPoint()))
        w.pan_to(48)
        self.assertAlmostEqual(w.key_rect(48).center().x(),w.width()/2,delta=1)

    def test_volume_controls_real_output_samples(self):
        loud=PianoOutput(); quiet=PianoOutput(); muted=PianoOutput()
        loud.gain=1; quiet.gain=.25; muted.gain=0
        for p in (loud,quiet,muted): p.synth.note_on(48)
        full=loud.render(2048); low=quiet.render(2048)
        np.testing.assert_allclose(low,full*.25,atol=1e-7)
        self.assertEqual(float(np.max(np.abs(muted.render(2048)))),0)

if __name__=='__main__': unittest.main()
