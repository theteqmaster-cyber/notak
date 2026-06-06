from PySide6.QtCore import Qt, QTimer, QRect, QPoint, QSize
from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QPainter, QFontMetrics, QPalette

class MarqueeLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.text_content = text # Renamed to avoid collision with QLabel.text()
        self.offset = 0
        self.scroll_speed = 1 # pixels per frame
        self.gap = 50 # space between loops
        self.alignment_flags = Qt.AlignLeft | Qt.AlignVCenter
        self._is_hovered = False
        self.always_scroll = False
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_offset)
        self.timer.setInterval(30) # ~33 fps for smooth motion
        
        self.setFixedHeight(30)
        self.setAttribute(Qt.WA_StyledBackground)
        self.setStyleSheet("background: transparent; color: white; font-weight: bold; border: none;")

    def setAlignment(self, alignment):
        self.alignment_flags = alignment
        self.update()

    def setText(self, text):
        self.text_content = text
        super().setText("") # Hide the original QLabel text rendering
        self.offset = 0
        self.check_overflow()
        self.update()

    def check_overflow(self):
        metrics = QFontMetrics(self.font())
        if self.isVisible() and (self.always_scroll or self._is_hovered) and metrics.horizontalAdvance(self.text_content) > self.width() > 0:
            if not self.timer.isActive():
                self.timer.start()
        else:
            self.timer.stop()
            self.offset = 0
            self.update()

    def showEvent(self, event):
        super().showEvent(event)
        self.check_overflow()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.timer.stop()
        self.offset = 0

    def enterEvent(self, event):
        super().enterEvent(event)
        self._is_hovered = True
        self.check_overflow()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._is_hovered = False
        self.check_overflow()

    def update_offset(self):
        metrics = QFontMetrics(self.font())
        text_width = metrics.horizontalAdvance(self.text_content)
        
        if text_width <= self.width():
            self.timer.stop()
            self.offset = 0
            self.update()
            return
            
        self.offset -= self.scroll_speed
        if abs(self.offset) >= text_width + self.gap:
            self.offset = 0
        self.update()

    def sizeHint(self):
        metrics = QFontMetrics(self.font())
        # Default size hint based on text width or minimum width
        width = metrics.horizontalAdvance(self.text_content)
        return QSize(min(width + 20, 200), 30)

    def minimumSizeHint(self):
        return QSize(50, 30)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Use the stylesheet-defined color if possible, otherwise white
        color = self.palette().color(QPalette.WindowText)
        painter.setPen(color)
        
        metrics = QFontMetrics(self.font())
        text_width = metrics.horizontalAdvance(self.text_content)
        
        # If we have no width yet, don't draw
        if self.width() <= 0:
            return
        
        # Draw normally if text fits, respecting alignment
        if text_width <= self.width():
            painter.drawText(self.rect(), self.alignment_flags, self.text_content)
            return

        # Continuous loop drawing
        # 1. Main text at current offset
        y = metrics.ascent() + (self.height() - metrics.height()) // 2
        painter.drawText(int(self.offset), int(y), self.text_content)
        
        # 2. Second copy for seamless transition
        painter.drawText(int(self.offset + text_width + self.gap), int(y), self.text_content)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Re-check if scrolling is needed on resize
        self.check_overflow()
