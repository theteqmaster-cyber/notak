import os
import datetime
from PySide6.QtCore import Qt, QTimer, Signal, QDateTime, QDate
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog
from qfluentwidgets import (ScrollArea, TitleLabel, SubtitleLabel, TransparentPushButton, SearchLineEdit,
                            StrongBodyLabel, CardWidget, IconWidget, FluentIcon as FIF, BodyLabel, CaptionLabel)

from core.database import get_events_for_date, get_recent_files, get_library_stats
from core.importer import split_filename_for_display

class HomeInterface(ScrollArea):
    backgroundChanged = Signal(str)
    searchRequested = Signal(str)

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
        
        self.btn_search = TransparentPushButton(FIF.SEARCH, "Deep Search", self.view)
        self.btn_search.setFixedSize(180, 40)
        self.btn_search.clicked.connect(lambda: self.searchRequested.emit(""))
        self.btn_search.setStyleSheet(self.btn_inspiration.styleSheet())
        self.top_actions.addWidget(self.btn_search)
        
        self.vBoxLayout.addLayout(self.top_actions)

        # Hero / Clock / Quick Search Section
        self.vBoxLayout.addSpacing(60)
        
        self.clock_label = TitleLabel("", self.view)
        self.clock_label.setAlignment(Qt.AlignCenter)
        font = self.clock_label.font()
        font.setPointSize(64)
        font.setBold(True)
        self.clock_label.setFont(font)
        self.clock_label.setStyleSheet("color: white; font-weight: bold;")
        self.vBoxLayout.addWidget(self.clock_label)
        
        self.date_label = SubtitleLabel("", self.view)
        self.date_label.setAlignment(Qt.AlignCenter)
        self.date_label.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 20px;")
        self.vBoxLayout.addWidget(self.date_label)
        
        self.vBoxLayout.addSpacing(40)
        
        # Quick Search Bar in Hero
        self.hero_search = SearchLineEdit(self.view)
        self.hero_search.setPlaceholderText("Quick search your entire library...")
        self.hero_search.setFixedWidth(500)
        self.hero_search.searchButton.clicked.connect(lambda: self.searchRequested.emit(self.hero_search.text()))
        self.hero_search.returnPressed.connect(lambda: self.searchRequested.emit(self.hero_search.text()))
        self.vBoxLayout.addWidget(self.hero_search, alignment=Qt.AlignCenter)
        
        self.vBoxLayout.addSpacing(80)
        
        # Cards Layout
        self.cards_layout = QHBoxLayout()
        self.cards_layout.setSpacing(25)
        self.cards_layout.setAlignment(Qt.AlignCenter)
        
        # 1. Today's Events Card
        self.events_card, self.ev_list_layout = self.create_card("TODAY'S EVENTS", 320)
        self.ev_list_layout.setContentsMargins(20, 20, 20, 20)
        self.ev_list_layout.setAlignment(Qt.AlignTop | Qt.AlignCenter)
        self.cards_layout.addWidget(self.events_card)
        
        # 2. Recent Studies Card
        self.recent_card, self.recent_list_layout = self.create_card("RECENTLY WORKED ON", 320)
        self.recent_list_layout.setContentsMargins(20, 20, 20, 20)
        self.recent_list_layout.setAlignment(Qt.AlignTop | Qt.AlignCenter)
        self.cards_layout.addWidget(self.recent_card)
        
        # 3. Library Pulse Card (Stats)
        self.stats_card, self.stats_list_layout = self.create_card("LIBRARY PULSE", 320)
        self.stats_list_layout.setContentsMargins(20, 20, 20, 20)
        self.stats_list_layout.setAlignment(Qt.AlignTop | Qt.AlignCenter)
        self.cards_layout.addWidget(self.stats_card)
        
        self.vBoxLayout.addLayout(self.cards_layout)
        
        # Clock Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_clock)
        self.timer.start(1000)
        self.update_clock()

    def create_card(self, title, width):
        card = CardWidget(self.view)
        card.setFixedWidth(width)
        card.setFixedHeight(250)
        card.setStyleSheet("""
            CardWidget {
                background: rgba(0, 0, 0, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 12px;
            }
        """)
        # We'll use this layout to add the header then the sub-widgets
        v = QVBoxLayout(card)
        v.setAlignment(Qt.AlignTop)
        hdr = StrongBodyLabel(title)
        hdr.setStyleSheet("color: rgba(255, 255, 255, 0.4); font-size: 10px; letter-spacing: 1px;")
        v.addWidget(hdr, alignment=Qt.AlignCenter)
        v.addSpacing(15)
        return card, v
        
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
        self.refresh_recent_studies()
        self.refresh_library_pulse()

    def _clear_layout(self, layout):
        if not layout:
            return
        while layout.count() > 2: # Keep title and spacing
            item = layout.takeAt(2)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # Recursive clear for nested layouts
                self._clear_layout_recursive(item.layout())
                
    def _clear_layout_recursive(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout_recursive(item.layout())

    def refresh_today_events(self):
        layout = self.events_card.layout()
        self._clear_layout(layout)
                
        today = QDate.currentDate().toString("yyyy-MM-dd")
        events = get_events_for_date(today)
        
        if not events:
            lbl = BodyLabel("No tasks for today. Stay focused!")
            lbl.setStyleSheet("color: #666; font-style: italic; font-size: 13px;")
            layout.addWidget(lbl, alignment=Qt.AlignCenter)
        else:
            for ev in events:
                elbl = BodyLabel(ev['title'])
                elbl.setStyleSheet("color: white; font-size: 15px; font-weight: 500;")
                layout.addWidget(elbl, alignment=Qt.AlignCenter)

    def refresh_recent_studies(self):
        layout = self.recent_card.layout()
        self._clear_layout(layout)
            
        recent = get_recent_files(5)
        if not recent:
            lbl = BodyLabel("Your journey starts here.")
            lbl.setStyleSheet("color: #666; font-style: italic; font-size: 13px;")
            layout.addWidget(lbl, alignment=Qt.AlignCenter)
            return

        for r in recent:
            basename = os.path.basename(r['path'])
            name, _ = split_filename_for_display(basename)
            rlbl = BodyLabel(name)
            rlbl.setStyleSheet("color: #ddd; font-size: 13px;")
            layout.addWidget(rlbl, alignment=Qt.AlignCenter)

    def refresh_library_pulse(self):
        layout = self.stats_card.layout()
        self._clear_layout(layout)
            
        stats = get_library_stats()
        
        st_layout = QVBoxLayout()
        st_layout.setSpacing(10)
        
        def add_stat(icon, text, val):
            h = QHBoxLayout()
            h.setAlignment(Qt.AlignCenter)
            i = IconWidget(icon)
            i.setFixedSize(16, 16)
            h.addWidget(i)
            l = BodyLabel(f"{text}: {val}")
            l.setStyleSheet("color: #ccc; font-size: 14px;")
            h.addWidget(l)
            st_layout.addLayout(h)
            
        add_stat(FIF.FOLDER, "Courses", stats['course_count'])
        add_stat(FIF.EDIT, "Notes", stats['notei_count'])
        add_stat(FIF.DOCUMENT, "Total Assets", stats['total_files'])
        
        layout.addLayout(st_layout)
