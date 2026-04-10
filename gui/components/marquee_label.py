from PySide6.QtCore import Qt, QTimer, QRect, QPoint
from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtGui import QPainter, QFontMetrics

class MarqueeLabel(QWidget):
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.text = text
        self.offset = 0
        self.scroll_speed = 1 # pixels per frame
        self.gap = 50 # space between loops
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_offset)
        self.timer.setInterval(30) # ~33 fps for smooth motion
        
        self.setFixedHeight(30)
        self.setStyleSheet("background: transparent; color: white; font-weight: bold; border: none;")

    def setText(self, text):
        self.text = text
        self.offset = 0
        self.update()
        # Only start timer if text is too long
        metrics = QFontMetrics(self.font())
        if metrics.horizontalAdvance(self.text) > self.width():
            if not self.timer.isActive():
                self.timer.start()
        else:
            self.timer.stop()

    def update_offset(self):
        metrics = QFontMetrics(self.font())
        text_width = metrics.horizontalAdvance(self.text)
        
        if text_width <= self.width():
            self.timer.stop()
            self.offset = 0
            self.update()
            return
            
        self.offset -= self.scroll_speed
        if abs(self.offset) >= text_width + self.gap:
            self.offset = 0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        metrics = QFontMetrics(self.font())
        text_width = metrics.horizontalAdvance(self.text)
        
        # Center horizontally if text fits
        if text_width <= self.width():
            painter.drawText(self.rect(), Qt.AlignVCenter | Qt.AlignLeft, self.text)
            return

        # Continuous loop drawing
        # 1. Main text at current offset
        painter.drawText(self.offset, metrics.ascent() + (self.height() - metrics.height()) // 2, self.text)
        
        # 2. Second copy for seamless transition
        painter.drawText(self.offset + text_width + self.gap, metrics.ascent() + (self.height() - metrics.height()) // 2, self.text)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Re-check if scrolling is needed on resize
        self.setText(self.text)
