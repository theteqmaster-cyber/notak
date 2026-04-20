from PySide6.QtCore import Qt, QSize, Signal, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QStackedWidget, QListWidgetItem
from qfluentwidgets import (SubtitleLabel, BodyLabel, CaptionLabel, SearchLineEdit, 
                            Pivot, FluentIcon as FIF, TransparentPushButton, PrimaryPushButton,
                            ListWidget, CardWidget, IconWidget, StrongBodyLabel, TextBrowser,
                            ScrollArea, InfoBar, InfoBarPosition)

from core.supabase_service import SupabaseService
from gui.components.login_view import LoginView
from gui.zen_writer import ZenWriter
from gui.components.marquee_label import MarqueeLabel
from gui.components.gemma_chat_view import GemmaChatView
import datetime
import re

class NoteCard(CardWidget):
    def __init__(self, note_data, parent=None):
        super().__init__(parent)
        self.note_data = note_data
        self.setFixedHeight(85)
        self.setCursor(Qt.PointingHandCursor)
        
        self.setStyleSheet("""
            NoteCard {
                background: rgba(255, 255, 255, 0.03) !important;
                border: 1px solid rgba(255, 255, 255, 0.06) !important;
                border-radius: 12px;
            }
            NoteCard:hover {
                background: rgba(255, 255, 255, 0.08) !important;
                border: 1px solid rgba(255, 255, 255, 0.2) !important;
            }
        """)
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(15, 12, 15, 12)
        self.layout.setSpacing(15)
        
        type_str = (note_data.get('type') or 'lecture').lower()
        color = "#0078d7"
        icon = FIF.EDIT
        if 'assignment' in type_str: 
            icon = FIF.COMPLETED
            color = "#d83b01"
        elif 'key' in type_str: 
            icon = FIF.CAFE
            color = "#107c10"
        
        self.icon_bg = QWidget()
        self.icon_bg.setFixedSize(40, 40)
        self.icon_bg.setStyleSheet(f"background: {color}22; border-radius: 8px;")
        icon_layout = QVBoxLayout(self.icon_bg)
        icon_layout.setContentsMargins(8, 8, 8, 8)
        self.icon_widget = IconWidget(icon)
        self.icon_widget.setStyleSheet(f"color: {color};")
        icon_layout.addWidget(self.icon_widget)
        self.layout.addWidget(self.icon_bg)
        
        info_v = QVBoxLayout()
        info_v.setSpacing(2)
        
        self.title_lbl = MarqueeLabel(note_data.get('title', 'Untitled Note'))
        self.title_lbl.setFixedWidth(240)
        self.title_lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: white; background: transparent;")
        
        self.subtitle_lbl = CaptionLabel(f"{note_data.get('type', 'lecture')} • {note_data.get('created_at', '')[:10]}")
        self.subtitle_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.35);")
        info_v.addWidget(self.title_lbl)
        info_v.addWidget(self.subtitle_lbl)
        self.layout.addLayout(info_v)
        
        self.layout.addStretch(1)

    def update_data(self, note_data):
        self.note_data = note_data
        self.title_lbl.setText(note_data.get('title', 'Untitled Note'))
        self.subtitle_lbl.setText(f"{note_data.get('type', 'lecture')} • {note_data.get('created_at', '')[:10]}")

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        p = self.parent()
        while p and not hasattr(p, 'display_note'):
            p = p.parent()
        if p: p.display_note(self.note_data)

class MiniTimetableCard(CardWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(140)
        self.setStyleSheet("CardWidget { background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 12px; }")
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 12, 15, 12)
        self.layout.setSpacing(8)
        
        hdr = QHBoxLayout()
        icon = IconWidget(FIF.CALENDAR)
        icon.setFixedSize(14, 14)
        icon.setStyleSheet("color: #00ffaa;")
        title = CaptionLabel("TODAY'S CLASSES")
        title.setStyleSheet("color: #00ffaa; font-weight: bold; letter-spacing: 1px;")
        hdr.addWidget(icon)
        hdr.addWidget(title)
        hdr.addStretch()
        self.layout.addLayout(hdr)
        
        self.scroll = ScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(5)
        self.content_layout.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.content_widget)
        self.layout.addWidget(self.scroll)
        
    def set_data(self, classes):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        if not classes:
            lbl = CaptionLabel("No classes today.")
            lbl.setStyleSheet("color: rgba(255, 255, 255, 0.3);")
            self.content_layout.addWidget(lbl)
        else:
            for c in classes:
                item_v = QVBoxLayout()
                item_v.setSpacing(0)
                name = BodyLabel(c.get('title', 'Unknown'))
                name.setStyleSheet("color: white; font-size: 13px; font-weight: bold;")
                time = CaptionLabel(f"{c.get('start_time', '')} - {c.get('end_time', '')}")
                time.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-size: 11px;")
                item_v.addWidget(name)
                item_v.addWidget(time)
                self.content_layout.addLayout(item_v)

class MiniEventsCard(CardWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(120)
        self.setStyleSheet("CardWidget { background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 12px; }")
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 12, 15, 12)
        self.layout.setSpacing(8)
        
        hdr = QHBoxLayout()
        icon = IconWidget(FIF.COMPLETED)
        icon.setFixedSize(14, 14)
        icon.setStyleSheet("color: #ffaa00;")
        title = CaptionLabel("CALENDAR EVENTS")
        title.setStyleSheet("color: #ffaa00; font-weight: bold; letter-spacing: 1px;")
        hdr.addWidget(icon)
        hdr.addWidget(title)
        hdr.addStretch()
        self.layout.addLayout(hdr)
        
        self.scroll = ScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(5)
        self.content_layout.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.content_widget)
        self.layout.addWidget(self.scroll)
        
    def set_data(self, events):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        if not events:
            lbl = CaptionLabel("No events today.")
            lbl.setStyleSheet("color: rgba(255, 255, 255, 0.3);")
            self.content_layout.addWidget(lbl)
        else:
            for ev in events:
                l = BodyLabel(f"• {ev.get('title', 'Event')}")
                l.setStyleSheet("color: #ddd; font-size: 12px;")
                l.setWordWrap(True)
                self.content_layout.addWidget(l)

class MiniMusicCard(CardWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(120)
        self.setStyleSheet("CardWidget { background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 12px; }")
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 12, 15, 12)
        self.layout.setSpacing(8)
        
        hdr = QHBoxLayout()
        icon = IconWidget(FIF.MUSIC)
        icon.setFixedSize(14, 14)
        icon.setStyleSheet("color: #00ffaa;")
        title = CaptionLabel("NOW PLAYING")
        title.setStyleSheet("color: #00ffaa; font-weight: bold; letter-spacing: 1px;")
        hdr.addWidget(icon)
        hdr.addWidget(title)
        hdr.addStretch()
        self.layout.addLayout(hdr)
        
        self.marquee = MarqueeLabel("No Track Selected")
        self.marquee.setStyleSheet("color: white; font-weight: bold; font-size: 13px;")
        self.layout.addWidget(self.marquee)
        
        controls = QHBoxLayout()
        controls.setAlignment(Qt.AlignCenter)
        controls.setSpacing(15)
        
        self.btn_prev = TransparentPushButton(FIF.SKIP_BACK, "")
        self.btn_prev.setFixedSize(32, 32)
        self.btn_play = TransparentPushButton(FIF.PLAY, "")
        self.btn_play.setFixedSize(32, 32)
        self.btn_next = TransparentPushButton(FIF.SKIP_FORWARD, "")
        self.btn_next.setFixedSize(32, 32)
        
        controls.addWidget(self.btn_prev)
        controls.addWidget(self.btn_play)
        controls.addWidget(self.btn_next)
        self.layout.addLayout(controls)
        
        self.btn_prev.clicked.connect(self._prev)
        self.btn_next.clicked.connect(self._next)
        self.btn_play.clicked.connect(self._toggle_play)
        
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.sync_state)
        self.update_timer.start(1000)

    def get_music_interface(self):
        w = self.window()
        if hasattr(w, 'musicInterface'): return w.musicInterface
        return None

    def _prev(self):
        mi = self.get_music_interface()
        if mi: mi.play_previous()

    def _next(self):
        mi = self.get_music_interface()
        if mi: mi.play_next_manual()

    def _toggle_play(self):
        mi = self.get_music_interface()
        if mi:
            from PySide6.QtMultimedia import QMediaPlayer
            if mi.player.playbackState() == QMediaPlayer.PlayingState:
                mi.player.pause()
            else:
                mi.player.play()

    def sync_state(self):
        mi = self.get_music_interface()
        if not mi: return
        
        from PySide6.QtMultimedia import QMediaPlayer
        state = mi.player.playbackState()
        
        if state == QMediaPlayer.PlayingState:
            self.btn_play.setIcon(FIF.PAUSE)
        else:
            self.btn_play.setIcon(FIF.PLAY)
            
        if hasattr(mi.track_name_label, 'text_content'):
            song_lbl = mi.track_name_label.text_content
        else:
            song_lbl = "No Track Selected"
            
        if song_lbl and song_lbl != "No Track Selected":
            self.marquee.setText(song_lbl)
        else:
            self.marquee.setText("Hub Stopped")

class HydraSpaceInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("HydraSpaceInterface")
        self.supabase = SupabaseService()
        self._is_updating = False
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.stacked_widget = QStackedWidget(self)
        self.main_layout.addWidget(self.stacked_widget)
        
        self.login_view = LoginView(self)
        self.login_view.login_success.connect(self.on_login_success)
        self.stacked_widget.addWidget(self.login_view)
        
        self.dashboard = QWidget()
        self.dashboard.setStyleSheet("background: transparent;")
        dash_layout = QHBoxLayout(self.dashboard)
        dash_layout.setContentsMargins(0, 0, 0, 0)
        dash_layout.setSpacing(0)
        
        self.course_sidebar = QWidget()
        self.course_sidebar.setFixedWidth(220)
        self.course_sidebar.setStyleSheet("background: rgba(0, 0, 0, 0.45) !important; border-right: 1px solid rgba(255,255,255,0.03);")
        sidebar_layout = QVBoxLayout(self.course_sidebar)
        sidebar_layout.setContentsMargins(15, 30, 15, 15)
        
        cat_lbl = CaptionLabel("HYDRASPACE")
        cat_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.3); font-weight: bold; padding-left: 10px;")
        sidebar_layout.addWidget(cat_lbl)
        
        self.course_list = ListWidget()
        self.course_list.setStyleSheet("background: transparent; border: none;")
        self.course_list.currentItemChanged.connect(self.on_course_selected)
        sidebar_layout.addWidget(self.course_list)
        
        sidebar_layout.addSpacing(20)
        
        self.timetable_card = MiniTimetableCard()
        self.events_card = MiniEventsCard()
        self.music_card = MiniMusicCard()
        sidebar_layout.addWidget(self.timetable_card)
        sidebar_layout.addWidget(self.events_card)
        sidebar_layout.addWidget(self.music_card)
        
        sidebar_layout.addStretch(1)
        self.btn_logout = TransparentPushButton(FIF.CLOSE, "Sign Out")
        self.btn_logout.clicked.connect(self.handle_logout)
        sidebar_layout.addWidget(self.btn_logout)
        dash_layout.addWidget(self.course_sidebar)
        
        self.notes_browser = QWidget()
        self.notes_browser.setFixedWidth(400)
        self.notes_browser.setStyleSheet("background: rgba(255, 255, 255, 0.01);")
        browser_layout = QVBoxLayout(self.notes_browser)
        browser_layout.setContentsMargins(25, 25, 25, 25)
        browser_layout.setSpacing(20)
        
        self.header = SubtitleLabel("Cloud Notes")
        self.header.setStyleSheet("font-size: 28px; font-weight: 900; color: white;")
        browser_layout.addWidget(self.header)
        
        self.search_bar = SearchLineEdit()
        self.search_bar.setPlaceholderText("Search notes...")
        self.search_bar.textChanged.connect(self.filter_notes)
        browser_layout.addWidget(self.search_bar)
        
        # New Tool Row: Take Note, Ask Ingracia, Ask Gemma
        tool_row = QHBoxLayout()
        tool_row.setSpacing(8)
        
        button_style = """
            TransparentPushButton {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 5px 10px;
                font-size: 11px;
                font-weight: 600;
                color: rgba(255, 255, 255, 0.8);
            }
            TransparentPushButton:hover {
                background: rgba(255, 255, 255, 0.12);
                border: 1px solid rgba(255, 255, 255, 0.3);
                color: white;
            }
        """
        
        self.btn_new_note = TransparentPushButton(FIF.ADD, "Note")
        self.btn_new_note.setStyleSheet(button_style)
        self.btn_new_note.clicked.connect(self.handle_new_note)
        
        self.btn_ask_ingracia = TransparentPushButton(FIF.PEOPLE, "Ingracia")
        self.btn_ask_ingracia.setStyleSheet(button_style.replace("0.1);", "0.2); border-color: rgba(138, 43, 226, 0.3);"))
        self.btn_ask_ingracia.clicked.connect(self.launch_ingracia_chat)
        
        self.btn_ask_gemma = TransparentPushButton(FIF.CHAT, "Gemma")
        self.btn_ask_gemma.setStyleSheet(button_style)
        self.btn_ask_gemma.clicked.connect(self.open_course_gemma_chat)
        
        tool_row.addWidget(self.btn_new_note)
        tool_row.addWidget(self.btn_ask_ingracia)
        tool_row.addWidget(self.btn_ask_gemma)
        browser_layout.addLayout(tool_row)
        
        # Pivot Row (Below Tools)
        pivot_h = QHBoxLayout()
        self.pivot = Pivot()
        self.pivot.addItem("all", "All")
        self.pivot.addItem("lecture", "Lectures")
        self.pivot.addItem("assignment", "Assignments")
        self.pivot.addItem("key concept", "Key Concepts")
        self.pivot.setCurrentItem("all")
        self.pivot.currentItemChanged.connect(lambda: self.filter_notes())
        
        # Style pivot to be smaller
        self.pivot.setStyleSheet("""
            Pivot { background: transparent; }
            PivotItem { font-size: 11px; padding: 5px 10px; }
        """)
        
        pivot_h.addWidget(self.pivot)
        pivot_h.addStretch(1)
        browser_layout.addLayout(pivot_h)
        
        self.scroll_area = ScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")
        self.scroll_widget = QWidget()
        self.notes_layout = QVBoxLayout(self.scroll_widget)
        self.notes_layout.setAlignment(Qt.AlignTop)
        self.notes_layout.setContentsMargins(0, 0, 10, 0)
        self.notes_layout.setSpacing(12)
        self.scroll_area.setWidget(self.scroll_widget)
        browser_layout.addWidget(self.scroll_area)
        dash_layout.addWidget(self.notes_browser)
        
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("background: rgba(0,0,0,0.1);")
        
        self.empty_page = CardWidget()
        self.empty_page.setStyleSheet("background: transparent; border: none;")
        empty_layout = QVBoxLayout(self.empty_page)
        empty_layout.setAlignment(Qt.AlignCenter)
        self.empty_icon = IconWidget(FIF.GLOBE)
        self.empty_icon.setFixedSize(100, 100)
        self.empty_icon.setStyleSheet("color: rgba(255, 255, 255, 0.05);")
        empty_layout.addWidget(self.empty_icon)
        self.content_stack.addWidget(self.empty_page)
        
        self.viewer_page = QWidget()
        viewer_layout = QVBoxLayout(self.viewer_page)
        viewer_layout.setContentsMargins(50, 50, 50, 50)
        
        v_header = QHBoxLayout()
        v_header.setSpacing(20)
        title_v = QVBoxLayout()
        self.v_title = MarqueeLabel("Note Title", self)
        self.v_title.setFixedHeight(45)
        self.v_title.setStyleSheet("font-size: 28px; font-weight: bold; color: white;")
        
        self.v_info = CaptionLabel("Info")
        title_v.addWidget(self.v_title)
        title_v.addWidget(self.v_info)
        v_header.addLayout(title_v)
        v_header.addStretch(1)
        self.btn_edit_zen = PrimaryPushButton(FIF.EDIT, "Zen Mode")
        self.btn_edit_zen.clicked.connect(self.open_zen_editor)
        v_header.addWidget(self.btn_edit_zen)
        viewer_layout.addLayout(v_header)
        
        self.note_viewer = TextBrowser()
        self.note_viewer.setReadOnly(True)
        self.note_viewer.setStyleSheet("background: transparent; border: none; font-size: 18px; color: #e0e0e0;")
        viewer_layout.addWidget(self.note_viewer)
        self.content_stack.addWidget(self.viewer_page)
        
        self.editor_page = QWidget()
        editor_layout = QVBoxLayout(self.editor_page)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        self.zen_container = QVBoxLayout()
        
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(30,30,30,0)
        self.btn_close_editor = TransparentPushButton(FIF.LEFT_ARROW, "Back to Library")
        self.btn_close_editor.clicked.connect(self.close_zen_editor)
        top_bar.addWidget(self.btn_close_editor)
        top_bar.addStretch(1)
        editor_layout.addLayout(top_bar)
        editor_layout.addLayout(self.zen_container)
        self.content_stack.addWidget(self.editor_page)
        
        dash_layout.addWidget(self.content_stack, 1)
        self.stacked_widget.addWidget(self.dashboard)
        
        self.all_courses = []
        self.current_notes = []
        self.selected_note = None
        self.current_zen_editor = None
        
        if self.supabase.is_authenticated():
            self.stacked_widget.setCurrentIndex(1)
            # Defer loading to showEvent to avoid blocking main window startup
        else:
            self.stacked_widget.setCurrentIndex(0)

    def on_login_success(self):
        self.stacked_widget.setCurrentIndex(1)
        self.load_initial_data()
        self.refresh_sidebar_data()

    def refresh_sidebar_data(self):
        """Update timetable and events in the sidebar."""
        classes = self.supabase.get_timetable()
        self.timetable_card.set_data(classes)
        
        events = self.supabase.get_calendar_events()
        self.events_card.set_data(events)

    def handle_logout(self):
        self.supabase.sign_out()
        self.stacked_widget.setCurrentIndex(0)

    def load_initial_data(self):
        self.refresh_sidebar_data()
        self.all_courses = self.supabase.get_courses()
        self.course_list.clear()
        all_item = QListWidgetItem("🌍 All Library")
        all_item.setData(Qt.UserRole, "all")
        self.course_list.addItem(all_item)
        for course in self.all_courses:
            item = QListWidgetItem(f"📚 {course.get('name')}")
            item.setData(Qt.UserRole, course.get('id'))
            self.course_list.addItem(item)
        self.course_list.setCurrentRow(0)

    def on_course_selected(self, current, previous):
        if not current or self._is_updating: return
        cid = current.data(Qt.UserRole)
        name = current.text().split(' ')[1] if ' ' in current.text() else current.text()
        self.header.setText(name)
        self.current_notes = self.supabase.get_all_notes() if cid == "all" else self.supabase.get_notes_for_course(cid)
        self.filter_notes()

    def display_note(self, note):
        if self.content_stack.currentIndex() == 2: return
        self.selected_note = note
        self.content_stack.setCurrentIndex(1)
        self.v_title.setText(note.get('title'))
        self.v_info.setText(f"{note.get('type')} • {note.get('created_at', '')[:10]}")
        html = f"<div style='color: #eee; line-height: 1.8; padding: 20px;'>{note.get('content', 'No content.')}</div>"
        self.note_viewer.setHtml(html)

    def open_zen_editor(self):
        if not self.selected_note: return
        self.content_stack.setCurrentIndex(2)
        while self.zen_container.count():
            item = self.zen_container.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        
        self.current_zen_editor = ZenWriter(cloud_data=self.selected_note)
        # BIND THE REAL-TIME PATCHER
        self.current_zen_editor.saveCompleted.connect(self.handle_cloud_save)
        self.zen_container.addWidget(self.current_zen_editor)

    def handle_cloud_save(self, note_data):
        # Update local selected note state
        self.selected_note = note_data
        
        # Real-time viewer patch
        self.v_title.setText(note_data.get('title'))
        html = f"<div style='color: #eee; line-height: 1.8; padding: 20px;'>{note_data.get('content', 'No content.')}</div>"
        self.note_viewer.setHtml(html)
        
        # Patch the note item in the list browser without full reload
        for i in range(self.notes_layout.count()):
            widget = self.notes_layout.itemAt(i).widget()
            if isinstance(widget, NoteCard) and widget.note_data.get('id') == note_data.get('id'):
                widget.update_data(note_data)
                break

    def close_zen_editor(self):
        self.content_stack.setCurrentIndex(1)
        # No full reload needed anymore due to live patching!

    def handle_new_note(self):
        cid = self.course_list.currentItem().data(Qt.UserRole)
        if cid == "all": return
        ctype = (self.pivot.currentRouteKey() or "lecture").lower()
        if ctype == "all": ctype = "lecture"
        new_note = self.supabase.create_note("New Fragment", cid, ctype)
        if new_note:
            # Bug Fix: Ensure new note is tracked locally
            self.current_notes.insert(0, new_note)
            self.filter_notes()
            
            self.selected_note = new_note
            self.open_zen_editor()

    def launch_ingracia_chat(self):
        """Standalone Ingracia launch for cloud course context."""
        current_course = self.course_list.currentItem()
        if not current_course: return
        course_name = current_course.text().split('📚 ')[-1]
        
        context_parts = []
        for note in self.current_notes[:3]:
            title = note.get('title', 'Untitled')
            # Rudimentary HTML strip
            clean_content = re.sub('<[^<]+?>', '', note.get('content', ''))
            context_parts.append(f"### {title}\n{clean_content[:500]}")
        
        from gui.components.ingracia_chat_view import IngraciaChatView
        self.chat_overlay = IngraciaChatView(
            course_name=course_name, 
            context_text="\n\n".join(context_parts),
            parent=self.window()
        )
        self.chat_overlay.resize(500, 750)
        geo = self.window().geometry()
        self.chat_overlay.move(geo.center() - self.chat_overlay.rect().center())
        self.chat_overlay.show()

    def open_course_gemma_chat(self):
        current_course = self.course_list.currentItem()
        if not current_course: return
        
        course_name = current_course.text()
        if "📚" in course_name: course_name = course_name.split("📚")[1].strip()
        
        # Gather context from RECENT notes (strictly the top 3 most recent to keep it focused)
        sorted_notes = sorted(self.current_notes, key=lambda x: x.get('created_at', ''), reverse=True)
        
        context_parts = []
        for note in sorted_notes[:3]:
            title = note.get('title', 'Untitled')
            content = note.get('content', '')
            # Strip HTML to get clean markdown/text content
            import re
            clean_content = re.sub('<[^<]+?>', '', content)
            # Take only the first 800 characters of each note to avoid overwhelming the model
            context_parts.append(f"### Note: {title}\n{clean_content[:800]}...")
        
        context_text = "\n\n".join(context_parts)
        
        self.chat_overlay = GemmaChatView(course_name=course_name, context_text=context_text, parent=self.window())
        self.chat_overlay.resize(500, 700)
        self.chat_overlay.closed.connect(self.chat_overlay.close)
        
        # Center on screen
        geo = self.window().geometry()
        self.chat_overlay.move(geo.center() - self.chat_overlay.rect().center())
        self.chat_overlay.show()

    def filter_notes(self):
        if self._is_updating: return
        query = self.search_bar.text().lower()
        cat = (self.pivot.currentRouteKey() or "all").lower()
        filtered = [n for n in self.current_notes if (query in n.get('title', '').lower()) and (cat == "all" or cat == (n.get('type') or '').lower())]
        self.refresh_list(filtered)

    def refresh_list(self, notes):
        if self._is_updating: return
        self._is_updating = True
        try:
            while self.notes_layout.count():
                item = self.notes_layout.takeAt(0)
                if item is not None:
                    widget = item.widget()
                    if widget is not None:
                        widget.setParent(None)
                        widget.deleteLater()
            for note in notes:
                card = NoteCard(note, self.scroll_widget)
                self.notes_layout.addWidget(card)
        finally:
            self._is_updating = False

    def showEvent(self, event):
        super().showEvent(event)
        # Only load if we haven't already or if we are authenticated
        if self.supabase.is_authenticated():
            # Use singleShot to ensure the UI is rendered before heavy fetching starts
            QTimer.singleShot(100, self.load_initial_data)
