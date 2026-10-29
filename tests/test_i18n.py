import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile
import unittest
import numpy as np
from PySide6.QtWidgets import QApplication,QPushButton
from PySide6.QtWidgets import QMessageBox,QWidget
from unittest.mock import patch
from pathlib import Path
import json
from app import Window,configure_app
from PySide6.QtGui import QFontDatabase
from i18n import translate
from i18n import Label

class TranslationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])
        # Offscreen Qt does not discover Windows fonts automatically.
        for name in ('segoeui.ttf','msyh.ttc'):
            path=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'/name
            if path.exists(): QFontDatabase.addApplicationFont(str(path))
        configure_app(cls.app)
    def test_dynamic_text_keeps_user_names(self):
        self.assertEqual(translate('已保存 · 我的音量乐句','en'),'Saved · 我的音量乐句')
        self.assertEqual(translate('实际 90 BPM · 音高保持','en'),'Effective 90 BPM · pitch preserved')
        self.assertEqual(translate('声音输出：我的耳机','en'),'Output: 我的耳机')
        self.assertEqual(translate('不能删除整段录音，请保留一部分声音','en'),'Keep some audio; the entire recording cannot be deleted.')
    def test_language_switch_and_restore_without_changing_phrase_name(self):
        with tempfile.TemporaryDirectory() as d:
            w=Window(d); w.set_audio(np.zeros((8000,2),np.float32),8000); w.name.setText('我的乐句')
            w.set_language('en')
            self.assertEqual(w.play_button.text(),'▶ Loop from cursor')
            self.assertEqual(w.record_button.text(),'● Record system audio')
            self.assertEqual(w.name.placeholderText(),'Name this phrase')
            self.assertEqual(w.piano_decay.suffix(),' s')
            w.save(); self.assertTrue(w.status.text().startswith('Saved ·'))
            w.close(); v=Window(d)
            self.assertEqual(v.language,'en'); self.assertEqual(v.name.text(),'我的乐句')
            self.assertTrue(any(b.text()=='Import audio' for b in v.findChildren(QPushButton)))
            v.set_language('zh'); self.assertEqual(v.record_button.text(),'● 录电脑声音'); v.close()

    def test_english_static_labels_and_dynamic_record_button(self):
        with tempfile.TemporaryDirectory() as d:
            w=Window(d); w.set_language('en')
            for label in w.findChildren(Label):
                self.assertFalse(any('\u4e00'<=c<='\u9fff' for c in label.text()),label.text())
            w.record_button.setText('■ 结束录音')
            self.assertEqual(w.record_button.text(),'■ Finish recording')
            w.status.setText('录音中 1.2 秒 · 播放设备的内部声音（最长 10 分钟）')
            self.assertEqual(w.status.text(),'Recording 1.2 s · system output (10-minute maximum)')
            w.close()

    def test_delete_keeps_preferences_and_unnamed_status_is_english(self):
        with tempfile.TemporaryDirectory() as d:
            w=Window(d); w.set_audio(np.zeros((8000,2),np.float32),8000); w.set_language('en'); w.piano_decay.setValue(2.4)
            w.save(); self.assertEqual(w.status.text(),'Saved · Untitled phrase')
            w.library.setCurrentRow(0)
            with patch('app.QMessageBox.question',return_value=QMessageBox.StandardButton.Yes): w.delete()
            state=json.loads((Path(d)/'session.json').read_text(encoding='utf-8'))
            self.assertEqual(state['language'],'en'); self.assertEqual(state['piano_decay'],2.4); self.assertIsNone(state['last']); w.close()

    def test_english_parameter_labels_fit(self):
        with tempfile.TemporaryDirectory() as d:
            w=Window(d); w.set_language('en'); w.show(); self.app.processEvents()
            for group in w.findChildren(QWidget,'parameter'):
                for label in group.findChildren(Label):
                    self.assertLessEqual(label.fontMetrics().horizontalAdvance(label.text()),label.width(),label.text())
            w.close()

if __name__=='__main__': unittest.main()
