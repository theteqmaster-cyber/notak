import os
from collections import defaultdict
from datetime import datetime
from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QPainter, QColor, QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QTableWidgetItem, QHeaderView
from qfluentwidgets import (SubtitleLabel, BodyLabel, SpinBox, PrimaryPushButton, 
                            TransparentPushButton, TitleLabel, FluentIcon as FIF,
                            CardWidget, PushButton, LineEdit, ComboBox, TableWidget,
                            InfoBar, InfoBarPosition, ScrollArea)

from core.database import get_session_history

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
            painter.setBrush(QColor(0, 120, 215, 200))
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


class SessionInterface(QWidget):
    # Signal emitted when a session starts (int: minutes, str: intent)
    sessionStarted = Signal(int, str)
    # Signal emitted when a session is cancelled
    sessionCancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("SessionInterface")
        self.setStyleSheet("background: transparent;")
        
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Scroll area
        self.scroll_area = ScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        
        self.scroll_widget = QWidget()
        self.scroll_widget.setStyleSheet("background: transparent;")
        self.layout = QVBoxLayout(self.scroll_widget)
        self.layout.setContentsMargins(40, 40, 40, 40)
        self.layout.setSpacing(20)
        
        # Header
        self.title = TitleLabel("Focus Sessions", self)
        self.title.setStyleSheet("font-size: 32px; font-weight: bold;")
        self.layout.addWidget(self.title)
        
        self.subtitle = BodyLabel("Master your time to master your pressure. Set a timer and stay focused on a single module without getting burnt out.", self)
        self.subtitle.setWordWrap(True)
        self.subtitle.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 14px; margin-bottom: 20px;")
        self.layout.addWidget(self.subtitle)

        # Settings Card
        self.card = CardWidget(self)
        self.card.setStyleSheet("""
            CardWidget {
                background: rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
            }
        """)
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(30, 30, 30, 30)
        card_layout.setSpacing(25)
        
        # Intent Layout
        intent_layout = QHBoxLayout()
        intent_label = SubtitleLabel("Session Intent:")
        self.intent_input = LineEdit(self)
        self.intent_input.setPlaceholderText("e.g. Statistics Mean, Math Ch 4, Physics Review")
        self.intent_input.setMinimumWidth(300)
        intent_layout.addWidget(intent_label)
        intent_layout.addWidget(self.intent_input)
        intent_layout.addStretch(1)
        card_layout.addLayout(intent_layout)
        
        # Custom Time Layout
        custom_layout = QHBoxLayout()
        time_label = SubtitleLabel("Custom Time (minutes):")
        
        self.time_spinbox = SpinBox(self)
        self.time_spinbox.setRange(1, 240)
        self.time_spinbox.setValue(20)
        self.time_spinbox.setFixedWidth(150)
        
        custom_layout.addWidget(time_label)
        custom_layout.addWidget(self.time_spinbox)
        custom_layout.addStretch(1)
        card_layout.addLayout(custom_layout)
        
        # Preset Buttons
        presets_label = BodyLabel("Quick Presets:")
        presets_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        card_layout.addWidget(presets_label)
        
        preset_layout = QHBoxLayout()
        preset_layout.setSpacing(15)
        
        self.btn_10m = PushButton("10 min", self)
        self.btn_20m = PushButton("20 min", self)
        self.btn_40m = PushButton("40 min", self)
        self.btn_60m = PushButton("60 min", self)
        
        self.btn_10m.clicked.connect(lambda: self.time_spinbox.setValue(10))
        self.btn_20m.clicked.connect(lambda: self.time_spinbox.setValue(20))
        self.btn_40m.clicked.connect(lambda: self.time_spinbox.setValue(40))
        self.btn_60m.clicked.connect(lambda: self.time_spinbox.setValue(60))
        
        preset_layout.addWidget(self.btn_10m)
        preset_layout.addWidget(self.btn_20m)
        preset_layout.addWidget(self.btn_40m)
        preset_layout.addWidget(self.btn_60m)
        preset_layout.addStretch(1)
        card_layout.addLayout(preset_layout)
        
        self.layout.addWidget(self.card)
        
        # Action Buttons
        action_layout = QHBoxLayout()
        self.btn_start = PrimaryPushButton(FIF.PLAY, "Start Session", self)
        self.btn_start.setFixedSize(200, 45)
        self.btn_start.setStyleSheet("font-size: 16px;")
        self.btn_start.clicked.connect(self.start_session)
        
        self.btn_cancel = TransparentPushButton(FIF.CANCEL, "Cancel Active Session", self)
        self.btn_cancel.setFixedSize(200, 45)
        self.btn_cancel.clicked.connect(self.cancel_session)
        
        action_layout.addWidget(self.btn_start)
        action_layout.addWidget(self.btn_cancel)
        action_layout.addStretch(1)
        
        self.layout.addLayout(action_layout)
        
        # History Section
        history_header = QHBoxLayout()
        history_title = TitleLabel("Session History", self)
        history_title.setStyleSheet("font-size: 24px; font-weight: bold; margin-top: 20px;")
        history_header.addWidget(history_title)
        history_header.addStretch(1)
        
        self.filter_combo = ComboBox(self)
        self.filter_combo.addItems(["7 Days", "14 Days", "1 Month", "All Time"])
        self.filter_combo.currentIndexChanged.connect(self.load_history)
        history_header.addWidget(self.filter_combo)
        
        self.layout.addLayout(history_header)
        
        # Graph Card
        self.graph_card = CardWidget(self)
        self.graph_card.setStyleSheet("""
            CardWidget {
                background: rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
            }
        """)
        graph_layout = QVBoxLayout(self.graph_card)
        self.graph_widget = SessionGraphWidget(self)
        graph_layout.addWidget(self.graph_widget)
        self.layout.addWidget(self.graph_card)
        
        # Table Card
        self.table = TableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Date", "Intent", "Duration", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setMinimumHeight(250)
        self.layout.addWidget(self.table)
        
        self.layout.addStretch(1)
        
        self.scroll_area.setWidget(self.scroll_widget)
        self.main_layout.addWidget(self.scroll_area)
        
        # Initial load
        self.load_history()

    def start_session(self):
        intent = self.intent_input.text().strip()
        if not intent:
            InfoBar.error(
                title='Intent Required',
                content="Please enter the cause/intent of this session before starting.",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=3000,
                parent=self
            )
            return
            
        minutes = self.time_spinbox.value()
        self.sessionStarted.emit(minutes, intent)
        # Clear input after starting
        self.intent_input.clear()

    def cancel_session(self):
        self.sessionCancelled.emit()

    def load_history(self):
        idx = self.filter_combo.currentIndex()
        if idx == 0:
            days = 7
        elif idx == 1:
            days = 14
        elif idx == 2:
            days = 30
        else:
            days = None
            
        history = get_session_history(days)
        
        # 1. Update Table
        self.table.setRowCount(len(history))
        for i, row in enumerate(history):
            date_item = QTableWidgetItem(row['created_at'].split(" ")[0])
            intent_item = QTableWidgetItem(row['intent'])
            duration_item = QTableWidgetItem(f"{row['duration_minutes']} min")
            status_item = QTableWidgetItem(row['status'].capitalize())
            
            # Color coding
            if row['status'] == 'finished':
                status_item.setForeground(QColor(0, 200, 0))
            else:
                status_item.setForeground(QColor(200, 0, 0))
                
            self.table.setItem(i, 0, date_item)
            self.table.setItem(i, 1, intent_item)
            self.table.setItem(i, 2, duration_item)
            self.table.setItem(i, 3, status_item)
            
        # 2. Update Graph Data
        # Group by date, sum duration for finished sessions
        graph_data = defaultdict(int)
        for row in history:
            if row['status'] == 'finished':
                date_str = row['created_at'].split(" ")[0]
                graph_data[date_str] += row['duration_minutes']
                
        self.graph_widget.set_data(dict(graph_data))
