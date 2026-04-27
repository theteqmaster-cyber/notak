import os
import datetime
from PySide6.QtCore import Qt, QTimer, Signal, QDateTime, QDate
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QFrame
from qfluentwidgets import (ScrollArea, TitleLabel, SubtitleLabel, TransparentPushButton, SearchLineEdit,
                            StrongBodyLabel, CardWidget, IconWidget, FluentIcon as FIF, BodyLabel, CaptionLabel)
from gui.components.marquee_label import MarqueeLabel

from core.database import get_events_for_date, get_recent_files, get_library_stats
from core.importer import split_filename_for_display
from core.gemma_service import GemmaService

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

        # Top Action Area
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
        
        self.btn_gemma = TransparentPushButton(FIF.CHAT, "Ask Gemma", self.view)
        self.btn_gemma.setFixedSize(160, 40)
        self.btn_gemma.clicked.connect(self.open_gemma_chat)
        self.btn_gemma.setStyleSheet(self.btn_inspiration.styleSheet())
        self.top_actions.addWidget(self.btn_gemma)
        
        self.btn_ingracia = TransparentPushButton(FIF.PEOPLE, "Ask Ingracia", self.view)
        self.btn_ingracia.setFixedSize(160, 40)
        self.btn_ingracia.clicked.connect(self.open_ingracia_chat)
        self.btn_ingracia.setStyleSheet(self.btn_inspiration.styleSheet())
        self.top_actions.addWidget(self.btn_ingracia)
        
        self.top_actions.addStretch()
        
        from gui.interfaces.vault_interface import MiniWeatherCard, MiniMusicCard
        self.weather_card = MiniWeatherCard(self.view)
        self.weather_card.setFixedWidth(200)
        self.top_actions.addWidget(self.weather_card)
        
        self.vBoxLayout.addLayout(self.top_actions)

        self.vBoxLayout.addSpacing(70)
        
        # Clock Section
        self.clock_label = TitleLabel("", self.view)
        self.clock_label.setAlignment(Qt.AlignCenter)
        font = self.clock_label.font()
        font.setPointSize(68)
        font.setBold(True)
        self.clock_label.setFont(font)
        self.clock_label.setStyleSheet("color: white; font-weight: bold;")
        self.vBoxLayout.addWidget(self.clock_label)
        
        self.date_label = SubtitleLabel("", self.view)
        self.date_label.setAlignment(Qt.AlignCenter)
        self.vBoxLayout.addWidget(self.date_label)
        
        self.vBoxLayout.addSpacing(10)
        self.music_card = MiniMusicCard(self.view)
        self.music_card.setFixedWidth(300)
        # Make the background transparent so it looks seamless under the clock
        self.music_card.setStyleSheet("CardWidget { background: transparent; border: none; }")
        self.vBoxLayout.addWidget(self.music_card, alignment=Qt.AlignCenter)
        
        self.vBoxLayout.addSpacing(30)
        
        # Search Bar
        self.hero_search = SearchLineEdit(self.view)
        self.hero_search.setPlaceholderText("Quick search your entire library...")
        self.hero_search.setFixedWidth(600)
        self.hero_search.searchButton.clicked.connect(lambda: self.searchRequested.emit(self.hero_search.text()))
        self.hero_search.returnPressed.connect(lambda: self.searchRequested.emit(self.hero_search.text()))
        self.vBoxLayout.addWidget(self.hero_search, alignment=Qt.AlignCenter)
        self.vBoxLayout.addSpacing(40)
        
        # --- AI HERO CARD (Motivational) SIDE-BY-SIDE ---
        self.ai_card = CardWidget(self.view)
        self.ai_card.setFixedWidth(850)
        self.ai_card.setMinimumHeight(200)
        self.ai_card.setStyleSheet("""
            CardWidget { 
                background: rgba(255, 255, 255, 0.04); 
                border: 1px solid rgba(255, 255, 255, 0.1); 
                border-radius: 20px; 
            }
        """)
        ai_main_layout = QHBoxLayout(self.ai_card)
        ai_main_layout.setContentsMargins(40, 35, 40, 35)
        ai_main_layout.setSpacing(0)
        
        # Left Side (Tip)
        self.tip_container = QWidget()
        tip_v = QVBoxLayout(self.tip_container)
        tip_v.setContentsMargins(0, 0, 20, 0)
        tip_v.setSpacing(8)
        
        tip_header_h = QHBoxLayout()
        tip_header_h.setSpacing(8)
        tip_icon = IconWidget(FIF.EXPRESSIVE_INPUT_ENTRY)
        tip_icon.setFixedSize(14, 14)
        tip_icon.setStyleSheet("color: #00ffaa;")
        self.tip_hdr = CaptionLabel("STUDY TIP")
        self.tip_hdr.setStyleSheet("color: #00ffaa; font-weight: bold; font-size: 9px; letter-spacing: 1.5px;")
        tip_header_h.addWidget(tip_icon)
        tip_header_h.addWidget(self.tip_hdr)
        tip_header_h.addStretch()
        
        self.tip_lbl = BodyLabel("Thinking...")
        self.tip_lbl.setWordWrap(True)
        self.tip_lbl.setStyleSheet("color: white; font-size: 14px; font-weight: 500;")
        
        tip_v.addLayout(tip_header_h)
        tip_v.addWidget(self.tip_lbl)
        tip_v.addStretch()
        
        # Vertical Divider
        self.divider = QFrame()
        self.divider.setFixedWidth(1)
        self.divider.setStyleSheet("background-color: rgba(255, 255, 255, 0.1);")
        
        # Right Side (Quote)
        self.quote_container = QWidget()
        quote_v = QVBoxLayout(self.quote_container)
        quote_v.setContentsMargins(20, 0, 0, 0)
        quote_v.setSpacing(8)
        
        quote_header_h = QHBoxLayout()
        quote_header_h.setSpacing(8)
        quote_icon = IconWidget(FIF.CHAT)
        quote_icon.setFixedSize(14, 14)
        quote_icon.setStyleSheet("color: #ffaa00;")
        self.quote_hdr = CaptionLabel("INSPIRATION")
        self.quote_hdr.setStyleSheet("color: #ffaa00; font-weight: bold; font-size: 9px; letter-spacing: 1.5px;")
        quote_header_h.addWidget(quote_icon)
        quote_header_h.addWidget(self.quote_hdr)
        quote_header_h.addStretch()
        
        self.quote_lbl = BodyLabel("...")
        self.quote_lbl.setWordWrap(True)
        self.quote_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 13px; font-style: italic;")
        
        quote_v.addLayout(quote_header_h)
        quote_v.addWidget(self.quote_lbl)
        quote_v.addStretch()
        
        ai_main_layout.addWidget(self.tip_container, 6)
        ai_main_layout.addWidget(self.divider)
        ai_main_layout.addWidget(self.quote_container, 4)
        
        # MAKE CARD CLICKABLE FOR RETRY
        self.ai_card.setCursor(Qt.PointingHandCursor)
        self.ai_card.mousePressEvent = lambda e: self.update_ai_recommendation(force=True)
        
        self.vBoxLayout.addWidget(self.ai_card, alignment=Qt.AlignCenter)
        self.vBoxLayout.addSpacing(70)
        
        # Bottom Grid (Events, Studies, Stats)
        self.cards_layout = QHBoxLayout()
        self.cards_layout.setSpacing(25)
        self.cards_layout.setAlignment(Qt.AlignCenter)
        
        self.events_card, self.ev_list_layout = self.create_card("TODAY'S TASKS", 320)
        self.cards_layout.addWidget(self.events_card)
        self.recent_card, self.recent_list_layout = self.create_card("RECENT WORK", 320)
        self.cards_layout.addWidget(self.recent_card)
        self.stats_card, self.stats_list_layout = self.create_card("LIBRARY PULSE", 320)
        self.cards_layout.addWidget(self.stats_card)
        
        self.vBoxLayout.addLayout(self.cards_layout)

        # Internal State
        self._recommendation_raw = ""
        self._ai_generated = False
        
        # Timers
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_clock)
        self.timer.start(1000)
        
        # AIR GAP Polling Timer
        self.polling_timer = QTimer(self)
        self.polling_timer.timeout.connect(self._sync_ai_buffer)
        
        self.update_clock()

    def create_card(self, title, width):
        card = CardWidget(self.view)
        card.setFixedWidth(width)
        card.setFixedHeight(250)
        card.setStyleSheet("CardWidget { background: rgba(0, 0, 0, 0.7); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; }")
        v = QVBoxLayout(card)
        v.setAlignment(Qt.AlignTop)
        v.setContentsMargins(20, 20, 20, 20)
        hdr = StrongBodyLabel(title)
        hdr.setStyleSheet("color: rgba(255, 255, 255, 0.3); font-size: 10px; letter-spacing: 1.5px;")
        v.addWidget(hdr, alignment=Qt.AlignCenter)
        v.addSpacing(15)
        return card, v

    def update_clock(self):
        now = QDateTime.currentDateTime()
        self.clock_label.setText(now.toString("HH:mm:ss"))
        self.date_label.setText(now.toString("dddd, MMMM d, yyyy"))

    def import_inspiration(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Inspiration", "", "Images (*.png *.jpg *.jpeg)")
        if file_path: self.backgroundChanged.emit(file_path)

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_today_events()
        self.refresh_recent_studies()
        self.refresh_library_pulse()
        if not self._ai_generated:
            self.update_ai_recommendation()

    def update_ai_recommendation(self, force=False):
        if self._ai_generated and not force:
            return
            
        self._recommendation_raw = ""
        self.tip_lbl.setText("Computing your study plan...")
        self.quote_lbl.setText("...")
        
        service = GemmaService()
        prompt = service.get_recommendation_prompt(get_library_stats(), get_recent_files(3))
        thread, worker = service.get_chat_thread(prompt, "You are a brief assistant.")
        
        self._ai_worker = worker
        self._ai_thread = thread
        self._ai_generated = True
        self.polling_timer.start(50)
        thread.start()

    def _sync_ai_buffer(self):
        if not hasattr(self, '_ai_worker') or not self._ai_worker: return
        
        # Check for errors (Sync logic with Chat)
        if self._ai_worker.error_msg:
            self.polling_timer.stop()
            self.tip_lbl.setText("⚠️ AI currently unavailable.")
            self.quote_lbl.setText("Check Ollama status and click here to retry.")
            self._ai_generated = False # Allow retry
            return

        while self._ai_worker.output_buffer:
            chunk = self._ai_worker.output_buffer.pop(0)
            self._recommendation_raw += chunk
            
        # ROBUST PARSING: Search for keywords instead of relying on '|'
        raw = self._recommendation_raw.replace("**", "").replace("*", "")
        
        tip_start = raw.find("Tip:")
        quote_start = raw.find("Quote:")
        
        if tip_start != -1 and quote_start != -1:
            if tip_start < quote_start:
                tip = raw[tip_start+4:quote_start].strip().rstrip("|").strip()
                quote = raw[quote_start+6:].strip()
            else:
                quote = raw[quote_start+6:tip_start].strip().rstrip("|").strip()
                tip = raw[tip_start+4:].strip()
                
            self.tip_lbl.setText(tip)
            self.quote_lbl.setText(quote)
        elif tip_start != -1:
            self.tip_lbl.setText(raw[tip_start+4:].strip())
        elif quote_start != -1:
            self.quote_lbl.setText(raw[quote_start+6:].strip())
        else:
            self.tip_lbl.setText(raw.strip())
            
        # Ensure UI updates to fit new text
        self.tip_lbl.adjustSize()
        self.quote_lbl.adjustSize()
        self.ai_card.adjustSize()
            
        if self._ai_worker.is_done and not self._ai_worker.output_buffer:
            self.polling_timer.stop()
            self._ai_thread.quit()
            self._ai_thread.wait()
            self._ai_thread = None
            self._ai_worker = None

    def open_gemma_chat(self):
        from gui.components.gemma_chat_view import GemmaChatView
        self.chat_overlay = GemmaChatView(parent=self.window())
        self.chat_overlay.closed.connect(self.chat_overlay.close)
        self.chat_overlay.resize(500, 750)
        geo = self.window().geometry()
        self.chat_overlay.move(geo.center() - self.chat_overlay.rect().center())
        self.chat_overlay.show()

    def open_ingracia_chat(self):
        from gui.components.ingracia_chat_view import IngraciaChatView
        self.chat_overlay = IngraciaChatView(parent=self.window())
        self.chat_overlay.closed.connect(self.chat_overlay.close)
        self.chat_overlay.resize(500, 750)
        geo = self.window().geometry()
        self.chat_overlay.move(geo.center() - self.chat_overlay.rect().center())
        self.chat_overlay.show()

    def _clear_layout(self, layout):
        while layout.count() > 2: 
            item = layout.takeAt(2)
            if item.widget(): item.widget().deleteLater()

    def refresh_today_events(self):
        layout = self.events_card.layout()
        self._clear_layout(layout)
        events = get_events_for_date(QDate.currentDate().toString("yyyy-MM-dd"))
        if not events:
            lbl = BodyLabel("No tasks today.")
            lbl.setStyleSheet("color: #555; font-size: 13px;")
            layout.addWidget(lbl, alignment=Qt.AlignCenter)
        else:
            for ev in events:
                l = BodyLabel(ev['title'])
                l.setStyleSheet("color: white; font-size: 14px;")
                layout.addWidget(l, alignment=Qt.AlignCenter)

    def refresh_recent_studies(self):
        layout = self.recent_card.layout()
        self._clear_layout(layout)
        recent = get_recent_files(5)
        if not recent:
            layout.addWidget(BodyLabel("No recent work."), alignment=Qt.AlignCenter)
        else:
            for r in recent:
                name, _ = split_filename_for_display(os.path.basename(r['path']))
                l = MarqueeLabel(name)
                l.setStyleSheet("color: #ccc; font-size: 13px;")
                layout.addWidget(l)

    def refresh_library_pulse(self):
        layout = self.stats_card.layout()
        self._clear_layout(layout)
        stats = get_library_stats()
        v = QVBoxLayout()
        v.setSpacing(10)
        def add(icon, txt, val):
            h = QHBoxLayout()
            h.setAlignment(Qt.AlignCenter)
            h.addWidget(IconWidget(icon))
            h.addWidget(BodyLabel(f"{txt}: {val}"))
            v.addLayout(h)
        add(FIF.FOLDER, "Courses", stats['course_count'])
        add(FIF.EDIT, "Notes", stats['notei_count'])
        layout.addLayout(v)
