import json
import os
from pathlib import Path
import sys
import numpy as np
from PySide6.QtCore import Qt, QTimer, Signal, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QShortcut, QKeySequence,QIcon
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QHBoxLayout,QVBoxLayout,QGridLayout,QPushButton,QLabel,QListWidget,QLineEdit,QDoubleSpinBox,QSpinBox,QSlider,QMessageBox,QSplitter,QCheckBox,QFileDialog,QComboBox,QScrollBar)
from core import Mixer,PhraseStore,atomic_json,edit_audio,remap_time,SnapDrag
from audio import Recorder,Player,PrepareLoop,ImportFile
from piano import PianoKeyboard,PianoOutput,note_name
from output import output_devices,refresh_output_devices
from i18n import Label as QLabel,Button,translate
from branding import BrandMark

class OutputCombo(QComboBox):
    refreshRequested=Signal()
    def showPopup(self):
        self.refreshRequested.emit(); super().showPopup()

class Timeline(QWidget):
    selected=Signal(float,float)
    offsetChanged=Signal(float)
    seekRequested=Signal(float)
    def __init__(self,click=False):
        super().__init__(); self.click=click; self.audio=None; self.duration=1.; self.a=0.; self.b=1.; self.left=0.; self.span=1.; self.anchor=None; self.cursor=None; self.offset=0.; self.bpm=120; self.beats=4
        self.drag_mode=None; self.snap=None
        self.language='zh'
        self.setMouseTracking(True)
        self.drag_moved=False
        if click: self.setFixedHeight(32)
        else: self.setMinimumHeight(180)
    def at(self,x): return max(0,min(self.duration,self.left+x/max(1,self.width())*self.span))
    def px(self,t): return (t-self.left)/self.span*self.width()
    def handle_x(self,t): return max(6,min(self.width()-6,self.px(t)))
    def beat_times(self):
        return [self.offset+n*60/self.bpm for n in range(self.beats)]
    def display_cursor(self):
        if self.cursor is None: return None
        if not self.click: return self.cursor
        if self.cursor<self.offset: return None
        return self.offset+(self.cursor-self.offset)%(self.beats*60/self.bpm)
    def paintEvent(self,e):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w=self.width(); h=self.height()
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor('#f5f1e9')); p.drawRoundedRect(self.rect(),12,12)
        if self.click:
            for n,t in enumerate(self.beat_times()):
                x=self.px(t); bw=60/self.bpm/self.span*w
                p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor('#f2b179' if n%self.beats==0 else '#e9e0d3'))
                p.drawRoundedRect(QRectF(x+2,5,max(1,bw-4),22),5,5)
                if bw>28:
                    p.setPen(QColor('#775c45')); p.drawText(QRectF(x,5,bw,22),Qt.AlignmentFlag.AlignCenter,str(n%self.beats+1))
            p.setPen(QPen(QColor('#cf8252'),2,Qt.PenStyle.DotLine)); x=int(self.px(self.a)); p.drawLine(x,0,x,h)
            if self.snap and self.snap.snapped:
                p.setPen(QColor('#a3592c')); p.drawText(max(4,min(w-65,x+7)),h-1,translate('已吸附',self.language))
        else:
            if self.audio is not None:
                p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor('#f2e3d0'))
                p.drawRect(QRectF(self.px(self.a),25,(self.b-self.a)/self.span*w,h-25))
            p.setPen(QColor('#b9ada0'))
            for i in range(9):
                x=int(i*w/8); p.drawText(x+5,18,f'{self.left+i*self.span/8:.2f}s')
            p.setPen(QPen(QColor('#e9e1d7'),1))
            for i in range(1,8): p.drawLine(int(i*w/8),25,int(i*w/8),h)
        if not self.click and self.audio is not None:
            p.setPen(QColor('#d79760')); rate=len(self.audio)/self.duration
            for x in range(w):
                lo=int((self.left+x/w*self.span)*rate); hi=min(len(self.audio),max(lo+1,int((self.left+(x+1)/w*self.span)*rate)))
                if lo>=len(self.audio): break
                v=float(np.max(np.abs(self.audio[lo:hi]))); p.drawLine(x,int(h/2-v*(h/2-25)),x,int(h/2+v*(h/2-25)))
            for t,label in ((self.a,'起'),(self.b,'止')):
                x=self.handle_x(t)
                p.setPen(QPen(QColor('#bb7c47'),2)); p.drawLine(int(x),25,int(x),h-5)
                p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor('#bb7c47')); p.drawRoundedRect(QRectF(x-6,h/2-20,12,40),5,5)
                p.setPen(QColor('#ffffff')); p.drawLine(int(x),int(h/2-8),int(x),int(h/2+8))
                p.setPen(QColor('#9e673b')); p.drawText(max(3,min(w-25,int(x)-5)),h-8,translate(label,self.language))
        elif not self.click:
            p.setPen(QColor('#9c8d7c')); p.drawText(self.rect(),Qt.AlignmentFlag.AlignCenter,translate('留住一段声音，慢慢练好它\n\n播放音乐，然后点击「录电脑声音」',self.language))
        cursor=self.display_cursor()
        if cursor is not None:
            p.setPen(QPen(QColor('#66564b'),2)); p.drawLine(int(self.px(cursor)),5,int(self.px(cursor)),h)
            if not self.click:
                x=self.px(cursor); p.setBrush(QColor('#66564b')); p.drawRoundedRect(QRectF(x-5,23,10,12),3,3)
    def mousePressEvent(self,e):
        if e.button()!=Qt.MouseButton.LeftButton: return
        self.anchor=self.at(e.position().x()); self.base=self.offset; self.press_x=e.position().x(); self.drag_moved=False
        if self.click:
            unit=self.span/max(1,self.width())
            self.snap=SnapDrag(self.a,unit*10,unit*22); self.snap.move(self.base)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        else:
            x=e.position().x()
            self.drag_mode='start' if abs(x-self.handle_x(self.a))<=12 else 'end' if abs(x-self.handle_x(self.b))<=12 else 'seek' if self.cursor is not None and abs(x-self.px(self.cursor))<=10 else 'select'
    def mouseMoveEvent(self,e):
        if self.anchor is None:
            edge=min(abs(e.position().x()-self.handle_x(self.a)),abs(e.position().x()-self.handle_x(self.b)))<=12
            self.setCursor(Qt.CursorShape.OpenHandCursor if self.click else Qt.CursorShape.SizeHorCursor if edge else Qt.CursorShape.CrossCursor)
            return
        t=self.at(e.position().x())
        self.drag_moved=self.drag_moved or abs(e.position().x()-self.press_x)>3
        if self.click:
            self.offsetChanged.emit(self.snap.move(self.base+t-self.anchor)); self.update()
        elif self.drag_mode=='seek': self.seekRequested.emit(t)
        elif self.drag_mode=='start': self.selected.emit(min(t,self.b-.001),self.b)
        elif self.drag_mode=='end': self.selected.emit(self.a,max(t,self.a+.001))
        elif self.drag_moved and abs(t-self.anchor)>.01: self.selected.emit(min(t,self.anchor),max(t,self.anchor))
    def mouseReleaseEvent(self,e):
        self.mouseMoveEvent(e)
        if not self.click and self.drag_mode=='select' and not self.drag_moved: self.seekRequested.emit(self.at(e.position().x()))
        self.anchor=None; self.snap=None; self.update()
    def wheelEvent(self,e):
        center=self.at(e.position().x()); fraction=e.position().x()/max(1,self.width())
        self.span=min(self.duration,max(min(.1,self.duration),self.span*(.8 if e.angleDelta().y()>0 else 1.25)))
        self.left=max(0,min(self.duration-self.span,center-self.span*fraction)); self.update()
        if hasattr(self,'peer'): self.peer.left=self.left; self.peer.span=self.span; self.peer.update()

class Window(QMainWindow):
    def __init__(self,root=None):
        super().__init__(); self.language='zh'; self.resize(1180,960)
        self.setWindowIcon(QIcon(str(Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'assets'/'branding'/'riff-tonic-desktop.png')))
        self.store=PhraseStore(root or Path(os.getenv('LOCALAPPDATA',str(Path.home())))/'RiffLoop'/'phrases')
        self.audio=None; self.rate=48000; self.key=None; self.recorder=None; self.player=Player(); self.loading=False
        self.audio_dirty=False; self.undo_stack=[]
        self.audition=0.; self.prepare_worker=None; self.pending_play=None; self.prepared_cache=None; self.close_pending=False
        self.import_worker=None; self.import_close_pending=False
        self.piano_output=PianoOutput()
        self.output_ready=True
        host=QWidget(); host.setObjectName('host'); self.setCentralWidget(host); outer=QHBoxLayout(host); outer.setContentsMargins(22,22,22,22); outer.setSpacing(22)
        side_widget=QWidget(); side_widget.setFixedWidth(210); side=QVBoxLayout(side_widget); side.setContentsMargins(0,0,0,0); side.setSpacing(12); outer.addWidget(side_widget)
        self.brand=BrandMark(); side.addWidget(self.brand)
        self.language_combo=QComboBox(); self.language_combo.addItem('简体中文','zh'); self.language_combo.addItem('English','en'); side.addWidget(self.language_combo)
        side.addWidget(QLabel('我的乐句  /  PHRASES'))
        self.library=QListWidget(); side.addWidget(self.library); self.library.itemClicked.connect(lambda i:self.open_phrase(i.data(Qt.ItemDataRole.UserRole)))
        side.addWidget(QLabel('声音输出 · 钢琴与录音共用'))
        self.outputs=OutputCombo(); side.addWidget(self.outputs)
        self.device_refresh_button=self.button(side,'刷新设备',self.refresh_devices)
        try:
            rows,default=output_devices()
            for index,name in rows: self.outputs.addItem(name,index)
            if not rows: self.outputs.addItem(self.t('未找到输出，请刷新'),None); self.output_ready=False
            self.outputs.setCurrentIndex(max(0,self.outputs.findData(default)))
        except Exception: self.outputs.addItem(self.t('未找到输出，请刷新'),None); self.output_ready=False
        try: saved_session=json.loads((self.store.root/'session.json').read_text(encoding='utf-8'))
        except (OSError,ValueError): saved_session={}
        saved_index=self.outputs.findText(saved_session.get('output_name',''))
        if saved_index>=0: self.outputs.setCurrentIndex(saved_index)
        self.player.device=self.piano_output.device=self.outputs.currentData()
        self.outputs.setToolTip(self.outputs.currentText())
        self.button(side,'新建录音',self.new); self.button(side,'删除所选乐句',self.delete)
        workspace=QWidget(); workspace.setObjectName('workspace'); outer.addWidget(workspace,1)
        main=QVBoxLayout(workspace); main.setContentsMargins(22,18,22,18); main.setSpacing(9)
        heading=QLabel('把喜欢的乐句，练成自己的。'); heading.setObjectName('heading'); main.addWidget(heading)
        top=QHBoxLayout(); main.addLayout(top); self.name=QLineEdit(); self.name.setPlaceholderText('给这个乐句起个名字'); top.addWidget(self.name)
        self.button(top,'保存乐句',self.save); self.button(top,'导入音乐',self.import_audio)
        transport=QHBoxLayout(); main.addLayout(transport)
        self.record_button=self.button(transport,'● 录电脑声音',self.record)
        self.record_button.setObjectName('accent')
        self.play_button=self.button(transport,'▶ 从当前位置循环',self.play_from_current)
        self.start_play_button=self.button(transport,'|◀ 从循环开头播放',self.play_from_start); self.button(transport,'■ 停止',self.stop)
        speed_row=QHBoxLayout(); speed_row.setSpacing(10); main.addLayout(speed_row)
        self.speed=self.parameter(speed_row,'速度 ×',.5,2,1,.05); self.speed.setDecimals(2)
        self.speed.setKeyboardTracking(False)
        for value in (.5,.75,1,1.25,1.5): self.button(speed_row,f'{value:g}×',lambda checked=False,v=value:self.speed.setValue(v))
        self.tempo_label=QLabel('实际 120 BPM · 音高保持'); speed_row.addWidget(self.tempo_label); speed_row.addStretch()
        main.addWidget(QLabel('录音  /  单击定位试听，拖动游标移动；两端手柄调循环范围，拖动其他位置框选'))
        self.wave=Timeline(); main.addWidget(self.wave,3)
        times=QHBoxLayout(); times.setSpacing(14); main.addLayout(times)
        self.start=self.parameter(times,'起点 / 秒',0,36000,0,.001); self.end=self.parameter(times,'终点 / 秒',0,36000,1,.001)
        times.addStretch()
        self.button(times,'显示全段',self.fit); self.button(times,'放大选段',self.zoom_selection)
        edits=QHBoxLayout(); main.addLayout(edits)
        self.button(edits,'仅保留选区',lambda:self.edit_selection('keep')); self.button(edits,'删除选区并拼接',lambda:self.edit_selection('delete'))
        self.undo_button=self.button(edits,'撤销剪辑 · Ctrl Z',self.undo_edit); self.undo_button.setEnabled(False)
        main.addWidget(QLabel('节拍器 · 拖动对齐，靠近起点吸附，继续拖动脱开'))
        self.click=Timeline(True); main.addWidget(self.click); self.wave.peer=self.click; self.click.peer=self.wave
        parameters=QGridLayout(); parameters.setHorizontalSpacing(20); parameters.setVerticalSpacing(8); main.addLayout(parameters)
        cells=[]
        for row in range(2):
            for col in range(3):
                cell=QHBoxLayout(); cell.setContentsMargins(0,0,0,0); cell.setSpacing(0); parameters.addLayout(cell,row,col); cells.append(cell)
        parameters.setColumnStretch(3,1)
        self.bpm=self.parameter(cells[0],'BPM',20,400,120,1)
        self.beats=self.parameter(cells[1],'每小节拍数',1,12,4,1)
        self.offset=self.parameter(cells[2],'第一拍 / 秒',-36000,36000,0,.001)
        self.av=self.parameter(cells[3],'录音音量 %',0,100,80,1)
        self.cv=self.parameter(cells[4],'节拍音量 %',0,100,35,1)
        self.am=QCheckBox('录音静音'); self.cm=QCheckBox('节拍静音'); cells[5].addWidget(self.am); cells[5].addSpacing(14); cells[5].addWidget(self.cm)
        piano_header=QHBoxLayout(); main.addLayout(piano_header)
        self.piano_label=QLabel('钢琴找音 · C2–C5'); piano_header.addWidget(self.piano_label)
        self.button(piano_header,'试音',self.piano_test)
        piano_header.addWidget(QLabel('音量')); self.piano_volume=QSpinBox(); self.piano_volume.setFixedSize(78,32); self.piano_volume.setRange(0,150); self.piano_volume.setSuffix('%'); self.piano_volume.setValue(int(saved_session.get('piano_volume',80))); piano_header.addWidget(self.piano_volume)
        self.piano_output.gain=self.piano_volume.value()/100
        piano_header.addWidget(QLabel('余音')); self.piano_decay=QDoubleSpinBox(); self.piano_decay.setFixedSize(82,32); self.piano_decay.setRange(.3,3); self.piano_decay.setDecimals(1); self.piano_decay.setSingleStep(.1); self.piano_decay.setSuffix(' 秒'); self.piano_decay.setValue(float(saved_session.get('piano_decay',1.2))); piano_header.addWidget(self.piano_decay)
        self.piano_output.synth.release_seconds=self.piano_decay.value()
        piano_header.addStretch()
        self.piano=PianoKeyboard(); main.addWidget(self.piano)
        self.piano_scroll=QScrollBar(Qt.Orientation.Horizontal); self.piano_scroll.setRange(0,700); self.piano_scroll.setPageStep(1500); self.piano_scroll.setSingleStep(100); self.piano_scroll.setFixedHeight(12); main.addWidget(self.piano_scroll)
        self.piano_scroll.valueChanged.connect(self.piano.set_pan)
        self.piano.panChanged.connect(self.piano_scroll.setValue)
        self.piano.noteOn.connect(self.piano_note_on); self.piano.noteOff.connect(self.piano_output.note_off)
        self.status=QLabel('就绪 · 乐句保存在本机，设置自动记忆'); main.addWidget(self.status)
        self.wave.selected.connect(self.select); self.wave.seekRequested.connect(self.seek_to); self.click.offsetChanged.connect(self.offset.setValue)
        self.outputs.currentIndexChanged.connect(self.output_changed); self.piano_volume.valueChanged.connect(self.piano_volume_changed)
        self.outputs.refreshRequested.connect(self.refresh_devices)
        self.piano_decay.valueChanged.connect(self.piano_decay_changed)
        self.speed.valueChanged.connect(self.changed)
        for control in (self.start,self.end,self.bpm,self.beats,self.offset): control.valueChanged.connect(self.changed)
        for control in (self.av,self.cv): control.valueChanged.connect(self.gains_changed)
        for control in (self.am,self.cm): control.toggled.connect(self.gains_changed)
        self.name.textEdited.connect(self.schedule_save)
        self.autosave=QTimer(self); self.autosave.setSingleShot(True); self.autosave.timeout.connect(self.save)
        self.clock=QTimer(self); self.clock.timeout.connect(self.tick); self.clock.start(50)
        QShortcut(QKeySequence('Space'),self,activated=self.toggle)
        QShortcut(QKeySequence('Ctrl+Z'),self,activated=self.undo_edit)
        self.language_combo.currentIndexChanged.connect(lambda:self.set_language(self.language_combo.currentData()))
        self.set_language(saved_session.get('language','zh'),persist=False)
        self.refresh()
        try:
            session=json.loads((self.store.root/'session.json').read_text(encoding='utf-8'))
            if session.get('last'): self.open_phrase(session['last'])
        except (OSError,ValueError,KeyError): pass
    def button(self,layout,text,fn):
        b=Button(text); b.clicked.connect(fn); layout.addWidget(b); return b
    def t(self,text): return translate(text,self.language)
    def set_language(self,language,persist=True):
        self.language=language if language in ('zh','en') else 'zh'
        self.language_combo.blockSignals(True); self.language_combo.setCurrentIndex(self.language_combo.findData(self.language)); self.language_combo.blockSignals(False)
        for widget in self.findChildren(QWidget):
            if isinstance(widget,(QLabel,Button)): widget.retranslate()
            elif isinstance(widget,QCheckBox):
                source=widget.property('source_text') or widget.text(); widget.setProperty('source_text',source); widget.setText(self.t(source))
        self.name.setPlaceholderText(self.t('给这个乐句起个名字'))
        self.piano_decay.setSuffix(' s' if self.language=='en' else ' 秒')
        self.wave.language=self.click.language=self.language; self.wave.update(); self.click.update()
        if self.outputs.currentData() is None:
            self.outputs.setItemText(self.outputs.currentIndex(),self.t('未找到输出，请刷新'))
        self.setWindowTitle('Riff Tonic 0.8 · '+('Phrase practice' if self.language=='en' else '乐句练习'))
        if persist:
            try: self.save_session()
            except OSError as e: self.error(e)
    def number(self,layout,label,lo,hi,value,step):
        layout.addWidget(QLabel(label)); s=QDoubleSpinBox(); s.setDecimals(6 if step<1 else 0); s.setRange(lo,hi); s.setSingleStep(step); s.setValue(value); layout.addWidget(s); return s
    def parameter(self,layout,label,lo,hi,value,step):
        group=QWidget(); group.setFixedWidth(196); group.setObjectName('parameter')
        row=QHBoxLayout(group); row.setContentsMargins(0,0,0,0); row.setSpacing(8)
        text=QLabel(label); text.setFixedWidth(76); row.addWidget(text)
        value_box=QDoubleSpinBox(); value_box.setDecimals(6 if step<1 else 0)
        value_box.setRange(lo,hi); value_box.setSingleStep(step); value_box.setValue(value)
        value_box.setFixedSize(112,32); row.addWidget(value_box); layout.addWidget(group)
        return value_box
    def settings(self): return {k:getattr(self,k).value() for k in ('start','end','bpm','beats','offset','av','cv','speed')}|{'am':self.am.isChecked(),'cm':self.cm.isChecked(),'audition':self.audition}
    def refresh(self):
        self.library.clear()
        for m in self.store.list():
            self.library.addItem(m['name']); self.library.item(self.library.count()-1).setData(Qt.ItemDataRole.UserRole,m['id'])
    def save(self):
        if self.audio is None or self.loading: return True
        try:
            self.key=self.store.save(self.key,self.name.text() or self.t('未命名乐句'),self.audio,self.rate,self.settings(),replace_audio=self.audio_dirty)
            self.audio_dirty=False
            self.save_session(); self.refresh(); self.status.setText('已保存 · '+(self.name.text() or self.t('未命名乐句'))); return True
        except Exception as e: self.error(e); return False
    def schedule_save(self,*args):
        if not self.loading and self.audio is not None: self.autosave.start(700)
    def changed(self,*args):
        if self.audio is not None:
            self.audition=max(self.start.value(),min(self.audition,max(self.start.value(),self.end.value()-1/self.rate)))
            if not self.player.stream: self.wave.cursor=self.audition
        self.wave.a=self.click.a=self.start.value(); self.wave.b=self.click.b=self.end.value()
        self.click.bpm=self.bpm.value(); self.click.beats=int(self.beats.value()); self.click.offset=self.offset.value()
        self.tempo_label.setText(f'实际 {self.bpm.value()*self.speed.value():g} BPM · 音高保持')
        self.wave.update(); self.click.update(); self.schedule_save()
        if not self.loading and (self.player.stream or self.pending_play): self.play(preserve=True)
    def seek_to(self,seconds):
        if self.audio is None: return
        self.audition=max(self.start.value(),min(seconds,max(self.start.value(),self.end.value()-1/self.rate)))
        if self.player.stream and self.player.mixer: self.player.mixer.seek(self.audition)
        if self.pending_play:
            key,source,kwargs,_=self.pending_play; self.pending_play=(key,source,kwargs,self.audition)
        self.wave.cursor=self.audition; self.wave.update(); self.schedule_save()
    def piano_note_on(self,note):
        if not self.output_ready: self.error('请先刷新并选择可用的声音输出设备'); return
        try:
            self.piano_output.note_on(note); self.piano_label.setText(f'钢琴 · {note_name(note)}')
        except Exception as e: self.piano.switch_note(None); self.error(e)
    def piano_test(self):
        self.piano_note_on(60)
        QTimer.singleShot(550,lambda:self.piano_output.note_off(60))
    def piano_volume_changed(self,value):
        self.piano_output.gain=value/100
        try: self.save_session()
        except OSError as e: self.error(e)
    def piano_decay_changed(self,value):
        self.piano_output.synth.release_seconds=value
        try: self.save_session()
        except OSError as e: self.error(e)
    def save_session(self):
        atomic_json(self.store.root/'session.json',{'last':self.key,'output_name':self.outputs.currentText(),'piano_volume':self.piano_volume.value(),'piano_decay':self.piano_decay.value(),'language':self.language})
    def output_changed(self,*args):
        resume=bool(self.player.stream or self.pending_play); self.stop(); self.piano.switch_note(None); self.piano_output.close()
        self.player.device=self.piano_output.device=self.outputs.currentData()
        self.outputs.setToolTip(self.outputs.currentText()); self.status.setText('声音输出：'+self.outputs.currentText())
        try: self.save_session()
        except OSError as e: self.error(e)
        if resume: self.play()
    def refresh_devices(self,*args):
        old_name=self.outputs.currentText(); resume=bool(self.player.stream or self.pending_play)
        self.stop(); self.piano.switch_note(None); self.piano_output.close()
        try:
            rows,default=refresh_output_devices()
            if not rows: raise RuntimeError('未发现可用播放设备，请连接耳机或扬声器后再次刷新')
            self.outputs.blockSignals(True); self.outputs.clear()
            for index,name in rows: self.outputs.addItem(name,index)
            current=self.outputs.findText(old_name)
            if current<0: current=max(0,self.outputs.findData(default))
            self.outputs.setCurrentIndex(current); self.outputs.blockSignals(False)
            self.player.device=self.piano_output.device=self.outputs.currentData()
            self.output_ready=True
            self.outputs.setToolTip(self.outputs.currentText()); self.save_session()
            self.status.setText('设备已刷新，可选择新连接的蓝牙耳机')
            if resume: self.play()
        except Exception as e:
            self.outputs.blockSignals(True); self.outputs.clear(); self.outputs.addItem(self.t('未找到输出，请刷新'),None); self.outputs.blockSignals(False)
            self.player.device=self.piano_output.device=None; self.output_ready=False; self.error(e)
    def gains_changed(self,*args):
        if self.player.mixer:
            self.player.mixer.audio_volume=0 if self.am.isChecked() else self.av.value()/100
            self.player.mixer.click_volume=0 if self.cm.isChecked() else self.cv.value()/100
        self.schedule_save()
    def select(self,a,b):
        self.start.blockSignals(True); self.end.blockSignals(True)
        self.start.setValue(a); self.end.setValue(b)
        self.start.blockSignals(False); self.end.blockSignals(False); self.changed()

    def edit_selection(self,mode):
        if self.audio is None or (self.recorder and self.recorder.isRunning()): return
        try:
            lo=round(self.start.value()*self.rate)/self.rate; hi=round(self.end.value()*self.rate)/self.rate
            edited=edit_audio(self.audio,self.rate,lo,hi,mode)
            self.undo_stack.append((self.audio,self.settings())); self.undo_stack=self.undo_stack[-10:]
            self.stop(); self.loading=True
            offset=remap_time(self.offset.value(),lo,hi,mode)
            audition=remap_time(self.audition,lo,hi,mode)
            self.set_audio(edited,self.rate); self.offset.setValue(offset); self.audition=audition
            self.loading=False; self.audio_dirty=True; self.undo_button.setEnabled(True); self.changed(); self.save()
        except Exception as e: self.loading=False; self.error(e)

    def undo_edit(self):
        if not self.undo_stack or (self.recorder and self.recorder.isRunning()): return
        audio,settings=self.undo_stack.pop(); self.stop(); self.loading=True; self.set_audio(audio,self.rate)
        for k,v in settings.items():
            if k=='audition': self.audition=v; continue
            control=getattr(self,k)
            if isinstance(control,QCheckBox): control.setChecked(v)
            else: control.setValue(v)
        self.loading=False; self.audio_dirty=True; self.undo_button.setEnabled(bool(self.undo_stack)); self.changed(); self.save()
    def set_audio(self,a,rate):
        if rate<=0 or len(a)==0: raise ValueError('录音为空，请先播放音乐并录制片段')
        self.audio=a; self.rate=rate; duration=len(a)/rate
        self.audition=0.; self.prepared_cache=None
        self.wave.audio=a; self.wave.duration=self.click.duration=duration
        self.start.setMaximum(max(0,duration-1/rate)); self.end.setMaximum(duration)
        self.start.setValue(0); self.end.setValue(duration); self.fit(); self.changed()
    def fit(self):
        for v in (self.wave,self.click): v.left=0; v.span=v.duration; v.update()
    def zoom_selection(self):
        for v in (self.wave,self.click): v.left=self.start.value(); v.span=max(.1,self.end.value()-self.start.value()); v.update()
    def new(self):
        if self.recorder and self.recorder.isRunning(): return False
        if not self.save(): return False
        self.stop(); self.loading=True; self.key=None; self.audio=None; self.audition=0.; self.prepared_cache=None; self.audio_dirty=False; self.undo_stack.clear(); self.undo_button.setEnabled(False); self.wave.audio=None; self.wave.cursor=None; self.name.setText(''); self.offset.setValue(0); self.speed.setValue(1); self.loading=False; self.wave.update(); self.status.setText('准备录制新乐句'); return True
    def open_phrase(self,key):
        if self.recorder and self.recorder.isRunning(): return
        if not self.save(): return
        self.stop()
        try:
            meta,a,rate=self.store.load(key); self.loading=True; self.audio_dirty=False; self.undo_stack.clear(); self.undo_button.setEnabled(False); self.key=key; self.name.setText(meta['name']); self.set_audio(a,rate); self.speed.setValue(1)
            for k,v in meta['settings'].items():
                if k=='audition': self.audition=float(v); continue
                c=getattr(self,k,None)
                if isinstance(c,QCheckBox): c.setChecked(v)
                elif isinstance(c,QDoubleSpinBox): c.setValue(v)
            self.loading=False; self.changed(); self.status.setText('已打开 · '+meta['name'])
        except Exception as e: self.loading=False; self.error(e)
    def record(self):
        if self.recorder and self.recorder.isRunning():
            self.recorder.stopping.set(); self.record_button.setEnabled(False); return
        if not self.new(): return
        self.recorder=Recorder(); self.recorder.captured.connect(self.recorded); self.recorder.failed.connect(self.error); self.recorder.elapsed.connect(lambda s:self.status.setText(f'录音中 {s:.1f} 秒 · 播放设备的内部声音（最长 10 分钟）')); self.recorder.finished.connect(self.record_finished); self.recorder.start(); self.record_button.setText('■ 结束录音')
    def record_finished(self): self.record_button.setText('● 录电脑声音'); self.record_button.setEnabled(True)
    def recorded(self,a,rate):
        self.loading=True; self.name.setText(self.t('录音乐句')); self.set_audio(a,rate); self.loading=False; self.save()
    def play_from_current(self,checked=False): self.play(preserve=True)
    def play_from_start(self,checked=False):
        if self.audio is None: return
        self.seek_to(self.start.value()); self.play()
    def play(self,checked=False,preserve=False):
        if self.audio is None: return
        if not self.output_ready: self.error('请先刷新并选择可用的声音输出设备'); return
        try:
            seek=self.player.mixer.source_time if preserve and self.player.stream and self.player.mixer else self.audition
            self.audition=seek
            self.player.stop()
            lo=round(self.start.value()*self.rate); hi=min(len(self.audio),round(self.end.value()*self.rate))
            if hi<=lo: raise ValueError('请选择有效的循环范围')
            speed=self.speed.value(); key=(id(self.audio),self.rate,lo,hi,speed)
            kwargs=dict(rate=self.rate,start=lo/self.rate,end=hi/self.rate,bpm=self.bpm.value(),offset=self.offset.value(),beats=int(self.beats.value()),speed=speed)
            self.pending_play=(key,self.audio,kwargs,seek)
            self.launch_pending()
        except Exception as e: self.stop(); self.error(e)
    def launch_pending(self):
        if not self.pending_play: return
        key,source,kwargs,seek=self.pending_play
        if key[-1]==1: buffer=source[key[2]:key[3]]
        elif self.prepared_cache and self.prepared_cache[0]==key: buffer=self.prepared_cache[1]
        else:
            if self.prepare_worker is None:
                self.prepare_worker=PrepareLoop(key,source[key[2]:key[3]],kwargs['rate'],kwargs['speed'])
                self.prepare_worker.finished.connect(self.preparation_done); self.prepare_worker.start()
            self.status.setText('正在准备变速片段 · 音高保持，界面仍可操作'); return
        try:
            mixer=Mixer(source,**kwargs,prepared_audio=buffer,audio_volume=0 if self.am.isChecked() else self.av.value()/100,click_volume=0 if self.cm.isChecked() else self.cv.value()/100)
            mixer.seek(seek); self.player.play(mixer); self.pending_play=None
            self.status.setText(f'循环播放 · {kwargs["speed"]:g}× · 实际 {kwargs["bpm"]*kwargs["speed"]:g} BPM · 音高保持')
        except Exception as e: self.pending_play=None; self.player.stop(); self.error(e)
    def preparation_done(self):
        worker=self.prepare_worker; self.prepare_worker=None
        relevant=self.pending_play and self.pending_play[0]==worker.key
        if relevant:
            if worker.error: self.pending_play=None; self.error(worker.error)
            else: self.prepared_cache=(worker.key,worker.buffer)
        worker.deleteLater()
        if self.close_pending: self.close(); return
        self.launch_pending()
    def stop(self):
        if self.player.stream and self.player.mixer: self.audition=self.player.mixer.source_time
        self.pending_play=None; self.player.stop(); self.wave.cursor=self.audition if self.audio is not None else None; self.click.cursor=None; self.wave.update(); self.click.update()
    def toggle(self): self.stop() if self.player.stream or self.pending_play else self.play()
    def tick(self):
        if self.piano_output.last_error:
            self.status.setText('钢琴输出错误：'+self.piano_output.last_error); self.piano_output.last_error=None
        m=self.player.mixer
        if self.player.stream and m:
            self.wave.cursor=self.click.cursor=m.source_time; self.wave.update(); self.click.update()
    def delete(self):
        item=self.library.currentItem()
        if not item: return
        key=item.data(Qt.ItemDataRole.UserRole)
        if QMessageBox.question(self,self.t('删除乐句'),self.t('确定删除这个乐句及其录音？'))!=QMessageBox.StandardButton.Yes: return
        if self.key==key:
            self.autosave.stop(); self.stop(); self.audio=None; self.audio_dirty=False; self.undo_stack.clear(); self.undo_button.setEnabled(False); self.wave.audio=None; self.key=None; self.name.clear(); self.wave.update(); self.save_session()
        self.store.delete(key); self.refresh()
    def import_audio(self):
        if self.import_worker is not None or (self.recorder and self.recorder.isRunning()): return
        from media import AUDIO_FILTER
        path,_=QFileDialog.getOpenFileName(self,self.t('导入音乐'),'',self.t(AUDIO_FILTER))
        if not path: return
        if not self.save(): return
        self.stop(); self.status.setText('正在导入音乐…'); self.centralWidget().setEnabled(False)
        self.import_worker=ImportFile(path); self.import_worker.finished.connect(self.import_finished); self.import_worker.start()
    def import_finished(self):
        worker=self.import_worker; self.import_worker=None; self.centralWidget().setEnabled(True)
        worker.deleteLater()
        if self.import_close_pending: self.import_close_pending=False; self.close(); return
        if worker.error: self.status.setText('导入失败，原乐句保持不变'); self.error(worker.error); return
        try:
            if not self.new(): return
            self.name.setText(Path(worker.path).stem); self.set_audio(worker.audio,worker.rate); self.save()
        except Exception as e: self.error(e)
    def error(self,e): QMessageBox.warning(self,self.t('操作未完成'),self.t(str(e)))
    def changeEvent(self,event):
        if event.type()==event.Type.ActivationChange and not self.isActiveWindow() and hasattr(self,'piano'):
            self.piano.switch_note(None)
        super().changeEvent(event)
    def closeEvent(self,e):
        if self.import_worker is not None:
            self.import_close_pending=True; self.status.setText('等待导入结束后关闭…'); e.ignore(); return
        if self.recorder and self.recorder.isRunning():
            self.recorder.stopping.set(); self.status.setText('正在结束录音，请稍后关闭'); e.ignore(); return
        if self.prepare_worker is not None:
            self.close_pending=True; self.stop(); self.status.setText('正在完成音频处理，完成后自动关闭'); e.ignore(); return
        self.stop()
        self.autosave.stop()
        if not self.save(): e.ignore(); return
        self.piano.switch_note(None); self.piano_output.close()
        try: self.save_session()
        except OSError as exc: self.error(exc); e.ignore(); return
        e.accept()

def configure_app(app):
    app.setApplicationName('Riff Tonic')
    app.setStyle('Fusion')
    from PySide6.QtGui import QFont
    app.setFont(QFont('Microsoft YaHei UI',10))
    app.setStyleSheet('''
        QWidget { color:#776e65; font-family:"Microsoft YaHei UI"; font-size:12px; background:transparent; }
        QMainWindow, QWidget#host, QMessageBox, QFileDialog { background:#faf8ef; }
        QWidget#workspace { background:#fffdf8; border:1px solid #eae3d8; border-radius:18px; }
        QLabel#brand { font-family:"Segoe UI"; font-size:32px; font-weight:700; color:#776e65; padding-bottom:12px; }
        QLabel#heading { font-size:20px; font-weight:600; color:#64584e; padding-bottom:4px; }
        QPushButton { background:#eee4da; border:1px solid #e6d9cb; padding:10px 13px; border-radius:9px; font-weight:500; }
        QPushButton:hover { background:#e6d5c2; } QPushButton:pressed { background:#d9c4ad; }
        QPushButton:disabled { color:#b7ada3; background:#f3eee5; border-color:#eee8de; }
        QPushButton#accent { background:#f2b179; color:#fffdf8; border-color:#eda76a; }
        QPushButton#accent:hover { background:#eda368; }
        QLineEdit,QDoubleSpinBox,QSpinBox { background:#fffdf8; padding:8px; border:1px solid #dfd5c8; border-radius:8px; selection-background-color:#eac49d; }
        QLineEdit:focus,QDoubleSpinBox:focus { border:1px solid #d19b6b; }
        QDoubleSpinBox { min-width:62px; } QDoubleSpinBox::up-button,QDoubleSpinBox::down-button { width:16px; border:0; }
        QListWidget { background:transparent; border:0; outline:0; }
        QListWidget::item { padding:12px 10px; border-radius:9px; margin-bottom:5px; }
        QListWidget::item:selected { background:#e8d7c4; color:#70563f; }
        QListWidget::item:hover { background:#f0e7db; }
        QCheckBox { spacing:6px; } QCheckBox::indicator { width:15px; height:15px; border:1px solid #c7b6a3; border-radius:4px; background:#fffdf8; }
        QCheckBox::indicator:checked { background:#cd8c55; border-color:#b87b48; }
        QComboBox { background:#fffdf8; border:1px solid #dfd5c8; border-radius:8px; padding:8px; }
        QComboBox QAbstractItemView { background:#fffdf8; selection-background-color:#e8d7c4; }
        QScrollBar:horizontal { background:#eee6d9; border-radius:5px; height:12px; }
        QScrollBar::handle:horizontal { background:#cbb69b; border-radius:5px; min-width:40px; }
        QScrollBar::add-line:horizontal,QScrollBar::sub-line:horizontal { width:0px; }
        QSlider::groove:horizontal { height:4px; background:#e5d9c9; border-radius:2px; }
        QSlider::handle:horizontal { width:12px; margin:-4px 0; background:#c18c57; border-radius:6px; }
        QToolTip { background:#776e65; color:#fffaf2; padding:6px; border:0; }
    ''')
def main():
    app=QApplication(sys.argv); configure_app(app)
    if '--self-test' in sys.argv:
        import tempfile
        import soundcard, sounddevice
        with tempfile.TemporaryDirectory() as root:
            w=Window(root); w.set_language('en'); w.name.setText('Packaging check'); w.set_audio(np.zeros((48000,2),np.float32),48000); w.select(.1,.9); w.seek_to(.4); w.speed.setValue(.75); w.save(); key=w.key; w.close()
            v=Window(root)
            assert v.key==key and v.start.value()==.1 and v.end.value()==.9 and v.player.stream is None
            assert v.speed.value()==.75 and v.audition==.4
            assert v.language=='en' and v.record_button.text()=='● Record system audio' and v.brand.renderer.isValid()
            assert not v.windowIcon().isNull()
            m=Mixer(v.audio,48000,.1,.9,speed=.75)
            assert m.output_length==51200 and np.isfinite(m.render(512)).all()
            from piano import PianoSynth
            synth=PianoSynth(); synth.note_on(48); assert np.max(np.abs(synth.render(2048)))>0
            v.piano.pan_to(72)
            assert v.piano.key_rect(72).right()<=v.piano.width()
            from media import load_audio
            import imageio_ffmpeg,subprocess
            mp3=Path(root)/'decoder-check.mp3'
            subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-nostdin','-i',str(Path(root)/(key+'.wav')),str(mp3)],check=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            decoded,sample_rate=load_audio(mp3)
            assert sample_rate==48000 and decoded.shape[1]==2 and len(decoded)>=47000
            v.refresh_devices(); assert v.output_ready
            if '--audio-test' in sys.argv:
                v.piano_output.note_on(72)
                QTimer.singleShot(900,lambda:v.piano_output.note_off(72))
                QTimer.singleShot(1400,app.quit); app.exec()
            v.show(); app.processEvents(); v.close()
        return
    w=Window()
    if '--lang' in sys.argv:
        index=sys.argv.index('--lang')
        if index+1<len(sys.argv): w.set_language(sys.argv[index+1])
    w.show(); sys.exit(app.exec())
if __name__=='__main__': main()
