import unittest
from unittest.mock import patch
from output import output_devices,stream_options,refresh_output_devices

class OutputTests(unittest.TestCase):
    def test_prefers_wasapi_default_instead_of_legacy_mme(self):
        devices=[dict(name='Speaker MME',max_output_channels=2,hostapi=0),dict(name='Headphones',max_output_channels=2,hostapi=1)]
        apis=[dict(name='MME',default_output_device=0),dict(name='Windows WASAPI',default_output_device=1)]
        with patch('sounddevice.query_devices',return_value=devices),patch('sounddevice.query_hostapis',return_value=apis):
            self.assertEqual(output_devices(),([(1,'Headphones')],1))
    def test_stream_routes_to_explicit_output_with_low_latency(self):
        with patch('sounddevice.query_devices',return_value={'hostapi':0}),patch('sounddevice.query_hostapis',return_value={'name':'Windows WASAPI'}):
            options=stream_options(15)
            self.assertEqual(options['device'],15)
            self.assertEqual(options['latency'],'low')
            self.assertEqual(options['blocksize'],0)
            self.assertIsNotNone(options['extra_settings'])

    def test_rescan_reinitializes_backend_before_enumeration(self):
        calls=[]
        with patch('sounddevice._terminate',side_effect=lambda:calls.append('terminate')),patch('sounddevice._initialize',side_effect=lambda:calls.append('initialize')),patch('output.output_devices',side_effect=lambda:(calls.append('enumerate') or ([(5,'new')],5))):
            self.assertEqual(refresh_output_devices(),([(5,'new')],5))
        self.assertEqual(calls,['terminate','initialize','enumerate'])

if __name__=='__main__': unittest.main()
