import os
import subprocess
import datetime
import re

from PySide6.QtCore import Qt, QUrl, Signal, QTimer, QDateTime, QDate, QThread
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPixmap
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                               QInputDialog, QFileDialog, QLabel, QStackedWidget, QListWidgetItem)

from qfluentwidgets import (ScrollArea, TitleLabel, SubtitleLabel, PrimaryPushButton, PushButton,
                            StrongBodyLabel, CardWidget, IconWidget, FluentIcon as FIF, SearchLineEdit,
                            InfoBar, InfoBarPosition, SegmentedWidget, BodyLabel, MessageBoxBase, LineEdit,
                            RoundMenu, Action, MenuAnimationType, MessageBox, ComboBox, Pivot, ListWidget,
                            TransparentPushButton, CaptionLabel)

from core.database import (get_all_courses, get_connection, insert_file, 
                           check_duplicate_hash, delete_file_by_path, mark_as_deleted, 
                           restore_file_by_path, get_events_for_date)
from core.importer import process_file_import, VAULT_DIR, get_file_hash, split_filename_for_display
from gui.components.marquee_label import MarqueeLabel
from gui.zen_writer import ZenWriter


import urllib.request
import json

class MiniClockCard(CardWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(50)
        self.setStyleSheet("CardWidget { background: rgba(0, 0, 0, 0.4); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 8px; }")
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 0, 10, 0)
        self.layout.setAlignment(Qt.AlignCenter)
        
        self.clock_lbl = StrongBodyLabel("00:00:00")
        self.clock_lbl.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        self.layout.addWidget(self.clock_lbl, alignment=Qt.AlignCenter)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_clock)
        self.timer.start(1000)
        self.update_clock()
        
    def update_clock(self):
        self.clock_lbl.setText(QDateTime.currentDateTime().toString("HH:mm:ss a"))

class MiniEventsCard(CardWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(120)
        self.setStyleSheet("CardWidget { background: rgba(0, 0, 0, 0.4); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 8px; }")
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(5)
        
        hdr = CaptionLabel("TODAY'S TASKS")
        hdr.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-weight: bold; letter-spacing: 1px;")
        self.layout.addWidget(hdr)
        
        self.scroll = ScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 5, 0, 5)
        self.content_layout.setSpacing(4)
        self.content_layout.setAlignment(Qt.AlignTop)
        
        self.scroll.setWidget(self.content_widget)
        self.layout.addWidget(self.scroll)
        
        self.load_events()
        
    def load_events(self):
        try:
            today_str = QDate.currentDate().toString("yyyy-MM-dd")
            events = get_events_for_date(today_str)
            if not events:
                l = CaptionLabel("No tasks today.")
                l.setStyleSheet("color: #777;")
                self.content_layout.addWidget(l)
            else:
                for ev in events:
                    l = BodyLabel("• " + ev.get('title', ''))
                    l.setStyleSheet("color: #ddd; font-size: 11px;")
                    l.setWordWrap(True)
                    self.content_layout.addWidget(l)
        except Exception:
            pass

class MiniMusicCard(CardWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(85)
        self.setStyleSheet("CardWidget { background: rgba(0, 0, 0, 0.4); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 8px; }")
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 5, 10, 5)
        self.layout.setSpacing(2)
        
        self.marquee = MarqueeLabel("Now Playing: None")
        self.marquee.setFixedWidth(150)
        self.marquee.setStyleSheet("color: #00ffaa; font-weight: bold; font-size: 11px;")
        self.layout.addWidget(self.marquee, alignment=Qt.AlignCenter)
        
        controls = QHBoxLayout()
        controls.setAlignment(Qt.AlignCenter)
        controls.setSpacing(10)
        
        self.btn_prev = TransparentPushButton(FIF.SKIP_BACK, "")
        self.btn_prev.setFixedSize(30,30)
        self.btn_play = TransparentPushButton(FIF.PLAY, "")
        self.btn_play.setFixedSize(30,30)
        self.btn_next = TransparentPushButton(FIF.SKIP_FORWARD, "")
        self.btn_next.setFixedSize(30,30)
        
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
            self.marquee.setText("Music Hub stopped")

class WeatherWorker(QThread):
    finished = Signal(str, str)
    
    def run(self):
        try:
            req = urllib.request.Request(
                "https://wttr.in/Bulawayo?format=j1",
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read().decode())
                current = data['current_condition'][0]
                temp = current['temp_C'] + "°C"
                desc = current['weatherDesc'][0]['value']
                self.finished.emit(temp, desc)
        except Exception:
            self.finished.emit("--°C", "Error")

class MiniWeatherCard(CardWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(65)
        self.setStyleSheet("CardWidget { background: rgba(0, 0, 0, 0.4); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 8px; }")
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(15, 5, 15, 5)
        
        self.icon_widget = IconWidget(FIF.CLOUD)
        self.icon_widget.setFixedSize(24, 24)
        self.icon_widget.setStyleSheet("color: #3498DB;")
        self.layout.addWidget(self.icon_widget)
        
        info = QVBoxLayout()
        info.setSpacing(0)
        self.temp_lbl = StrongBodyLabel("--°C")
        self.temp_lbl.setStyleSheet("color: white; font-size: 14px;")
        self.desc_lbl = CaptionLabel("Loading...")
        self.desc_lbl.setStyleSheet("color: #aaa; font-size: 10px;")
        info.addWidget(self.temp_lbl)
        info.addWidget(self.desc_lbl)
        
        self.layout.addLayout(info)
        self.layout.addStretch()
        
        self.worker = WeatherWorker()
        self.worker.finished.connect(self.update_weather)
        self.worker.start()
        
    def update_weather(self, temp, desc):
        self.temp_lbl.setText(temp)
        self.desc_lbl.setText(desc[:15] + ("..." if len(desc) > 15 else ""))
        
        d = desc.lower()
        if "sunny" in d or "clear" in d:
            self.icon_widget.setIcon(FIF.BRIGHTNESS)
            self.icon_widget.setStyleSheet("color: #F1C40F;")
        elif "rain" in d or "drizzle" in d or "shower" in d:
            self.icon_widget.setIcon(FIF.CLOUD)
            self.icon_widget.setStyleSheet("color: #4A90E2;")
        else:
            self.icon_widget.setIcon(FIF.CLOUD)
            self.icon_widget.setStyleSheet("color: #BDC3C7;")

def get_files_for_course(course: str):
    conn = get_connection()
    cursor = conn.cursor()
    if course == "all":
        cursor.execute("""
            SELECT * FROM files 
            WHERE deleted_at IS NULL 
            ORDER BY created_at DESC
        """)
    else:
        cursor.execute("""
            SELECT * FROM files 
            WHERE course = ? AND deleted_at IS NULL 
            ORDER BY created_at DESC
        """, (course,))
    res = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return res

class VaultFileCard(CardWidget):
    deleted = Signal()
    
    def __init__(self, file_data, parent=None):
        super().__init__(parent)
        self.file_data = file_data
        self.file_path = file_data['path']
        self.category = file_data['category']
        self.text_content = file_data.get('text_content', '')
        
        self.setFixedHeight(85)
        self.setCursor(Qt.PointingHandCursor)
        
        self.setStyleSheet("""
            VaultFileCard {
                background: rgba(255, 255, 255, 0.03) !important;
                border: 1px solid rgba(255, 255, 255, 0.06) !important;
                border-radius: 12px;
            }
            VaultFileCard:hover {
                background: rgba(255, 255, 255, 0.08) !important;
                border: 1px solid rgba(255, 255, 255, 0.2) !important;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(15)
        
        # Small Preview Box
        self.preview_box = QWidget()
        self.preview_box.setFixedSize(60, 60)
        self.preview_box.setStyleSheet("background: rgba(0, 0, 0, 0.35); border-radius: 8px;")
        p_layout = QVBoxLayout(self.preview_box)
        p_layout.setContentsMargins(0, 0, 0, 0)
        
        if self.category == 'Images':
            img_lbl = QLabel()
            img_lbl.setAlignment(Qt.AlignCenter)
            try:
                pm = QPixmap(self.file_path)
                if not pm.isNull():
                    img_lbl.setPixmap(pm.scaled(60, 60, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
                else:
                    img_lbl.setText("IMG")
            except:
                pass
            p_layout.addWidget(img_lbl)
        else:
            # Text based preview
            p_layout.setContentsMargins(6, 6, 6, 6)
            text_preview_lbl = BodyLabel()
            text_preview_lbl.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 9px; line-height: 1.2; background: transparent;")
            text_preview_lbl.setWordWrap(True)
            text_preview_lbl.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            
            preview_text = self.text_content.strip() if self.text_content else ""
            
            if not preview_text and self.file_path.endswith(('.md', '.txt', '.csv')):
                try:
                    with open(self.file_path, 'r', encoding='utf-8') as f:
                        preview_text = f.read(500).strip()
                except Exception:
                    pass
            
            if not preview_text:
                preview_text = "No preview"
                
            preview_text = re.sub(r'\s+', ' ', preview_text)
            text_preview_lbl.setText(preview_text[:60] + ("..." if len(preview_text) > 60 else ""))
            p_layout.addWidget(text_preview_lbl)
            
        layout.addWidget(self.preview_box)
        
        info_v = QVBoxLayout()
        info_v.setSpacing(2)
        
        basename = os.path.basename(self.file_path)
        display_name, suffix = split_filename_for_display(basename)
        
        self.title_lbl = MarqueeLabel(display_name)
        self.title_lbl.setFixedWidth(220)
        self.title_lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: white; background: transparent;")
        
        self.subtitle_lbl = CaptionLabel(f"{self.category} • {suffix if suffix else 'File'}")
        self.subtitle_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.35);")
        
        info_v.addWidget(self.title_lbl)
        info_v.addWidget(self.subtitle_lbl)
        layout.addLayout(info_v)
        layout.addStretch(1)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == Qt.LeftButton:
            p = self.parent()
            while p and not hasattr(p, 'display_file'):
                p = p.parent()
            if p: p.display_file(self.file_data)
            
    def mouseDoubleClickEvent(self, event):
        try:
            subprocess.Popen(['xdg-open', self.file_path])
        except Exception as e:
            print(f"Error opening file: {e}")

    def contextMenuEvent(self, event):
        menu = RoundMenu(parent=self)
        
        open_folder_action = Action(FIF.FOLDER, "Open Folder")
        open_folder_action.triggered.connect(self.open_folder)
        menu.addAction(open_folder_action)
        
        delete_action = Action(FIF.DELETE, "Move to Recycle Bin", self)
        delete_action.triggered.connect(self.request_bin)
        menu.addAction(delete_action)
        
        menu.exec(event.globalPos(), aniType=MenuAnimationType.DROP_DOWN)

    def request_bin(self):
        title = "Move to Recycle Bin"
        content = f"Move '{os.path.basename(self.file_path)}' to the Recycle Bin? It will be permanently deleted after 30 days."
        w = MessageBox(title, content, self.window())
        if w.exec():
            mark_as_deleted(self.file_path)
            self.deleted.emit()

    def open_folder(self):
        folder = os.path.dirname(self.file_path)
        if os.path.exists(folder):
            try:
                subprocess.Popen(['xdg-open', folder])
            except Exception as e:
                print(f"Error opening folder: {e}")

class VaultInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("VaultInterface")
        self.setStyleSheet("background: transparent;")
        self.setAcceptDrops(True)
        self._is_updating = False
        
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # --- 1. COURSE SIDEBAR (Left) ---
        self.course_sidebar = QWidget()
        self.course_sidebar.setFixedWidth(220)
        self.course_sidebar.setStyleSheet("background: rgba(0, 0, 0, 0.45) !important; border-right: 1px solid rgba(255,255,255,0.03);")
        sidebar_layout = QVBoxLayout(self.course_sidebar)
        sidebar_layout.setContentsMargins(15, 30, 15, 15)
        
        cat_lbl = CaptionLabel("STUDY HUB")
        cat_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.3); font-weight: bold; padding-left: 10px;")
        sidebar_layout.addWidget(cat_lbl)
        
        self.course_list = ListWidget()
        self.course_list.setStyleSheet("background: transparent; border: none;")
        self.course_list.currentItemChanged.connect(self.on_course_selected)
        sidebar_layout.addWidget(self.course_list)
        
        sidebar_layout.addSpacing(10)
        
        self.mini_dashboard = QVBoxLayout()
        self.mini_dashboard.setSpacing(10)
        self.mini_clock = MiniClockCard()
        self.mini_events = MiniEventsCard()
        self.mini_music = MiniMusicCard()
        self.mini_weather = MiniWeatherCard()
        
        self.mini_dashboard.addWidget(self.mini_clock)
        self.mini_dashboard.addWidget(self.mini_events)
        self.mini_dashboard.addWidget(self.mini_music)
        self.mini_dashboard.addWidget(self.mini_weather)
        sidebar_layout.addLayout(self.mini_dashboard)
        
        sidebar_layout.addStretch(1)
        self.btn_new_course = TransparentPushButton(FIF.ADD, "New Course")
        self.btn_new_course.clicked.connect(self.add_new_course)
        sidebar_layout.addWidget(self.btn_new_course)
        self.main_layout.addWidget(self.course_sidebar)
        
        # --- 2. FILES BROWSER (Middle) ---
        self.files_browser = QWidget()
        self.files_browser.setFixedWidth(400)
        self.files_browser.setStyleSheet("background: rgba(255, 255, 255, 0.01);")
        browser_layout = QVBoxLayout(self.files_browser)
        browser_layout.setContentsMargins(25, 25, 25, 25)
        browser_layout.setSpacing(20)
        
        self.header = SubtitleLabel("My Vault")
        self.header.setStyleSheet("font-size: 28px; font-weight: 900; color: white;")
        browser_layout.addWidget(self.header)
        
        search_layout = QHBoxLayout()
        self.search_bar = SearchLineEdit()
        self.search_bar.setPlaceholderText("Filter files...")
        self.search_bar.textChanged.connect(lambda: self.filter_files())
        search_layout.addWidget(self.search_bar)
        
        self.btn_import = TransparentPushButton(FIF.DOWNLOAD, "")
        self.btn_import.setToolTip("Import PDF/Files")
        self.btn_import.clicked.connect(self.import_files_dialog)
        search_layout.addWidget(self.btn_import)
        browser_layout.addLayout(search_layout)
        
        # Action Buttons specific to Vault
        actions_layout = QHBoxLayout()
        self.btn_new_note = PushButton(FIF.EDIT, "Take Note")
        self.btn_new_note.clicked.connect(self.take_note)
        actions_layout.addWidget(self.btn_new_note)
        
        self.btn_ingracia = PrimaryPushButton(FIF.PEOPLE, "Ask Ingracia")
        self.btn_ingracia.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #8a2be2, stop:1 #ffd700); color: white;")
        self.btn_ingracia.clicked.connect(self.launch_ingracia_with_context)
        actions_layout.addWidget(self.btn_ingracia)
        browser_layout.addLayout(actions_layout)

        pivot_h = QHBoxLayout()
        self.pivot = Pivot()
        self.pivot.addItem("all", "All")
        self.pivot.addItem("PDFs", "PDFs")
        self.pivot.addItem("Notes", "Notes")
        self.pivot.addItem("Images", "Images")
        self.pivot.addItem("Slides", "Slides")
        self.pivot.setCurrentItem("all")
        self.pivot.currentItemChanged.connect(lambda: self.filter_files())
        pivot_h.addWidget(self.pivot)
        pivot_h.addStretch(1)
        browser_layout.addLayout(pivot_h)
        
        self.scroll_area = ScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")
        self.scroll_widget = QWidget()
        self.files_layout = QVBoxLayout(self.scroll_widget)
        self.files_layout.setAlignment(Qt.AlignTop)
        self.files_layout.setContentsMargins(0, 0, 10, 0)
        self.files_layout.setSpacing(12)
        self.scroll_area.setWidget(self.scroll_widget)
        browser_layout.addWidget(self.scroll_area)
        self.main_layout.addWidget(self.files_browser)
        
        # --- 3. VIEWER / EDITOR STACK (Right) ---
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("background: rgba(0,0,0,0.1);")
        
        # Page 0: Empty
        self.empty_page = QWidget()
        empty_layout = QVBoxLayout(self.empty_page)
        empty_layout.setAlignment(Qt.AlignCenter)
        self.empty_icon = IconWidget(FIF.FOLDER)
        self.empty_icon.setFixedSize(100, 100)
        self.empty_icon.setStyleSheet("color: rgba(255, 255, 255, 0.05);")
        empty_layout.addWidget(self.empty_icon)
        self.content_stack.addWidget(self.empty_page)
        
        # Page 1: File Info Viewer (PDFs/Images)
        self.viewer_page = QWidget()
        viewer_layout = QVBoxLayout(self.viewer_page)
        viewer_layout.setContentsMargins(50, 50, 50, 50)
        
        v_header = QHBoxLayout()
        v_header.setSpacing(20)
        title_v = QVBoxLayout()
        self.v_title = MarqueeLabel("File Title", self)
        self.v_title.setFixedHeight(45)
        self.v_title.setStyleSheet("font-size: 28px; font-weight: bold; color: white;")
        
        self.v_info = CaptionLabel("Info")
        title_v.addWidget(self.v_title)
        title_v.addWidget(self.v_info)
        v_header.addLayout(title_v)
        v_header.addStretch(1)
        self.btn_open_external = PrimaryPushButton(FIF.DOCUMENT, "Open Externally")
        self.btn_open_external.clicked.connect(self.open_current_external)
        v_header.addWidget(self.btn_open_external)
        viewer_layout.addLayout(v_header)
        
        # Big Preview area
        self.v_big_preview = QWidget()
        self.v_big_preview_layout = QVBoxLayout(self.v_big_preview)
        self.v_big_preview.setStyleSheet("background: rgba(0, 0, 0, 0.2); border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.05);")
        viewer_layout.addWidget(self.v_big_preview, 1)
        self.content_stack.addWidget(self.viewer_page)
        
        # Page 2: Zen Writer (Notes)
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
        
        self.main_layout.addWidget(self.content_stack, 1)
        
        self.all_courses_list = []
        self.current_files = []
        self.selected_file_data = None
        self.current_zen_editor = None
        
        self.load_courses()

    def clear_big_preview(self):
        while self.v_big_preview_layout.count():
            item = self.v_big_preview_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def load_courses(self):
        courses = [c for c in get_all_courses() if c != "Notei"]
        if not courses:
            courses = ["Inbox"]
            
        self.course_list.clear()
        
        all_item = QListWidgetItem("🌍 All Library")
        all_item.setData(Qt.UserRole, "all")
        self.course_list.addItem(all_item)
        
        for course in courses:
            item = QListWidgetItem(f"📚 {course}")
            item.setData(Qt.UserRole, course)
            self.course_list.addItem(item)
            
        self.course_list.setCurrentRow(0)

    def current_course(self):
        item = self.course_list.currentItem()
        if not item: return "Inbox"
        c = item.data(Qt.UserRole)
        # return "all" or specific course
        return c

    def on_course_selected(self, current, previous):
        if not current or self._is_updating: return
        cid = current.data(Qt.UserRole)
        
        name = current.text().split(' ')[1] if ' ' in current.text() else current.text()
        if cid == "all":
            name = "All Library"
            
        self.header.setText(name)
        
        # Load files for course
        self.current_files = get_files_for_course(cid)
        self.filter_files()
        self.content_stack.setCurrentIndex(0) # Reset to empty page

    def filter_files(self):
        if self._is_updating: return
        query = self.search_bar.text().lower()
        cat = (self.pivot.currentRouteKey() or "all")
        
        filtered = []
        for f in self.current_files:
            file_name_match = query in os.path.basename(f['path']).lower()
            cat_match = (cat == "all" or f['category'] == cat)
            if file_name_match and cat_match:
                filtered.append(f)
                
        self.refresh_list(filtered)

    def refresh_list(self, files):
        if self._is_updating: return
        self._is_updating = True
        try:
            while self.files_layout.count():
                item = self.files_layout.takeAt(0)
                if item is not None:
                    widget = item.widget()
                    if widget is not None:
                        widget.setParent(None)
                        widget.deleteLater()
                        
            if not files:
                empty = SubtitleLabel("No files found.", self)
                empty.setStyleSheet("color: #777; margin-top: 20px;")
                empty.setAlignment(Qt.AlignCenter)
                self.files_layout.addWidget(empty)
            else:
                for f in files:
                    card = VaultFileCard(f, self.scroll_widget)
                    card.deleted.connect(self.reload_current_course)
                    self.files_layout.addWidget(card)
        finally:
            self._is_updating = False

    def reload_current_course(self):
        cid = self.current_course()
        self.current_files = get_files_for_course(cid)
        self.filter_files()

    def display_file(self, file_data):
        self.selected_file_data = file_data
        cat = file_data['category']
        file_path = file_data['path']
        
        self.content_stack.setCurrentIndex(1)
        basename = os.path.basename(file_path)
        display_name, suffix = split_filename_for_display(basename)
        self.v_title.setText(display_name)
        self.v_info.setText(f"{cat} • {suffix if suffix else 'File'} • {file_data.get('created_at', '')[:10]}")
        
        self.clear_big_preview()
        
        if cat == 'Notes' or cat == 'Text' or file_path.endswith(('.md', '.txt', '.csv')):
            from qfluentwidgets import TextBrowser
            
            text_content = file_data.get('text_content', '')
            if not text_content.strip():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        text_content = f.read()
                except Exception as e:
                    text_content = f"Could not read local file:\n{e}"
            
            viewer = TextBrowser()
            viewer.setStyleSheet("background: transparent; border: none; font-size: 15px; color: #eee; padding: 20px; line-height: 1.6;")
            
            if file_path.endswith('.md'):
                viewer.setMarkdown(text_content)
            else:
                viewer.setPlainText(text_content)
                
            self.v_big_preview_layout.addWidget(viewer)
            
        elif cat == 'Images':
            img_lbl = QLabel()
            img_lbl.setAlignment(Qt.AlignCenter)
            pm = QPixmap(file_path)
            if not pm.isNull():
                img_lbl.setPixmap(pm.scaled(600, 600, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                img_lbl.setText("Image Corrupted")
                img_lbl.setStyleSheet("color: #888; font-size: 18px;")
            self.v_big_preview_layout.addWidget(img_lbl)
            
        else:
            # Just show generic message or partial text
            msg_lbl = QLabel()
            content = file_data.get('text_content', 'No full preview available inside app. Open externally.')
            if not content.strip():
                content = "Double click the file or click Open Externally to view."
            
            msg_lbl.setText(f"Preview:\n\n{content[:800]}...")
            msg_lbl.setStyleSheet("color: #aaa; font-size: 14px; padding: 20px; text-align: center;")
            msg_lbl.setAlignment(Qt.AlignCenter)
            msg_lbl.setWordWrap(True)
            self.v_big_preview_layout.addWidget(msg_lbl)

    def open_current_external(self):
        if self.selected_file_data:
            try:
                subprocess.Popen(['xdg-open', self.selected_file_data['path']])
            except Exception as e:
                print(f"Error opening file externally: {e}")

    def close_zen_editor(self):
        self.content_stack.setCurrentIndex(1)
        self.reload_current_course()

    def add_new_course(self):
        name, ok = QInputDialog.getText(self, "Create New Course", "Enter the new course name:")
        if ok and name.strip():
            new_course = name.strip()
            item = QListWidgetItem(f"📚 {new_course}")
            item.setData(Qt.UserRole, new_course)
            self.course_list.addItem(item)
            self.course_list.setCurrentItem(item)

    def take_note(self):
        cid = self.current_course()
        if cid == "all": return
        
        # Present in Editor Page
        self.content_stack.setCurrentIndex(2)
        while self.zen_container.count():
            item = self.zen_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        self.current_zen_editor = ZenWriter(cid)
        self.current_zen_editor.saveCompleted.connect(self.reload_current_course)
        self.zen_container.addWidget(self.current_zen_editor)

    def showEvent(self, event):
        super().showEvent(event)
        self.reload_current_course()

    def import_files_dialog(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Select Files to Import", "", "All Files (*)")
        if file_paths:
            self._execute_import(file_paths)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.search_bar.setPlaceholderText("Drop files to instantly import!")

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        file_paths = [url.toLocalFile() for url in urls if os.path.isfile(url.toLocalFile())]
        self.search_bar.setPlaceholderText("Filter files...")
        self._execute_import(file_paths)
        
    def _execute_import(self, file_paths):
        target_course = self.current_course()
        if target_course == "all": target_course = "Inbox"
        
        imported_count = 0
        skipped_count = 0
        
        for file_path in file_paths:
            res = process_file_import(file_path, target_course, check_duplicate_callback=check_duplicate_hash)
            if res['status'] == 'success':
                insert_file(
                    path=res['vault_path'],
                    file_hash=res['file_hash'],
                    course=res['course'],
                    category=res['category'],
                    text_content=res['extracted_text']
                )
                imported_count += 1
            elif res['status'] == 'skipped':
                skipped_count += 1
        
        msg = f"Successfully imported {imported_count} documents."
        if skipped_count:
            msg += f" (Skipped {skipped_count} identical duplicates)"
            
        self.reload_current_course()
        
        if imported_count > 0 or skipped_count > 0:
            InfoBar.success(
                title='Import Completed',
                content=msg,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=3500,
                parent=self
            )

    def launch_ingracia_with_context(self):
        course = self.current_course()
        if course == "all": course = "Inbox"
        
        files = self.current_files
        recent_files = files[:8]
        
        metadata_lines = [f"METADATA_REASONING_MODE: {course}"]
        for n in recent_files:
            filename = os.path.basename(n['path'])
            date_str = n.get('created_at', 'Unknown Date')
            metadata_lines.append(f"- File: {filename} (Modified: {date_str})")
        
        metadata_block = "\n".join(metadata_lines)
        
        from gui.components.ingracia_chat_view import IngraciaChatView
        self.chat_overlay = IngraciaChatView(course_name=course, context_text=metadata_block, parent=self.window())
        self.chat_overlay.closed.connect(self.chat_overlay.close)
        self.chat_overlay.resize(500, 750)
        
        geo = self.window().geometry()
        self.chat_overlay.move(geo.center() - self.chat_overlay.rect().center())
        self.chat_overlay.show()
