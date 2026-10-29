import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from core import edit_audio, remap_time, SnapDrag, PhraseStore

class EditTests(unittest.TestCase):
    def test_crop_and_delete_exact_samples(self):
        a=np.arange(20,dtype=np.float32).reshape(10,2)/20
        np.testing.assert_array_equal(edit_audio(a,10,.2,.6,'keep'),a[2:6])
        np.testing.assert_array_equal(edit_audio(a,10,.2,.6,'delete'),np.concatenate([a[:2],a[6:]]))
        self.assertAlmostEqual(remap_time(.8,.2,.6,'delete'),.4)
        self.assertAlmostEqual(remap_time(.5,.2,.6,'delete'),.2)
        self.assertAlmostEqual(remap_time(.1,.2,.6,'keep'),-.1)

    def test_invalid_edit_does_not_delete_everything(self):
        a=np.ones((10,2))
        for args in [(0,1,'delete'),(.5,.5,'keep'),(.7,.2,'delete')]:
            with self.assertRaises(ValueError): edit_audio(a,10,*args)

    def test_snap_can_be_broken_without_mouse_release(self):
        drag=SnapDrag(target=1,capture=.1,escape=.22)
        self.assertEqual(drag.move(.95),1)
        self.assertTrue(drag.snapped)
        self.assertEqual(drag.move(1.08),1)
        self.assertEqual(drag.move(1.23),1.23)
        self.assertFalse(drag.snapped)
        self.assertEqual(drag.move(1.01),1.01)
        self.assertEqual(SnapDrag(1,.1,.22).move(1.01),1)

    def test_snap_fast_crossing_catches_target(self):
        d=SnapDrag(1,.1,.22)
        self.assertEqual(d.move(.5),.5)
        self.assertEqual(d.move(1.3),1)
        self.assertEqual(d.move(1.31),1)
        self.assertEqual(d.move(1.55),1.55)

    def test_edit_revision_saved_and_old_format_readable(self):
        with tempfile.TemporaryDirectory() as d:
            s=PhraseStore(d); a=np.full((10,2),.25,np.float32)
            key=s.save(None,'乐句',a,10,{})
            s.save(key,'乐句',a[:4],10,{},replace_audio=True)
            self.assertEqual(len(s.load(key)[1]),4)
            self.assertEqual(len(s.list()),1)
            with patch('core.atomic_json',side_effect=OSError('disk full')):
                with self.assertRaises(OSError): s.save(key,'乐句',a[:2],10,{},replace_audio=True)
            self.assertEqual(len(s.load(key)[1]),4)
            s.delete(key); self.assertEqual(s.list(),[])

if __name__=='__main__': unittest.main()
