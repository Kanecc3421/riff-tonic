import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from PySide6.QtWidgets import QApplication
from app import Window,Timeline
from PySide6.QtCore import QPoint,Qt
from PySide6.QtTest import QTest

class UITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        # UI logic must also run on Windows CI machines with no audio endpoint.
        devices=patch('app.output_devices',return_value=([(0,'Test output')],0))
        devices.start(); self.addCleanup(devices.stop)
    def test_phrase_restore_and_switch(self):
        with tempfile.TemporaryDirectory() as d:
            w=Window(d)
            w.name.setText('测试 solo'); w.set_audio(np.zeros((48000,2),np.float32),48000)
            w.select(.2,.8); w.offset.setValue(.25); w.bpm.setValue(99); w.save(); key=w.key
            w.close()
            v=Window(d)
            self.assertEqual(v.key,key)
            self.assertEqual(v.name.text(),'测试 solo')
            self.assertEqual(v.start.value(),.2)
            self.assertEqual(v.end.value(),.8)
            self.assertEqual(v.bpm.value(),99)
            self.assertEqual(v.offset.value(),.25)
            self.assertIsNone(v.player.stream)
            v.new(); v.name.setText('第二句'); v.set_audio(np.ones((96000,2),np.float32)*.1,48000); v.save()
            v.open_phrase(key)
            self.assertEqual(len(v.audio),48000)
            self.assertEqual(v.end.value(),.8)
            v.resize(1100,750); v.show(); self.app.processEvents()
            v.grab().save(str(__import__('pathlib').Path(__file__).parents[1]/'preview.png'))
            v.close()

    def test_failed_save_keeps_recording_and_blocks_close(self):
        with tempfile.TemporaryDirectory() as d:
            w=Window(d); w.set_audio(np.zeros((48000,2),np.float32),48000)
            original=w.audio
            with patch.object(w.store,'save',side_effect=OSError('disk full')),patch.object(w,'error'):
                self.assertFalse(w.save())
                w.new(); self.assertIs(w.audio,original)
                from PySide6.QtGui import QCloseEvent
                event=QCloseEvent(); w.closeEvent(event); self.assertFalse(event.isAccepted())
            w.close()

    def test_volume_update_keeps_audio_clock(self):
        with tempfile.TemporaryDirectory() as d:
            w=Window(d); w.set_audio(np.zeros((48000,2),np.float32),48000)
            from core import Mixer
            m=Mixer(w.audio,48000,0,1); m.render(1234)
            w.player.mixer=m; w.player.stream=object()
            with patch.object(w,'play') as restart:
                w.av.setValue(50); w.cm.setChecked(True)
                restart.assert_not_called()
                self.assertEqual(m.pos,1234)
                self.assertEqual(m.audio_volume,.5)
                self.assertEqual(m.click_volume,0)
            w.player.stream=None; w.close()

    def test_empty_recording_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            w=Window(d)
            with self.assertRaises(ValueError): w.set_audio(np.zeros((0,2),np.float32),48000)
            w.close()

    def test_trim_delete_undo_and_reopen(self):
        with tempfile.TemporaryDirectory() as d:
            w=Window(d); a=np.arange(2000,dtype=np.float32).reshape(1000,2)/2000
            w.set_audio(a,1000); w.select(.2,.6); w.offset.setValue(.3); w.save(); key=w.key
            w.edit_selection('keep')
            np.testing.assert_array_equal(w.audio,a[200:600])
            self.assertAlmostEqual(w.offset.value(),.1)
            self.assertEqual(w.end.value(),.4)
            w.undo_edit(); np.testing.assert_array_equal(w.audio,a)
            self.assertEqual(w.start.value(),.2); self.assertEqual(w.end.value(),.6)
            self.assertAlmostEqual(w.offset.value(),.3)
            w.edit_selection('delete'); w.save(); w.close()
            v=Window(d); self.assertEqual(v.key,key)
            self.assertEqual(len(v.audio),600)
            np.testing.assert_allclose(v.audio,np.concatenate([a[:200],a[600:]]),atol=1/32767)
            self.assertEqual(v.offset.value(),.2); v.close()

    def test_drag_handles_and_compact_metronome(self):
        with tempfile.TemporaryDirectory() as d:
            w=Window(d); w.set_audio(np.zeros((10000,2),np.float32),1000); w.select(2,8)
            w.show(); self.app.processEvents(); wave=w.wave
            QTest.mousePress(wave,Qt.MouseButton.LeftButton,pos=QPoint(round(wave.px(2)),70))
            QTest.mouseMove(wave,QPoint(round(wave.px(3)),70))
            QTest.mouseRelease(wave,Qt.MouseButton.LeftButton,pos=QPoint(round(wave.px(3)),70))
            self.assertAlmostEqual(w.start.value(),3,delta=.02)
            self.assertEqual(w.end.value(),8)
            self.assertLessEqual(w.click.height(),60); w.close()

    def test_metronome_drag_snap_then_escape(self):
        with tempfile.TemporaryDirectory() as d:
            w=Window(d); w.set_audio(np.zeros((10000,2),np.float32),1000); w.select(1,8); w.offset.setValue(.2)
            w.show(); self.app.processEvents(); strip=w.click
            def point(t): return QPoint(round(strip.px(t)),20)
            QTest.mousePress(strip,Qt.MouseButton.LeftButton,pos=point(.2))
            QTest.mouseMove(strip,point(.98))
            self.assertAlmostEqual(w.offset.value(),1,places=3)
            QTest.mouseMove(strip,point(1.5))
            self.assertAlmostEqual(w.offset.value(),1.5,delta=.03)
            QTest.mouseMove(strip,point(1.01))
            self.assertNotEqual(w.offset.value(),1)
            QTest.mouseRelease(strip,Qt.MouseButton.LeftButton,pos=point(1.01)); w.close()

    def test_edits_preserve_exact_recording_boundary(self):
        with tempfile.TemporaryDirectory() as d:
            w=Window(d); a=np.zeros((2048,2),np.float32); a[-1]=.5
            w.set_audio(a,48000)
            self.assertEqual(round(w.end.value()*48000),2048)
            w.edit_selection('keep'); self.assertEqual(len(w.audio),2048)
            np.testing.assert_array_equal(w.audio[-1],[.5,.5]); w.close()

    def test_zoomed_offscreen_handle_can_be_dragged(self):
        with tempfile.TemporaryDirectory() as d:
            w=Window(d); w.set_audio(np.zeros((10000,2),np.float32),1000); w.select(2,8)
            w.show(); self.app.processEvents(); wave=w.wave; wave.left=4; wave.span=2
            QTest.mousePress(wave,Qt.MouseButton.LeftButton,pos=QPoint(6,70))
            QTest.mouseMove(wave,QPoint(round(wave.px(4.5)),70))
            QTest.mouseRelease(wave,Qt.MouseButton.LeftButton,pos=QPoint(round(wave.px(4.5)),70))
            self.assertAlmostEqual(w.start.value(),4.5,delta=.01); self.assertEqual(w.end.value(),8); w.close()

    def test_metronome_displays_only_one_bar_and_wraps_cursor(self):
        strip=Timeline(True); strip.resize(1000,48); strip.span=20; strip.duration=20
        strip.offset=1; strip.bpm=120; strip.beats=4
        self.assertEqual(strip.beat_times(),[1,1.5,2,2.5])
        strip.cursor=6.25
        self.assertEqual(strip.display_cursor(),2.25)
        strip.beats=8
        self.assertEqual(strip.beat_times(),[1,1.5,2,2.5,3,3.5,4,4.5])
        self.assertEqual(strip.display_cursor(),2.25)

    def test_parameter_fields_compact_and_aligned(self):
        with tempfile.TemporaryDirectory() as d:
            w=Window(d); w.show(); self.app.processEvents()
            for top,bottom in ((w.bpm,w.av),(w.beats,w.cv)):
                self.assertLessEqual(top.width(),120)
                self.assertEqual(top.mapTo(w,QPoint()).x(),bottom.mapTo(w,QPoint()).x())
            self.assertEqual(w.bpm.mapTo(w,QPoint()).y(),w.offset.mapTo(w,QPoint()).y())
            w.close()

    def test_audition_cursor_does_not_move_loop_and_speed_restores(self):
        with tempfile.TemporaryDirectory() as d:
            w=Window(d); w.set_audio(np.zeros((10000,2),np.float32),1000); w.select(1,8)
            w.seek_to(4.25)
            self.assertEqual((w.start.value(),w.end.value()),(1,8))
            self.assertEqual(w.audition,4.25)
            w.speed.setValue(.75); w.save(); w.close()
            v=Window(d); self.assertEqual(v.speed.value(),.75); self.assertEqual(v.audition,4.25)
            self.assertLessEqual(v.click.height(),34); v.close()

    def test_click_wave_seeks_without_changing_selection(self):
        with tempfile.TemporaryDirectory() as d:
            w=Window(d); w.set_audio(np.zeros((10000,2),np.float32),1000); w.select(1,8)
            w.show(); self.app.processEvents(); point=QPoint(round(w.wave.px(4)),70)
            QTest.mouseClick(w.wave,Qt.MouseButton.LeftButton,pos=point)
            self.assertAlmostEqual(w.audition,4,delta=.02)
            self.assertEqual((w.start.value(),w.end.value()),(1,8)); w.close()

    def test_rapid_speed_changes_keep_current_position_and_latest_request(self):
        import time
        from core import Mixer
        class Sink:
            def stop(self): pass
            def close(self): pass
        with tempfile.TemporaryDirectory() as d:
            w=Window(d); w.set_audio(np.zeros((32000,2),np.float32),16000); w.select(.25,1.75)
            w.player.mixer=Mixer(w.audio,16000,.25,1.75); w.player.mixer.seek(1.25); w.player.stream=Sink()
            def receive(mixer): w.player.mixer=mixer; w.player.stream=Sink()
            with patch.object(w.player,'play',side_effect=receive):
                w.speed.setValue(.75); w.speed.setValue(1.5)
                self.assertEqual(w.pending_play[3],1.25)
                deadline=time.monotonic()+8
                while w.prepare_worker is not None and time.monotonic()<deadline: QTest.qWait(20)
                self.assertIsNone(w.prepare_worker)
                self.assertIsNotNone(w.player.stream)
                self.assertEqual(w.player.mixer.speed,1.5)
                self.assertAlmostEqual(w.player.mixer.source_time,1.25,delta=.001)
            w.close()

    def test_stop_cancels_prepared_playback(self):
        import time
        with tempfile.TemporaryDirectory() as d:
            w=Window(d); w.set_audio(np.zeros((16000,2),np.float32),8000); w.speed.setValue(.75)
            with patch.object(w.player,'play') as output:
                w.play(); w.stop()
                deadline=time.monotonic()+8
                while w.prepare_worker is not None and time.monotonic()<deadline: QTest.qWait(20)
                self.assertIsNone(w.prepare_worker); self.assertIsNone(w.pending_play)
                output.assert_not_called()
            w.close()

    def test_play_buttons_have_distinct_start_positions(self):
        with tempfile.TemporaryDirectory() as d:
            w=Window(d); w.set_audio(np.zeros((10000,2),np.float32),1000); w.select(1,8); w.seek_to(4)
            starts=[]
            with patch.object(w.player,'play',side_effect=lambda m:starts.append(m.source_time)):
                w.play_from_current(); w.play_from_start()
            self.assertEqual(starts,[4,1])
            self.assertEqual((w.start.value(),w.end.value()),(1,8)); w.close()

    def test_current_button_uses_live_cursor_not_old_seek(self):
        from core import Mixer
        class Sink:
            def stop(self): pass
            def close(self): pass
        with tempfile.TemporaryDirectory() as d:
            w=Window(d); w.set_audio(np.zeros((10000,2),np.float32),1000); w.select(1,8); w.seek_to(2)
            w.player.mixer=Mixer(w.audio,1000,1,8); w.player.mixer.seek(5); w.player.stream=Sink()
            starts=[]
            with patch.object(w.player,'play',side_effect=lambda m:starts.append(m.source_time)): w.play_from_current()
            self.assertEqual(starts,[5]); w.close()

    def test_piano_duration_and_volume_controls_restore(self):
        with tempfile.TemporaryDirectory() as d:
            w=Window(d); w.piano_decay.setValue(2.4); w.piano_volume.setValue(125)
            self.assertAlmostEqual(w.piano_output.synth.release_seconds,2.4)
            self.assertAlmostEqual(w.piano_output.gain,1.25)
            w.close(); v=Window(d)
            self.assertEqual(v.piano_decay.value(),2.4)
            self.assertEqual(v.piano_volume.value(),125)
            self.assertAlmostEqual(v.piano_output.synth.release_seconds,2.4)
            v.close()

    def test_rescan_lists_new_bluetooth_without_restart(self):
        from PySide6.QtWidgets import QPushButton
        with tempfile.TemporaryDirectory() as d:
            w=Window(d); w.set_audio(np.zeros((10000,2),np.float32),1000); w.select(1,8); w.seek_to(4)
            old=w.outputs.currentText(); events=[]
            with patch.object(w.player,'stop',side_effect=lambda:events.append('stop')),patch.object(w.piano_output,'close',side_effect=lambda:events.append('piano')),patch('app.refresh_output_devices',side_effect=lambda:(events.append('refresh') or ([(21,old),(23,'New Bluetooth')],23))):
                w.refresh_devices()
            self.assertLess(events.index('stop'),events.index('refresh')); self.assertLess(events.index('piano'),events.index('refresh'))
            self.assertGreaterEqual(w.outputs.findText('New Bluetooth'),0)
            self.assertEqual(w.player.device,21)
            w.outputs.setCurrentIndex(w.outputs.findText('New Bluetooth')); self.assertEqual(w.player.device,23); self.assertEqual(w.piano_output.device,23)
            self.assertEqual(w.audition,4)
            self.assertFalse(any(b.text() in ('C2','C3 居中','C5') for b in w.findChildren(QPushButton)))
            w.close()

    def test_failed_rescan_discards_stale_device_ids(self):
        with tempfile.TemporaryDirectory() as d:
            w=Window(d)
            with patch('app.refresh_output_devices',return_value=([],-1)),patch.object(w,'error'):
                w.refresh_devices()
            self.assertIsNone(w.outputs.currentData()); self.assertIsNone(w.player.device)
            self.assertFalse(w.output_ready); w.close()

    def test_import_background_success_and_failure_preserve_library(self):
        import time,wave
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'new.wav'
            with wave.open(str(source),'wb') as f:
                f.setnchannels(1); f.setsampwidth(2); f.setframerate(8000)
                f.writeframes((np.ones(8000)*5000).astype('<i2').tobytes())
            w=Window(Path(d)/'library'); old=np.zeros((8000,2),np.float32)
            w.set_audio(old,8000); w.name.setText('original'); w.save(); old_key=w.key
            with patch('app.QFileDialog.getOpenFileName',return_value=(str(source),'')):
                w.import_audio()
            deadline=time.monotonic()+10
            while w.import_worker is not None and time.monotonic()<deadline: QTest.qWait(20)
            self.assertIsNone(w.import_worker); self.assertTrue(w.centralWidget().isEnabled())
            self.assertEqual(len(w.audio),48000); self.assertNotEqual(w.key,old_key)
            self.assertEqual(len(w.store.list()),2)
            current=w.audio; key=w.key
            bad=Path(d)/'bad.mp3'; bad.write_bytes(b'broken')
            with patch('app.QFileDialog.getOpenFileName',return_value=(str(bad),'')),patch.object(w,'error'):
                w.import_audio(); deadline=time.monotonic()+10
                while w.import_worker is not None and time.monotonic()<deadline: QTest.qWait(20)
            self.assertIsNone(w.import_worker); self.assertIs(w.audio,current); self.assertEqual(w.key,key)
            self.assertTrue(w.centralWidget().isEnabled()); w.close()

if __name__=='__main__': unittest.main()
