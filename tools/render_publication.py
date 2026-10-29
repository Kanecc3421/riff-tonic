"""Reproducible native screenshots and editorial share cards; no invented UI."""
from pathlib import Path
import sys
import tempfile
import html
import numpy as np
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt,QRectF
from PySide6.QtGui import QImage,QPainter,QColor,QFont,QPainterPath
from PySide6.QtSvg import QSvgRenderer

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app import Window,configure_app

OUT=ROOT/'publication'/'images'
INK='#695344'; MUTED='#a08c76'; AMBER='#c79055'; PAPER='#faf8ef'

def text(p,x,y,w,value,size=30,color=INK,bold=False,serif=False):
    f=QFont('Georgia' if serif else 'Microsoft YaHei UI'); f.setPixelSize(size); f.setBold(bold)
    p.setFont(f); p.setPen(QColor(color))
    box=QRectF(x,y,w,4000)
    bounds=p.boundingRect(box,Qt.TextFlag.TextWordWrap,value)
    p.drawText(box,Qt.TextFlag.TextWordWrap,value)
    return y+bounds.height()

def panel(p,x,y,w,h,color='#fffdf8',radius=24):
    p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(color)); p.drawRoundedRect(QRectF(x,y,w,h),radius,radius)

def picture(p,path,x,y,w,h,rounding=0):
    image=QImage(str(path)); assert not image.isNull(),path
    scale=min(w/image.width(),h/image.height()); iw=image.width()*scale; ih=image.height()*scale
    target=QRectF(x+(w-iw)/2,y+(h-ih)/2,iw,ih)
    p.save()
    if rounding:
        clip=QPainterPath(); clip.addRoundedRect(target,rounding,rounding); p.setClipPath(clip)
    p.drawImage(target,image); p.restore()

def mark(p,x=60,y=40,w=270):
    svg=QSvgRenderer(str(ROOT/'assets/branding/wordmark.svg'))
    svg.render(p,QRectF(x,y,w,w*198/420))

def start(w,h):
    image=QImage(w,h,QImage.Format.Format_ARGB32); image.fill(QColor(PAPER))
    painter=QPainter(image); painter.setRenderHint(QPainter.RenderHint.Antialiasing); painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    return image,painter

def finish(image,p,name):
    p.end(); assert image.save(str(OUT/name)); return OUT/name

def footer(p,y,w=1080):
    text(p,60,y,w-120,'RIFF TONIC  /  WINDOWS  /  EN + 中文',19,MUTED)

def screenshots(app):
    with tempfile.TemporaryDirectory() as d:
        w=Window(d); rate=48000; t=np.arange(rate*8)/rate
        freq=np.take([220,261.6256,293.6648,329.6276],(t*2).astype(int)%4)
        wave=(.55*np.sin(2*np.pi*freq*t)+.12*np.sin(4*np.pi*freq*t))*np.exp(-(t%.5)*8)
        w.set_audio(wave.astype(np.float32)[:,None],rate); w.select(1,5); w.offset.setValue(1); w.seek_to(2.25); w.speed.setValue(.75)
        w.name.setText('五声音阶 · 示范乐句'); w.show(); app.processEvents()
        w.grab().save(str(OUT/'app-zh.png')); w.wave.grab().save(str(OUT/'wave-detail.png')); w.piano.grab().save(str(OUT/'piano-detail.png'))
        w.name.setText('Pentatonic phrase · demo'); w.set_language('en'); app.processEvents(); w.grab().save(str(OUT/'app-en.png'))
        w.close()

def github():
    image,p=start(1280,640); mark(p,55,25,260)
    text(p,60,175,575,'Catch a phrase.\nMake it yours.',65,bold=True,serif=True)
    text(p,60,365,525,'Capture. Loop. Slow down.\nBack to the guitar.',27)
    panel(p,60,492,515,68,'#eee4d6',14)
    text(p,82,511,480,'0.5–2×  ·  PITCH PRESERVED',23,bold=True)
    text(p,60,588,530,'Windows desktop  /  中文 + English',20,MUTED)
    panel(p,640,45,595,555,'#e9dfd1',28)
    picture(p,OUT/'app-en.png',655,60,565,525,18)
    return finish(image,p,'github-hero.png')

def xhs_cover():
    image,p=start(1080,1440); mark(p); picture(p,ROOT/'assets/branding/riff-tonic-desktop.png',795,60,205,205)
    text(p,60,245,940,'一句乐句，\n慢一点。',92,bold=True)
    text(p,65,493,930,'Riff Tonic · 你的桌面吉他练习小工具',30,MUTED)
    panel(p,60,572,960,758,'#e9dfd1'); picture(p,OUT/'app-zh.png',73,585,934,732,18)
    footer(p,1380); return finish(image,p,'xiaohongshu-01-cover.png')

def xhs_loop():
    image,p=start(1080,1440); mark(p)
    text(p,60,230,960,'把难点\n圈出来。',86,bold=True)
    for index,(title,sub) in enumerate([('录下或导入','从原曲里留下一小段。'),('圈出一句','拖动两端手柄，精调循环范围。'),('对齐节拍','找到第一拍，吸附，再微调。'),('反复跟弹','从游标开始听，也能从头再来。')]):
        y=505+index*94; panel(p,60,y,57,57,'#ecd8be',14)
        text(p,76,y+7,40,str(index+1),30,bold=True)
        text(p,143,y-1,800,title,31,bold=True); text(p,143,y+40,800,sub,24,MUTED)
    panel(p,60,925,960,258,'#eee4d6'); picture(p,OUT/'wave-detail.png',76,941,928,226,12)
    text(p,60,1220,960,'A–B 循环 · 独立试听游标 · 剪辑与撤销',29)
    footer(p,1380); return finish(image,p,'xiaohongshu-02-loop.png')

def xhs_speed():
    image,p=start(1080,1440); mark(p)
    text(p,60,235,960,'慢下来，\n音高留住。',85,bold=True)
    panel(p,60,515,960,355,'#eee2d1',26)
    text(p,100,540,880,'0.75×',168,AMBER,bold=True,serif=True)
    text(p,104,754,850,'120 BPM → 90 BPM',47,bold=True)
    text(p,60,930,960,'音频与节拍器共用倍率。',39,bold=True)
    text(p,60,997,960,'慢放或快放都保持音高，\n从听清每个细节开始。',33,MUTED)
    picture(p,OUT/'wave-detail.png',60,1138,960,166,12)
    footer(p,1380); return finish(image,p,'xiaohongshu-03-speed.png')

def xhs_save():
    image,p=start(1080,1440); mark(p)
    text(p,60,230,960,'今天这一句，\n下次接着练。',77,bold=True)
    blocks=[('01  乐句收藏','音频、循环位置和练习设置一起保存在本机。'),('02  钢琴找音','C2–C5 键盘横移，音量与余音独立可调。'),('03  中英文界面','准备好后再播放，按自己的节奏练习。')]
    for i,(title,body) in enumerate(blocks):
        y=510+i*155; panel(p,60,y,960,132,'#eee6db',18)
        text(p,84,y+20,912,title,33,bold=True); text(p,84,y+75,912,body,26)
    text(p,60,1030,960,'用耳朵听，再用琴键对照。',32,bold=True)
    panel(p,60,1100,960,160); picture(p,OUT/'piano-detail.png',74,1114,932,132,8)
    footer(p,1380); return finish(image,p,'xiaohongshu-04-save.png')

def wechat_square():
    image,p=start(1080,1080); mark(p,60,35,270)
    text(p,60,240,960,'给喜欢的乐句，\n多一点时间。',77,bold=True)
    picture(p,ROOT/'assets/branding/riff-tonic-desktop.png',355,500,370,370)
    text(p,60,913,960,'录音 / 导入 · 循环 · 变速不变调 · 钢琴找音',27)
    footer(p,1010); return finish(image,p,'wechat-square.png')

def wechat_long():
    image,p=start(1080,2400); mark(p,60,45,310)
    text(p,60,255,960,'这一句，\n练到属于你。',88,bold=True)
    text(p,64,490,950,'Riff Tonic · Windows 乐句练习工具',30,MUTED)
    panel(p,60,575,960,810,'#e9dfd1'); picture(p,OUT/'app-zh.png',76,591,928,778,16)
    for i,(head,body) in enumerate([('留住难点','录电脑声音，或导入常见音频格式。'),('跟着节拍慢练','0.5–2× 不变调，音频与节拍器一起变速。'),('今天练，明天接着练','乐句保存在本机，中英文随时切换。')]):
        y=1450+i*180; text(p,65,y,950,head,43,bold=True); text(p,65,y+73,950,body,29,MUTED)
    picture(p,OUT/'piano-detail.png',60,2020,960,150,8)
    text(p,65,2225,950,'小小一杯，留给每一句想弹好的音乐。',31)
    footer(p,2330); return finish(image,p,'wechat-long.png')

def gallery(paths):
    cards='\n'.join(f'<figure><a href="images/{html.escape(p.name)}"><img src="images/{html.escape(p.name)}"></a><figcaption>{html.escape(p.name)}</figcaption></figure>' for p in paths)
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>Riff Tonic 发布素材</title><style>body{background:#faf8ef;color:#695344;font:16px system-ui;margin:40px}h1{font:italic bold 48px Georgia}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:24px}figure{margin:0}img{width:100%;border-radius:16px}figcaption{padding:12px}a{color:inherit}</style><h1>Riff Tonic</h1><p>真实界面截图 · GitHub / 小红书 / 微信配图。点击图片查看原尺寸。</p><p>文案：<a href="text/xiaohongshu.md">小红书</a> · <a href="text/wechat.md">微信</a> · <a href="text/release-v0.8.md">发布说明</a> · <a href="text/upload-checklist.md">上传检查</a></p><main>'''+cards+'</main></html>'
    (ROOT/'publication/index.html').write_text(page,encoding='utf-8')
    image,p=start(1600,1500)
    for i,path in enumerate(paths):
        x=30+(i%4)*395; y=25+(i//4)*730
        picture(p,path,x,y,365,650,10); text(p,x,y+660,365,path.stem,17)
    finish(image,p,'preview-sheet.png')

def main():
    OUT.mkdir(parents=True,exist_ok=True); app=QApplication.instance() or QApplication([]); configure_app(app)
    screenshots(app)
    paths=[github(),xhs_cover(),xhs_loop(),xhs_speed(),xhs_save(),wechat_square(),wechat_long()]
    gallery(paths); print('Rendered',len(paths),'publication cards plus bilingual screenshots.')

if __name__=='__main__': main()
