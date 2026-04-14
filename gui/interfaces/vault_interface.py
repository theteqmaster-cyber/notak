import os
import subprocess
import datetime

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QInputDialog, QFileDialog, QLabel

from qfluentwidgets import (ScrollArea, TitleLabel, SubtitleLabel, PrimaryPushButton, PushButton,
                            StrongBodyLabel, CardWidget, IconWidget, FluentIcon as FIF, SearchLineEdit,
                            InfoBar, InfoBarPosition, SegmentedWidget, BodyLabel, MessageBoxBase, LineEdit,
                            RoundMenu, Action, MenuAnimationType, MessageBox, ComboBox)

from core.database import (get_all_courses, get_connection, insert_file, 
                           check_duplicate_hash, delete_file_by_path, mark_as_deleted, 
                           restore_file_by_path)
from core.importer import process_file_import, VAULT_DIR, get_file_hash, split_filename_for_display
from gui.components.marquee_label import MarqueeLabel

def get_files_for_course(course: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM files 
        WHERE course = ? AND deleted_at IS NULL 
        ORDER BY created_at DESC
    """, (course,))
    res = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return res

class ClickableCardWidget(CardWidget):
    deleted = Signal()
    
    def __init__(self, file_path, category, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.category = category
        self.setCursor(Qt.PointingHandCursor)
        
        # Color coding for accent
        accent_color = "rgba(255, 255, 255, 0.15)" # Default subtle border
        if self.category == 'PDFs': accent_color = "#E74C3C"  # Red
        elif self.category == 'Notes': accent_color = "#3498DB" # Blue
        elif self.category == 'Images': accent_color = "#2ECC71" # Green
        elif self.category == 'Slides': accent_color = "#F39C12" # Orange
        
        self.setStyleSheet(f"""
            ClickableCardWidget {{
                background: rgba(20, 20, 25, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-top: 4px solid {accent_color};
                border-radius: 10px;
            }}
            ClickableCardWidget:hover {{
                background: rgba(40, 40, 45, 0.85);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-top: 4px solid {accent_color};
            }}
        """)

    def mouseDoubleClickEvent(self, event):
        # Open in native OS
        try:
            subprocess.Popen(['xdg-open', self.file_path])
        except Exception as e:
            print(f"Error opening file: {e}")

    def contextMenuEvent(self, event):
        menu = RoundMenu(parent=self)
        
        # Determine if we are in recycle bin or normal view
        is_in_bin = False
        p = self.parent()
        while p:
            if hasattr(p, 'objectName') and p.objectName() == "RecycleBinInterface":
                is_in_bin = True
                break
            p = p.parent()
        
        open_folder_action = Action(FIF.FOLDER, "Open Folder")
        open_folder_action.triggered.connect(self.open_folder)
        menu.addAction(open_folder_action)
        
        if is_in_bin:
            restore_action = Action(FIF.SYNC, "Restore")
            restore_action.triggered.connect(self.request_restore)
            menu.addAction(restore_action)
            
            delete_action = Action(FIF.DELETE, "Delete Permanent", self)
            delete_action.triggered.connect(self.request_permanent_delete)
            menu.addAction(delete_action)
        else:
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

    def request_restore(self):
        restore_file_by_path(self.file_path)
        self.deleted.emit()

    def request_permanent_delete(self):
        title = "Permanent Deletion"
        content = f"Are you sure you want to delete '{os.path.basename(self.file_path)}' permanently? This cannot be undone."
        w = MessageBox(title, content, self.window())
        if w.exec():
            try:
                if os.path.exists(self.file_path):
                    os.remove(self.file_path)
                delete_file_by_path(self.file_path)
                self.deleted.emit()
            except Exception as e:
                print(f"Error during deletion: {e}")

    def open_folder(self):
        folder = os.path.dirname(self.file_path)
        if os.path.exists(folder):
            try:
                subprocess.Popen(['xdg-open', folder])
            except Exception as e:
                print(f"Error opening folder: {e}")

    def request_delete(self):
        # Legacy support if needed, redirects to bin
        self.request_bin()

class VaultInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("VaultInterface")
        self.setStyleSheet("background: transparent;")
        self.setAcceptDrops(True)
        
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(40, 30, 40, 30)
        self.vBoxLayout.setSpacing(25)
        self.vBoxLayout.setAlignment(Qt.AlignTop)
        
        # --- 1. TOP NAVIGATION (Course Selector) ---
        top_nav_layout = QHBoxLayout()
        top_nav_layout.setAlignment(Qt.AlignLeft)
        
        self.course_selector = ComboBox(self)
        self.course_selector.setMinimumWidth(250)
        self.course_selector.setStyleSheet("font-size: 15px; font-weight: bold;")
        self.course_selector.currentTextChanged.connect(self.on_course_changed)
        
        self.btn_new_course = PushButton(FIF.ADD, "New Course", self)
        self.btn_new_course.clicked.connect(self.add_new_course)
        
        top_nav_layout.addWidget(self.course_selector)
        top_nav_layout.addSpacing(15)
        top_nav_layout.addWidget(self.btn_new_course)
        top_nav_layout.addStretch(1)
        
        self.vBoxLayout.addLayout(top_nav_layout)
        
        # --- 2. HERO DASHBOARD BANNER ---
        self.hero_widget = QWidget(self)
        self.hero_widget.setFixedHeight(120)
        self.hero_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(50, 50, 65, 0.8), stop:1 rgba(25, 25, 35, 0.9));
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)
        hero_layout = QHBoxLayout(self.hero_widget)
        hero_layout.setContentsMargins(35, 20, 35, 20)
        
        # Left side: Text
        text_layout = QVBoxLayout()
        text_layout.setAlignment(Qt.AlignVCenter)
        self.course_title_label = QLabel("Select a Course...", self.hero_widget)
        self.course_title_label.setStyleSheet("font-size: 28px; font-weight: bold; color: white; background: transparent; border: none;")
        self.stats_label = QLabel("0 Files • Ready to start studying", self.hero_widget)
        self.stats_label.setStyleSheet("font-size: 14px; color: #b0b0b0; background: transparent; border: none;")
        
        text_layout.addWidget(self.course_title_label)
        text_layout.addWidget(self.stats_label)
        hero_layout.addLayout(text_layout)
        hero_layout.addStretch(1)
        
        # Right side: Actions integrated cleanly
        self.btn_ingracia = PrimaryPushButton(FIF.PEOPLE, "Ask Ingracia", self.hero_widget)
        self.btn_ingracia.clicked.connect(self.launch_ingracia_with_context)
        self.btn_note = PushButton(FIF.EDIT, "Take Note", self.hero_widget)
        self.btn_note.clicked.connect(self.take_note)
        self.btn_import = PushButton(FIF.DOWNLOAD, "Import PDF/Files", self.hero_widget)
        self.btn_import.clicked.connect(self.import_files_dialog)
        self.btn_refresh = PushButton(FIF.SYNC, "Refresh", self.hero_widget)
        self.btn_refresh.clicked.connect(lambda: self.refresh_gallery(self.current_course(), self.search_bar.text()))
        
        button_style = "padding: 8px 16px; font-weight: bold;"
        self.btn_ingracia.setStyleSheet(button_style + "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #8a2be2, stop:1 #ffd700); color: white;")
        self.btn_note.setStyleSheet(button_style)
        self.btn_import.setStyleSheet(button_style)
        self.btn_refresh.setStyleSheet(button_style)

        hero_layout.addWidget(self.btn_ingracia)
        hero_layout.addWidget(self.btn_note)
        hero_layout.addWidget(self.btn_import)
        hero_layout.addWidget(self.btn_refresh)
        
        self.vBoxLayout.addWidget(self.hero_widget)
        
        # --- 3. LOCAL SEARCH BAR ---
        filter_layout = QHBoxLayout()
        self.search_bar = SearchLineEdit(self)
        self.search_bar.setPlaceholderText("Filter files instantly within this course...")
        self.search_bar.setMinimumWidth(350)
        self.search_bar.setClearButtonEnabled(True)
        self.search_bar.textChanged.connect(lambda t: self.refresh_gallery(self.current_course(), t))
        filter_layout.addWidget(self.search_bar)
        filter_layout.addStretch(1)
        self.vBoxLayout.addLayout(filter_layout)
        
        # --- 4. GALLERY AREA ---
        self.scroll_area = ScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("ScrollArea { background-color: transparent; border: none; }")
        
        self.gallery_widget = QWidget()
        self.gallery_widget.setStyleSheet("background-color: transparent;")
        
        self.gallery_layout = QGridLayout(self.gallery_widget)
        self.gallery_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.gallery_layout.setSpacing(25)
        
        self.scroll_area.setWidget(self.gallery_widget)
        self.vBoxLayout.addWidget(self.scroll_area)
        
        self.load_courses()

    def load_courses(self):
        courses = [c for c in get_all_courses() if c != "Notei"]
        
        self.course_selector.clear()
        
        if not courses:
            courses = ["Inbox"]
            
        for idx, course in enumerate(courses):
            self.course_selector.addItem(text=course)
            
        if courses:
            self.course_selector.setCurrentText(courses[0])

    def add_new_course(self):
        name, ok = QInputDialog.getText(self, "Create New Course", "Enter the new course name:")
        if ok and name.strip():
            new_course = name.strip()
            self.course_selector.addItem(text=new_course)
            self.course_selector.setCurrentText(new_course)

    def current_course(self):
        return getattr(self, '_current_course', "Inbox")

    def take_note(self):
        from gui.zen_writer import ZenWriter
        self.writer = ZenWriter(self.current_course())
        self.writer.saveCompleted.connect(lambda: self.refresh_gallery(self.current_course(), self.search_bar.text()))
        self.writer.show()

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_gallery(self.current_course(), self.search_bar.text())
                
    def import_files_dialog(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Select Files to Import", "", "All Files (*)")
        if file_paths:
            self._execute_import(file_paths)

    def on_course_changed(self, text: str):
        if not text:
            return
        self._current_course = text
        if self.search_bar.text() != "":
            self.search_bar.clear() # This implicitly triggers refresh_gallery due to textChanged
        else:
            self.refresh_gallery(text)

    def refresh_gallery(self, course: str, filter_text: str = ""):
        # Clear existing layout properly to prevent C++ invalid pointer crash
        while self.gallery_layout.count():
            item = self.gallery_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        # Update Hero Title
        self.course_title_label.setText(course)
        
        # Load files and calculate stats
        files = get_files_for_course(course)
        
        total = len(files)
        pdfs = sum(1 for f in files if f['category'] == 'PDFs')
        notes = sum(1 for f in files if f['category'] == 'Notes')
        others = total - pdfs - notes
        
        stat_parts = []
        if pdfs > 0: stat_parts.append(f"{pdfs} PDFs")
        if notes > 0: stat_parts.append(f"{notes} Notes")
        if others > 0: stat_parts.append(f"{others} Others")
        
        stat_str = " • ".join(stat_parts) if stat_parts else "Upload files to get started."
        self.stats_label.setText(f"{total} Total Documents | {stat_str}")
        
        if not files:
            empty = SubtitleLabel("No files here yet. Drag and Drop to visually import them.", self)
            empty.setStyleSheet("color: #777;")
            self.gallery_layout.addWidget(empty, 0, 0)
            return

        # Apply visual filtering
        if filter_text:
            filter_lower = filter_text.lower()
            files = [f for f in files if filter_lower in os.path.basename(f['path']).lower()]

        row, col = 0, 0
        max_cols = 5
        for f in files:
            card = ClickableCardWidget(f['path'], f['category'], self)
            card.setFixedSize(170, 220)
            card.deleted.connect(lambda: self.refresh_gallery(self.current_course(), self.search_bar.text()))
            
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(15, 20, 15, 15)
            c_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
            
            icon = FIF.DOCUMENT
            if f['category'] == 'PDFs': icon = FIF.CALENDAR  # Often overridden with PDF icon later
            elif f['category'] == 'Images': icon = FIF.PHOTO
            elif f['category'] == 'Notes': icon = FIF.EDIT
            
            icon_widget = IconWidget(icon)
            icon_widget.setFixedSize(45, 45)
            c_layout.addWidget(icon_widget, alignment=Qt.AlignHCenter)
            
            c_layout.addSpacing(15)
            
            basename = os.path.basename(f['path'])
            display_name, suffix = split_filename_for_display(basename)
            
            name = MarqueeLabel(display_name)
            name.setAlignment(Qt.AlignCenter)
            name.setStyleSheet("color: #f0f0f0; font-size: 13px; font-weight: bold; background: transparent; border: none;")
            c_layout.addWidget(name)
            
            if suffix:
                suf_lbl = SubtitleLabel(suffix)
                suf_lbl.setAlignment(Qt.AlignCenter)
                suf_lbl.setStyleSheet("color: #888; font-size: 10px;")
                c_layout.addWidget(suf_lbl)
            
            self.gallery_layout.addWidget(card, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.search_bar.setPlaceholderText("Drop files to instantly import into this course!")

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        file_paths = [url.toLocalFile() for url in urls if os.path.isfile(url.toLocalFile())]
        self.search_bar.setPlaceholderText("Filter files instantly within this course...")
        self._execute_import(file_paths)
        
    def _execute_import(self, file_paths):
        target_course = self.current_course()
        
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
            
        self.refresh_gallery(target_course, self.search_bar.text())
        
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
        files = get_files_for_course(course)
        
        # Phase Gamma+: Collect 8 most recent metadata entries irregardless of file type
        recent_files = files[:8]
        
        metadata_lines = [f"METADATA_REASONING_MODE: {course}"]
        for n in recent_files:
            filename = os.path.basename(n['path'])
            # Formatting for AI reasoning: Title | Date
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
