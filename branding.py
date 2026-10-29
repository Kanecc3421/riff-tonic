from pathlib import Path
import sys
from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QWidget

class BrandMark(QWidget):
    def __init__(self):
        super().__init__(); self.setFixedHeight(106)
        path=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'assets'/'branding'/'wordmark.svg'
        self.renderer=QSvgRenderer(str(path))
        self.setAccessibleName('Riff Tonic')
    def paintEvent(self,event):
        painter=QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.renderer.render(painter,QRectF(0,0,self.width(),99))
