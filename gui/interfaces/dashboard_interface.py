import os
import datetime
from PySide6.QtCore import Qt, QSize, Signal, QTimer
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QGridLayout)
from PySide6.QtGui import QFont, QPixmap

from qfluentwidgets import (ScrollArea, TransparentPushButton, FluentIcon as FIF,
                             CardWidget, IconWidget, SubtitleLabel, BodyLabel,
                             CaptionLabel, PrimaryPushButton, SearchLineEdit,
                             RoundMenu, Action)

from core.database import get_connection

class DashboardInterface(ScrollArea):
    backgroundChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("DashboardInterface")
        self.view = QWidget(self)
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.setStyleSheet("ScrollArea { background-color: transparent; border: none; }")
        self.view.setStyleSheet("QWidget { background-color: transparent; }")

        self.main_layout = QVBoxLayout(self.view)
        self.main_layout.setContentsMargins(40, 30, 40, 30)
        self.main_layout.setSpacing(0)

        # ── 1. TOP STAT PILLS ──────────────────────────────────────────────
        pills_row = QHBoxLayout()
        pills_row.addStretch(1)
        pills_row.setSpacing(10)
        self._add_pill(pills_row, "Notes", FIF.FOLDER)
        self._add_pill(pills_row, "Courses", FIF.EDUCATION)
        self._add_pill(pills_row, "Devices", FIF.IOT)
        self.main_layout.addLayout(pills_row)

        # ── 2. HERO SECTION ────────────────────────────────────────────────
        hero = QVBoxLayout()
        hero.setAlignment(Qt.AlignCenter)
        hero.setSpacing(6)
        hero.setContentsMargins(0, 40, 0, 30)

        hour = datetime.datetime.now().hour
        greetings = ["Good morning", "Good afternoon", "Good evening"]
        greeting = greetings[0] if hour < 12 else greetings[1] if hour < 18 else greetings[2]
        self.lbl_greeting = QLabel(f"{greeting}, Mphathisi")
        self.lbl_greeting.setAlignment(Qt.AlignCenter)
        self.lbl_greeting.setStyleSheet("font-size: 30px; font-weight: 800; color: white; background: transparent;")
        hero.addWidget(self.lbl_greeting)

        self.lbl_date = QLabel(datetime.datetime.now().strftime("%A, %B %d"))
        self.lbl_date.setAlignment(Qt.AlignCenter)
        self.lbl_date.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 13px; background: transparent;")
        hero.addWidget(self.lbl_date)

        self.main_layout.addLayout(hero)

        # ── 3. SEARCH BAR ──────────────────────────────────────────────────
        search_row = QHBoxLayout()
        search_row.setAlignment(Qt.AlignCenter)
        search_row.setContentsMargins(0, 0, 0, 40)

        self.search_bar = SearchLineEdit()
        self.search_bar.setPlaceholderText("Search notes, files, PDFs...")
        self.search_bar.setClearButtonEnabled(True)
        self.search_bar.setFixedWidth(480)
        self.search_bar.setFixedHeight(40)
        self.search_bar.setStyleSheet("""
            SearchLineEdit {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 20px;
                color: white;
                font-size: 14px;
                padding-left: 15px;
            }
            SearchLineEdit:focus {
                border: 1px solid rgba(128, 90, 213, 0.7);
                background: rgba(255, 255, 255, 0.12);
            }
        """)
        self.search_bar.textChanged.connect(lambda _: None)   # no live-redirect
        self.search_bar.returnPressed.connect(self._go_search)
        search_row.addLayout(search_row) if False else None  # skip – just add widget
        search_row.addWidget(self.search_bar)

        self.main_layout.addLayout(search_row)

        # ── 4. SPACER (pushes actions to the bottom) ───────────────────────
        self.main_layout.addStretch(1)

        # ── 5. BOTTOM ACTION CARDS ─────────────────────────────────────────
        actions_section = QVBoxLayout()
        actions_section.setSpacing(8)

        hint = CaptionLabel("Quick Actions")
        hint.setStyleSheet("color: rgba(255,255,255,0.3); letter-spacing: 1px;")
        hint.setAlignment(Qt.AlignCenter)
        actions_section.addWidget(hint)

        self.actions_layout = QHBoxLayout()
        self.actions_layout.setSpacing(12)

        self.btn_new_note = self._make_action_btn("New Note", FIF.EDIT)
        self.btn_search   = self._make_action_btn("Deep Search", FIF.SEARCH)
        self.btn_music    = self._make_action_btn("Music Hub", FIF.MUSIC)
        self.btn_calendar = self._make_action_btn("Calendar", FIF.CALENDAR)

        for b in [self.btn_new_note, self.btn_search, self.btn_music, self.btn_calendar]:
            self.actions_layout.addWidget(b)

        actions_section.addLayout(self.actions_layout)
        self.main_layout.addLayout(actions_section)
        self.main_layout.setContentsMargins(40, 30, 40, 30)

        # ── SIGNALS ────────────────────────────────────────────────────────
        self.btn_new_note.clicked.connect(lambda: self._nav("quickNoteInterface"))
        self.btn_search.clicked.connect(self._go_search)
        self.btn_music.clicked.connect(lambda: self._nav("musicInterface"))
        self.btn_calendar.clicked.connect(lambda: self._nav("calendarInterface"))

    # ── helpers ────────────────────────────────────────────────────────────

    def _add_pill(self, row, label, icon):
        pill = QFrame()
        pill.setFixedHeight(32)
        pill.setStyleSheet("""
            QFrame {
                background: rgba(128, 90, 213, 0.12);
                border: 1px solid rgba(128, 90, 213, 0.25);
                border-radius: 16px;
            }
        """)
        l = QHBoxLayout(pill)
        l.setContentsMargins(10, 0, 14, 0)
        l.setSpacing(6)
        iw = IconWidget(icon)
        iw.setFixedSize(14, 14)
        lbl = CaptionLabel(label)
        lbl.setStyleSheet("color: #c4b5fd; font-size: 11px;")
        l.addWidget(iw)
        l.addWidget(lbl)
        row.addWidget(pill)

    def _make_action_btn(self, title, icon):
        btn = TransparentPushButton(icon, title)
        btn.setFixedHeight(52)
        btn.setIconSize(QSize(18, 18))
        btn.setStyleSheet("""
            TransparentPushButton {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                color: white;
                font-size: 13px;
            }
            TransparentPushButton:hover {
                background: rgba(128, 90, 213, 0.2);
                border: 1px solid rgba(128, 90, 213, 0.4);
            }
        """)
        return btn

    def _on_search(self, text):
        """No-op: search only fires on Enter."""
        pass

    def _go_search(self):
        query = self.search_bar.text().strip()
        main_window = self.window()
        if hasattr(main_window, 'searchInterface'):
            main_window.stackedWidget.setCurrentWidget(main_window.searchInterface)
            if query:
                main_window.searchInterface.search_bar.setText(query)

    def _nav(self, interface_name):
        try:
            mw = self.window()
            mw.stackedWidget.setCurrentWidget(getattr(mw, interface_name))
        except Exception:
            pass

    def showEvent(self, event):
        super().showEvent(event)
        self.search_bar.clear()
