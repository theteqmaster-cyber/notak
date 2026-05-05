import os
from PySide6.QtCore import Qt, QSize, Signal, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QListWidget, QListWidgetItem, QLabel
from qfluentwidgets import (ScrollArea, TransparentPushButton, FluentIcon as FIF, PrimaryPushButton,
                            RoundMenu, Action, MenuAnimationType, CardWidget, IconWidget,
                            SubtitleLabel, BodyLabel, CaptionLabel, SearchLineEdit)
from gui.components.marquee_label import MarqueeLabel
from gui.components.session_graph import SessionGraphWidget
from gui.zen_writer import ZenWriter
from core.database import get_connection, get_session_history

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

        self.main_h_layout = QHBoxLayout(self.view)
        self.main_h_layout.setContentsMargins(30, 30, 30, 30)
        self.main_h_layout.setSpacing(30)

        # --- LEFT COLUMN: Academic Hub (Note Editor) ---
        self.left_col = QVBoxLayout()
        self.left_col.setSpacing(0)

        # Note Editor Header (Purple Area)
        self.editor_header = QFrame(self.view)
        self.editor_header.setFixedHeight(60)
        self.editor_header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6b46c1, stop:1 #805ad5);
                border-top-left-radius: 15px;
                border-top-right-radius: 15px;
            }
        """)
        header_layout = QHBoxLayout(self.editor_header)
        header_layout.setContentsMargins(15, 0, 15, 0)
        
        self.lbl_editor_title = BodyLabel("Note editor settings", self.editor_header)
        self.lbl_editor_title.setStyleSheet("color: white; font-weight: bold;")
        header_layout.addWidget(self.lbl_editor_title)
        
        header_layout.addStretch(1)
        
        # Vault Courses Button
        self.btn_vault_courses = TransparentPushButton(FIF.EDUCATION, "Study Vault", self.editor_header)
        self.btn_vault_courses.setStyleSheet("color: white;")
        self.btn_vault_courses.clicked.connect(lambda: self.show_course_menu(self.btn_vault_courses, "Study Vault"))
        header_layout.addWidget(self.btn_vault_courses)
        
        # Settings Button
        self.btn_settings = TransparentPushButton(FIF.SETTING, "", self.editor_header)
        self.btn_settings.setStyleSheet("color: white;")
        self.btn_settings.clicked.connect(self.show_settings_menu)
        header_layout.addWidget(self.btn_settings)
        
        # Open Button
        self.btn_open = TransparentPushButton(FIF.DOCUMENT, "Open", self.editor_header)
        self.btn_open.setStyleSheet("color: white;")
        self.btn_open.clicked.connect(self.show_open_menu)
        header_layout.addWidget(self.btn_open)

        # Close Button
        self.btn_close_note = TransparentPushButton(FIF.CLOSE, "Close", self.editor_header)
        self.btn_close_note.setStyleSheet("color: white;")
        self.btn_close_note.clicked.connect(self.close_note)
        header_layout.addWidget(self.btn_close_note)
        
        self.left_col.addWidget(self.editor_header)

        # Note Editor Body (Black Area)
        self.editor_body = QFrame(self.view)
        self.editor_body.setStyleSheet("""
            QFrame {
                background: rgba(0, 0, 0, 0.8);
                border-bottom-left-radius: 15px;
                border-bottom-right-radius: 15px;
            }
        """)
        body_layout = QVBoxLayout(self.editor_body)
        body_layout.setContentsMargins(10, 10, 10, 10)
        
        self.writer = ZenWriter()
        self.writer.status_label.setText("PENDING CONFIG")
        self.writer.status_label.setStyleSheet("color: #ffaa00; background: rgba(255, 170, 0, 0.1); padding: 4px 12px; border-radius: 10px;")
        self.writer.editor.setReadOnly(True)
        body_layout.addWidget(self.writer)
        
        self.left_col.addWidget(self.editor_body)
        self.main_h_layout.addLayout(self.left_col, 2)

        # --- RIGHT COLUMN: Utility Hub ---
        self.right_col = QVBoxLayout()
        self.right_col.setSpacing(20)

        # 1. Music Widget
        self.music_card = CardWidget(self.view)
        self.music_card.setFixedHeight(320)
        self.music_card.setStyleSheet("CardWidget { background: rgba(0, 0, 0, 0.6); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 15px; }")
        music_layout = QVBoxLayout(self.music_card)
        music_layout.setContentsMargins(20, 20, 20, 20)
        
        self.music_header = MarqueeLabel("No Track Playing")
        self.music_header.setFixedWidth(240)
        self.music_header.setStyleSheet("color: #a371f7; font-weight: bold; font-size: 13px;")
        music_layout.addWidget(self.music_header)
        
        self.marquee_song = MarqueeLabel("...")
        self.marquee_song.setFixedWidth(240)
        self.marquee_song.setFixedHeight(30)
        self.marquee_song.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        music_layout.addWidget(self.marquee_song)
        
        # Controls
        ctrl_h = QHBoxLayout()
        self.btn_prev = TransparentPushButton(FIF.SKIP_BACK, "", self.music_card)
        self.btn_play_pause = TransparentPushButton(FIF.PLAY, "", self.music_card)
        self.btn_next = TransparentPushButton(FIF.SKIP_FORWARD, "", self.music_card)
        
        self.btn_prev.clicked.connect(self.play_prev)
        self.btn_play_pause.clicked.connect(self.toggle_play)
        self.btn_next.clicked.connect(self.play_next)
        
        ctrl_h.addWidget(self.btn_prev)
        ctrl_h.addWidget(self.btn_play_pause)
        ctrl_h.addWidget(self.btn_next)
        music_layout.addLayout(ctrl_h)
        
        music_layout.addWidget(CaptionLabel("PLAYING QUEUE"))
        self.queue_list = QListWidget(self.music_card)
        self.queue_list.setStyleSheet("""
            QListWidget { background: transparent; border: none; color: #aaa; font-size: 12px; }
            QListWidget::item { padding: 4px; border-radius: 4px; }
            QListWidget::item:selected { background: rgba(163, 113, 247, 0.2); color: white; }
        """)
        self.queue_list.itemClicked.connect(self.play_queue_song)
        music_layout.addWidget(self.queue_list)
        
        self.right_col.addWidget(self.music_card)

        # 2. Shortcut Widget
        self.shortcut_card = QWidget(self.view)
        short_h = QHBoxLayout(self.shortcut_card)
        short_h.setContentsMargins(0, 0, 0, 0)
        short_h.setSpacing(15)
        
        self.btn_vault = CardWidget(self.shortcut_card)
        self.btn_vault.setFixedSize(140, 90)
        v_layout = QVBoxLayout(self.btn_vault)
        v_layout.addWidget(IconWidget(FIF.FOLDER), alignment=Qt.AlignCenter)
        v_layout.addWidget(CaptionLabel("Study Vault"), alignment=Qt.AlignCenter)
        self.btn_vault.setCursor(Qt.PointingHandCursor)
        self.btn_vault.mousePressEvent = lambda e: self.navigate_to('vaultInterface')
        
        self.btn_hydra = CardWidget(self.shortcut_card)
        self.btn_hydra.setFixedSize(140, 90)
        h_layout = QVBoxLayout(self.btn_hydra)
        h_layout.addWidget(IconWidget(FIF.IOT), alignment=Qt.AlignCenter) 
        h_layout.addWidget(CaptionLabel("Hydra Space"), alignment=Qt.AlignCenter)
        self.btn_hydra.setCursor(Qt.PointingHandCursor)
        self.btn_hydra.mousePressEvent = lambda e: self.navigate_to('hydraInterface')
        
        short_h.addWidget(self.btn_vault)
        short_h.addWidget(self.btn_hydra)
        self.right_col.addWidget(self.shortcut_card)

        # 3. Session Widget
        self.session_card = CardWidget(self.view)
        self.session_card.setStyleSheet("CardWidget { background: rgba(0, 0, 0, 0.4); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 15px; }")
        session_layout = QVBoxLayout(self.session_card)
        session_layout.setContentsMargins(20, 20, 20, 20)
        
        session_header = BodyLabel("Session graph")
        session_header.setStyleSheet("color: #aaa; font-weight: bold;")
        session_layout.addWidget(session_header)
        
        self.graph = SessionGraphWidget(self.session_card)
        session_layout.addWidget(self.graph)
        self.right_col.addWidget(self.session_card)

        self.main_h_layout.addLayout(self.right_col, 1)

        # Data initialization
        self.refresh_graph()
        QTimer.singleShot(1000, self.sync_music)

    def navigate_to(self, interface_name):
        try:
            main_window = self.window()
            target = getattr(main_window, interface_name)
            main_window.stackedWidget.setCurrentWidget(target)
        except: pass

    def show_course_menu(self, btn, location):
        menu = RoundMenu(parent=btn)
        from core.database import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        # Filter by course list (could be location based if needed, but for now global is fine)
        cursor.execute("SELECT DISTINCT course FROM files WHERE course != 'Uncategorized'")
        courses = [r[0] for r in cursor.fetchall()]
        conn.close()
        
        if not courses: courses = ["General"]
        
        for c in courses:
            action = Action(c, self)
            action.triggered.connect(lambda checked=False, course=c, loc=location, b=btn: self.set_course_config(course, loc, b))
            menu.addAction(action)
        menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))

    def set_course_config(self, course, location, btn):
        btn.setText(f"{course}")
        self.writer.course_name = course
        # Here we would set the destination path logic in writer
        self.writer.status_label.setText("READY")
        self.writer.status_label.setStyleSheet("color: #00ff88; background: rgba(0, 255, 136, 0.1); padding: 4px 12px; border-radius: 10px;")
        self.writer.editor.setReadOnly(False)

    def close_note(self):
        self.writer.editor.blockSignals(True)
        self.writer.editor.clear()
        self.writer.editor.blockSignals(False)
        self.writer.current_file_path = None
        self.writer.db_id = None
        self.writer.editor.setReadOnly(True)
        self.writer.status_label.setText("PENDING CONFIG")
        self.writer.status_label.setStyleSheet("color: #ffaa00; background: rgba(255, 170, 0, 0.1); padding: 4px 12px; border-radius: 10px;")
        self.btn_vault_courses.setText("Study Vault")

    def show_settings_menu(self):
        menu = RoundMenu(parent=self.btn_settings)
        
        gemma_action = Action(FIF.CHAT, "Ask Gemma", self)
        gemma_action.triggered.connect(self.launch_gemma)
        
        ingracia_action = Action(FIF.PEOPLE, "Ask Ingracia", self)
        ingracia_action.triggered.connect(self.launch_ingracia)
        
        bg_action = Action(FIF.IMAGE_EXPORT, "Import Inspiration", self)
        bg_action.triggered.connect(self.change_background)
        
        weather_action = Action(FIF.CLOUD, "Weather", self)
        weather_action.triggered.connect(self.show_weather)
        
        menu.addAction(gemma_action)
        menu.addAction(ingracia_action)
        menu.addSeparator()
        menu.addAction(bg_action)
        menu.addAction(weather_action)
        
        menu.exec(self.btn_settings.mapToGlobal(self.btn_settings.rect().bottomLeft()))

    def launch_gemma(self):
        try:
            from gui.components.gemma_chat_view import GemmaChatView
            self.gemma_view = GemmaChatView(parent=self.window())
            self.gemma_view.show()
        except: pass

    def launch_ingracia(self):
        try:
            from gui.components.ingracia_chat_view import IngraciaChatView
            self.ingracia_view = IngraciaChatView(parent=self.window())
            self.ingracia_view.show()
        except: pass

    def change_background(self):
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, "Choose Inspiration", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            self.backgroundChanged.emit(path)

    def show_weather(self):
        try:
            from qfluentwidgets import InfoBar, InfoBarPosition
            main_window = self.window()
            weather = getattr(main_window, 'weather_data', 'Weather data unavailable')
            InfoBar.info(
                title="Current Weather",
                content=weather,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=5000,
                parent=self
            )
        except: pass

    def show_open_menu(self):
        menu = RoundMenu(parent=self.btn_open)
        from core.database import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        # ONLY SHOW NOTES IN STUDY VAULT as requested
        # Removed limit to show all notes
        cursor.execute("SELECT id, path, course FROM files WHERE category = 'Notes' ORDER BY id DESC")
        notes = cursor.fetchall()
        conn.close()
        
        for nid, path, course in notes:
            name = os.path.basename(path).split('_')[0]
            label = f"{name} ({course})"
            action = Action(label, self)
            action.triggered.connect(lambda checked=False, p=path, n=nid: self.open_note(p, n))
            menu.addAction(action)
        
        if not notes:
            menu.addAction(Action("No notes found", self))
            
        menu.exec(self.btn_open.mapToGlobal(self.btn_open.rect().bottomLeft()))

    def open_note(self, path, db_id):
        from core.database import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT text_content FROM search_index WHERE file_id = ?", (db_id,))
        res = cursor.fetchone()
        content = res[0] if res else ""
        conn.close()
        
        self.writer.current_file_path = path
        self.writer.db_id = db_id
        self.writer.editor.blockSignals(True)
        self.writer.editor.setMarkdown(content)
        self.writer.editor.blockSignals(False)
        self.writer.status_label.setText("LOADED ✓")
        self.writer.status_label.setStyleSheet("color: #0088ff; background: rgba(0, 136, 255, 0.1); padding: 4px 12px; border-radius: 10px;")
        self.writer.editor.setReadOnly(False)

    def refresh_graph(self):
        try:
            from core.database import get_session_history
            from collections import defaultdict
            history = get_session_history(7)
            graph_data = defaultdict(int)
            for row in history:
                if row['status'] == 'finished':
                    date_str = row['created_at'].split(" ")[0]
                    graph_data[date_str] += row['duration_minutes']
            self.graph.set_data(dict(graph_data))
        except: pass

    def sync_music(self):
        try:
            main_window = self.window()
            if hasattr(main_window, 'musicInterface'):
                mi = main_window.musicInterface
                mi.player.playbackStateChanged.connect(self.on_music_state_changed)
                self.refresh_music_info()
                self.update_queue(mi)
        except: pass

    def refresh_music_info(self):
        try:
            main_window = self.window()
            mi = main_window.musicInterface
            label = mi.track_name_label
            song_name = label.text_content if hasattr(label, 'text_content') else label.text()
            self.music_header.setText(song_name)
            
            artist_label = mi.artist_label
            artist_name = artist_label.text_content if hasattr(artist_label, 'text_content') else artist_label.text()
            self.marquee_song.setText(artist_name) # Artist in marquee
            
            if mi.player.playbackState() == mi.player.PlaybackState.PlayingState:
                self.btn_play_pause.setIcon(FIF.PAUSE)
            else:
                self.btn_play_pause.setIcon(FIF.PLAY)
        except: pass

    def on_music_state_changed(self, state):
        self.refresh_music_info()

    def toggle_play(self):
        try:
            mi = self.window().musicInterface
            if mi.player.playbackState() == mi.player.PlaybackState.PlayingState:
                mi.player.pause()
            else:
                mi.player.play()
        except: pass

    def play_next(self):
        try: self.window().musicInterface.play_next_manual()
        except: pass

    def play_prev(self):
        try: self.window().musicInterface.play_previous()
        except: pass

    def play_queue_song(self, item):
        try:
            mi = self.window().musicInterface
            idx = self.queue_list.row(item)
            mi.playlist_widget.setCurrentRow(idx)
            mi.play_selected_track(mi.playlist_widget.currentItem())
        except: pass

    def update_queue(self, mi):
        self.queue_list.clear()
        for i in range(mi.playlist_widget.count()):
            item = mi.playlist_widget.item(i)
            path = item.data(Qt.UserRole)
            self.queue_list.addItem(os.path.basename(path))

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_graph()
        self.refresh_music_info()
        try: self.update_queue(self.window().musicInterface)
        except: pass
