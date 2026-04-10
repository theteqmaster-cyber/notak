from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QStackedWidget, QListWidgetItem
from qfluentwidgets import (SubtitleLabel, BodyLabel, CaptionLabel, SearchLineEdit, 
                            Pivot, FluentIcon as FIF, TransparentPushButton, PrimaryPushButton,
                            ListWidget, CardWidget, IconWidget, StrongBodyLabel, TextBrowser,
                            ScrollArea, InfoBar, InfoBarPosition)

from core.supabase_service import SupabaseService
from gui.components.login_view import LoginView
from gui.zen_writer import ZenWriter
from gui.components.marquee_label import MarqueeLabel

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
        self.search_bar.textChanged.connect(lambda: self.filter_notes())
        browser_layout.addWidget(self.search_bar)
        
        pivot_h = QHBoxLayout()
        self.pivot = Pivot()
        self.pivot.addItem("all", "All")
        self.pivot.addItem("lecture", "Lectures")
        self.pivot.addItem("assignment", "Assignments")
        self.pivot.addItem("key concept", "Key Concepts")
        self.pivot.setCurrentItem("all")
        self.pivot.currentItemChanged.connect(lambda: self.filter_notes())
        pivot_h.addWidget(self.pivot)
        pivot_h.addStretch(1)
        
        self.btn_new_note = TransparentPushButton(FIF.ADD, "")
        self.btn_new_note.clicked.connect(self.handle_new_note)
        pivot_h.addWidget(self.btn_new_note)
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
            self.load_initial_data()
        else:
            self.stacked_widget.setCurrentIndex(0)

    def on_login_success(self):
        self.stacked_widget.setCurrentIndex(1)
        self.load_initial_data()

    def handle_logout(self):
        self.supabase.sign_out()
        self.stacked_widget.setCurrentIndex(0)

    def load_initial_data(self):
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
            self.selected_note = new_note
            self.open_zen_editor()

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
        if self.supabase.is_authenticated() and not self.all_courses:
            self.load_initial_data()
