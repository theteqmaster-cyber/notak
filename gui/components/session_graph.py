from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor
from PySide6.QtWidgets import QWidget

class SessionGraphWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(220)
        self.data = {} # {"YYYY-MM-DD": minutes}

    def set_data(self, data):
        self.data = data
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), QColor(0, 0, 0, 50))
        
        if not self.data:
            painter.setPen(QColor(255, 255, 255, 100))
            painter.drawText(self.rect(), Qt.AlignCenter, "No finished sessions in this period.")
            return

        keys = list(self.data.keys())
        keys.sort()
        # Keep only the last 8 days if more
        keys = keys[-8:]
        
        values = [self.data[k] for k in keys]
        max_val = max(values) if values else 1
        
        width = self.width()
        height = self.height()
        
        margin_x = 40
        margin_y = 30
        
        graph_width = width - 2 * margin_x
        graph_height = height - 2 * margin_y
        
        # Draw axes
        painter.setPen(QColor(255, 255, 255, 100))
        painter.drawLine(margin_x, height - margin_y, width - margin_x, height - margin_y)
        painter.drawLine(margin_x, margin_y, margin_x, height - margin_y)
        
        # Draw bars
        n = len(keys)
        bar_width = min(40, graph_width / max(n, 1) * 0.6)
        spacing = (graph_width - (n * bar_width)) / max(n + 1, 2)
        
        for i, key in enumerate(keys):
            val = self.data[key]
            bar_h = (val / max_val) * graph_height
            
            x = margin_x + spacing + i * (bar_width + spacing)
            y = height - margin_y - bar_h
            
            rect = QRectF(x, y, bar_width, bar_h)
            painter.setBrush(QColor(163, 113, 247, 200)) # Purple theme for Zeni
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(rect, 4, 4)
            
            # Label
            painter.setPen(QColor(255, 255, 255, 200))
            font = painter.font()
            font.setPointSize(8)
            painter.setFont(font)
            
            # Draw day (e.g. "04-21")
            day_str = key[-5:]
            painter.drawText(int(x), int(height - margin_y + 10), int(bar_width), 15, Qt.AlignCenter, day_str)
            
            # Draw value
            painter.drawText(int(x), int(y - 20), int(bar_width), 15, Qt.AlignCenter, f"{val}m")
