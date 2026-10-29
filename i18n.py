"""Small, explicit UI catalogue. User phrase and device names are never translated."""
import re
from PySide6.QtWidgets import QLabel as QtLabel,QPushButton as QtButton

EN={
 '我的乐句  /  PHRASES':'MY PHRASES', '声音输出 · 钢琴与录音共用':'OUTPUT · AUDIO + PIANO',
 '刷新设备':'Refresh devices','未找到输出，请刷新':'No output — refresh',
 '新建录音':'New recording','删除所选乐句':'Delete selected phrase',
 '把喜欢的乐句，练成自己的。':'Make that phrase your own.',
 '给这个乐句起个名字':'Name this phrase','保存乐句':'Save phrase','导入音乐':'Import audio',
 '● 录电脑声音':'● Record system audio','■ 结束录音':'■ Finish recording',
 '▶ 从当前位置循环':'▶ Loop from cursor','|◀ 从循环开头播放':'|◀ Play from loop start','■ 停止':'■ Stop',
 '速度 ×':'Speed ×','录音  /  单击定位试听，拖动游标移动；两端手柄调循环范围，拖动其他位置框选':'AUDIO · Click to seek, drag the playhead to audition. Drag handles or select a new loop.',
 '起点 / 秒':'Start / s','终点 / 秒':'End / s','显示全段':'Fit all','放大选段':'Zoom selection',
 '仅保留选区':'Keep selection','删除选区并拼接':'Delete & join','撤销剪辑 · Ctrl Z':'Undo edit · Ctrl Z',
 '节拍器 · 拖动对齐，靠近起点吸附，继续拖动脱开':'CLICK · Drag to align. Snap near loop start; keep dragging to release.',
 '每小节拍数':'Beats / bar','第一拍 / 秒':'1st beat / s','录音音量 %':'Audio %','节拍音量 %':'Click %',
 '录音静音':'Mute audio','节拍静音':'Mute click','钢琴找音 · C2–C5':'PIANO · C2–C5','试音':'Test tone','音量':'Volume','余音':'Release',
 '就绪 · 乐句保存在本机，设置自动记忆':'Ready · Phrases stay on this PC. Settings are remembered.',
 '准备录制新乐句':'Ready for a new phrase','正在准备变速片段 · 音高保持，界面仍可操作':'Preparing speed change · Pitch preserved. You can keep using the app.',
 '正在完成音频处理，完成后自动关闭':'Finishing audio processing, then closing…',
 '正在结束录音，请稍后关闭':'Finishing recording. Please close again in a moment.',
 '等待导入结束后关闭…':'Waiting for import to finish, then closing…','正在导入音乐…':'Importing audio…',
 '导入失败，原乐句保持不变':'Import failed. Your previous phrase is unchanged.',
 '设备已刷新，可选择新连接的蓝牙耳机':'Devices refreshed. You can select the newly connected headphones.',
 '操作未完成':'Could not complete the action','删除乐句':'Delete phrase','确定删除这个乐句及其录音？':'Delete this phrase and its recording?',
 '录音乐句':'Recorded phrase','未命名乐句':'Untitled phrase','已吸附':'Snapped','起':'IN','止':'OUT',
 '留住一段声音，慢慢练好它\n\n播放音乐，然后点击「录电脑声音」':'Catch a phrase. Make it yours.\n\nPlay some music, then click Record system audio.',
 '录音为空，请先播放音乐并录制片段':'The recording is empty. Play some music and capture a phrase.',
 '请选择有效的循环范围':'Select a valid loop range.',
 '请先刷新并选择可用的声音输出设备':'Refresh devices and select an available audio output first.',
 '未发现可用播放设备，请连接耳机或扬声器后再次刷新':'No output found. Connect headphones or speakers, then refresh.',
 '未找到 Windows 播放设备':'No Windows playback device was found.',
 '请先选择有效的音频片段':'Select a valid audio range first.',
 '不能删除整段录音，请保留一部分声音':'Keep some audio; the entire recording cannot be deleted.',
 '变速范围为 0.5–2.0 倍':'Playback speed must be between 0.5× and 2.0×.',
 '找不到要导入的音频文件':'The audio file could not be found.',
 '音频解码超时，请尝试更短的文件':'Audio decoding timed out. Try a shorter file.',
 '无法读取此音频：文件可能已损坏、加密或没有音轨':'Cannot read this audio. The file may be damaged, encrypted, or have no audio track.',
 '音频时长超过导入上限（15 分钟），请先截取练习片段':'The file exceeds the 15-minute import limit. Trim a practice segment first.',
 '音频包含无效采样数据':'The audio contains invalid samples.',
}

def translate(source,language='zh'):
    source=str(source)
    if language!='en': return source
    if source in EN: return EN[source]
    for before,after in (('已保存 · ','Saved · '),('已打开 · ','Opened · '),('声音输出：','Output: '),('钢琴 · ','PIANO · ')):
        if source.startswith(before): return after+source[len(before):]
    if source.startswith('钢琴输出错误：'): return 'Piano output error: '+translate(source[len('钢琴输出错误：'):],language)
    match=re.fullmatch(r'实际 (.+) BPM · 音高保持',source)
    if match: return f'Effective {match[1]} BPM · pitch preserved'
    match=re.fullmatch(r'循环播放 · (.+)× · 实际 (.+) BPM · 音高保持',source)
    if match: return f'Looping · {match[1]}× · effective {match[2]} BPM · pitch preserved'
    match=re.fullmatch(r'录音中 (.+) 秒 · 播放设备的内部声音（最长 10 分钟）',source)
    if match: return f'Recording {match[1]} s · system output (10-minute maximum)'
    if source.startswith('音乐文件 ('):
        return source.replace('音乐文件 (','Audio files (',1).replace(';;所有文件 (*)',';;All files (*)')
    return source

class Label(QtLabel):
    def __init__(self,text='',*args,**kwargs):
        super().__init__('',*args,**kwargs); self.source_text=str(text); self.retranslate()
    def setText(self,text): self.source_text=str(text); self.retranslate()
    def retranslate(self): QtLabel.setText(self,translate(self.source_text,getattr(self.window(),'language','zh')))

class Button(QtButton):
    def __init__(self,text='',*args,**kwargs):
        super().__init__('',*args,**kwargs); self.source_text=str(text); self.retranslate()
    def setText(self,text): self.source_text=str(text); self.retranslate()
    def retranslate(self): QtButton.setText(self,translate(self.source_text,getattr(self.window(),'language','zh')))
