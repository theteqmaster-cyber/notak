import os
import datetime
from PySide6.QtCore import Qt, QTimer, Signal, QDateTime, QDate
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog
from qfluentwidgets import (ScrollArea, TitleLabel, SubtitleLabel, TransparentPushButton, 
                            StrongBodyLabel, CardWidget, IconWidget, FluentIcon as FIF, BodyLabel)

from core.database import get_events_for_date

class HomeInterface(ScrollArea):
    backgroundChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("HomeInterface")
        self.view = QWidget(self)
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.setStyleSheet("ScrollArea { background-color: transparent; border: none; }")
        self.view.setStyleSheet("QWidget { background-color: transparent; }")

        self.vBoxLayout = QVBoxLayout(self.view)
        self.vBoxLayout.setContentsMargins(40, 20, 40, 40)
        self.vBoxLayout.setSpacing(30)
        self.vBoxLayout.setAlignment(Qt.AlignTop)

        # Top Action Area (Inspiration Button)
        self.top_actions = QHBoxLayout()
        self.top_actions.setAlignment(Qt.AlignLeft)
        
        self.btn_inspiration = TransparentPushButton(FIF.PHOTO, "Import Inspiration", self.view)
        self.btn_inspiration.setFixedSize(180, 40)
        self.btn_inspiration.clicked.connect(self.import_inspiration)
        self.btn_inspiration.setStyleSheet("""
            TransparentPushButton {
                color: rgba(255, 255, 255, 0.4);
                font-weight: 500;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            TransparentPushButton:hover {
                color: white;
                background: rgba(255, 255, 255, 0.1);
            }
        """)
        
        self.top_actions.addWidget(self.btn_inspiration)
        self.vBoxLayout.addLayout(self.top_actions)

        # Hero / Clock Section
        self.vBoxLayout.addSpacing(120)
        
        self.clock_label = TitleLabel("", self.view)
        self.clock_label.setAlignment(Qt.AlignCenter)
        font = self.clock_label.font()
        font.setPointSize(72)
        font.setBold(True)
        self.clock_label.setFont(font)
        self.clock_label.setStyleSheet("color: white; font-weight: bold;")
        
        self.date_label = SubtitleLabel("", self.view)
        self.date_label.setAlignment(Qt.AlignCenter)
        self.date_label.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 24px;")
        
        self.vBoxLayout.addWidget(self.clock_label)
        self.vBoxLayout.addWidget(self.date_label)
        
        self.vBoxLayout.addSpacing(40)
        
        # Today's Events Card
        self.events_card = CardWidget(self.view)
        self.events_card.setFixedWidth(400)
        self.events_card.setStyleSheet("""
            CardWidget {
                background: rgba(0, 0, 0, 0.4);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
            }
        """)
        self.ev_card_layout = QVBoxLayout(self.events_card)
        self.ev_card_layout.setContentsMargins(20, 20, 20, 20)
        self.ev_card_layout.setAlignment(Qt.AlignCenter)
        
        self.ev_header = StrongBodyLabel("TODAY'S EVENTS", self.events_card)
        self.ev_header.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-size: 11px; letter-spacing: 1px;")
        self.ev_card_layout.addWidget(self.ev_header, alignment=Qt.AlignCenter)
        
        self.ev_list_layout = QVBoxLayout()
        self.ev_list_layout.setSpacing(8)
        self.ev_card_layout.addLayout(self.ev_list_layout)
        
        self.vBoxLayout.addWidget(self.events_card, alignment=Qt.AlignCenter)
        
        # Clock Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_clock)
        self.timer.start(1000)
        self.update_clock()

    def update_clock(self):
        now = QDateTime.currentDateTime()
        self.clock_label.setText(now.toString("HH:mm:ss"))
        self.date_label.setText(now.toString("dddd, MMMM d, yyyy"))

    def import_inspiration(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Background Image", "", 
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if file_path:
            self.backgroundChanged.emit(file_path)

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_today_events()

    def refresh_today_events(self):
        # Clear existing
        for i in reversed(range(self.ev_list_layout.count())):
            widget = self.ev_list_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
                
        today = QDate.currentDate().toString("yyyy-MM-dd")
        events = get_events_for_date(today)
        
        if not events:
            lbl = BodyLabel("No tasks for today. Stay focused!")
            lbl.setStyleSheet("color: #666; font-style: italic; font-size: 13px;")
            self.ev_list_layout.addWidget(lbl, alignment=Qt.AlignCenter)
        else:
            for ev in events:
                elbl = BodyLabel(ev['title'])
                elbl.setStyleSheet("color: white; font-size: 15px; font-weight: 500;")
                self.ev_list_layout.addWidget(elbl, alignment=Qt.AlignCenter)
