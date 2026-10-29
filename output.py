"""Explicit shared Windows output routing for playback and reference piano."""
def output_devices():
    import sounddevice as sd
    devices=sd.query_devices(); apis=sd.query_hostapis()
    wasapi=next((i for i,a in enumerate(apis) if a['name']=='Windows WASAPI'),None)
    chosen=wasapi if wasapi is not None else devices[sd.default.device[1]]['hostapi']
    rows=[(i,d['name']) for i,d in enumerate(devices) if d['max_output_channels']>=2 and d['hostapi']==chosen]
    default=apis[chosen]['default_output_device']
    return rows,default

def stream_options(device=None):
    import sounddevice as sd
    options=dict(device=device,latency='low',blocksize=0)
    info=sd.query_devices(device,kind='output')
    if sd.query_hostapis(info['hostapi'])['name']=='Windows WASAPI':
        options['extra_settings']=sd.WasapiSettings(exclusive=False,auto_convert=True)
    return options

def refresh_output_devices():
    """Call only after this application's PortAudio streams have been closed."""
    import sounddevice as sd
    sd._terminate()
    sd._initialize()
    return output_devices()
