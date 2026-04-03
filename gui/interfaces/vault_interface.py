import os
import subprocess
import datetime

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QInputDialog, QFileDialog

from qfluentwidgets import (ScrollArea, TitleLabel, SubtitleLabel, PrimaryPushButton,
                            StrongBodyLabel, CardWidget, IconWidget, FluentIcon as FIF,
                            InfoBar, InfoBarPosition, SegmentedWidget, BodyLabel, MessageBoxBase, LineEdit)

from core.database import get_all_courses, get_connection, insert_file, check_duplicate_hash
from core.importer import process_file_import, VAULT_DIR, get_file_hash, split_filename_for_display

def get_files_for_course(course: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM files WHERE course = ? ORDER BY created_at DESC", (course,))
    res = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return res

class ClickableCardWidget(CardWidget):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            ClickableCardWidget {
                background: rgba(0, 0, 0, 0.5);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
            }
            ClickableCardWidget:hover {
                background: rgba(0, 0, 0, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
        """)

    def mouseDoubleClickEvent(self, event):
        # Open in native OS
        try:
            subprocess.Popen(['xdg-open', self.file_path])
        except Exception as e:
            print(f"Error opening file: {e}")

class VaultInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("VaultInterface")
        self.setStyleSheet("background: transparent;")
        self.setAcceptDrops(True)
        
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(40, 40, 40, 40)
        self.vBoxLayout.setSpacing(20)
        self.vBoxLayout.setAlignment(Qt.AlignTop)
        
        # Header Area
        header_layout = QHBoxLayout()
        self.title_label = TitleLabel("My Vault", self)
        self.title_label.setStyleSheet("font-weight: bold;")
        
        self.course_tabs = SegmentedWidget(self)
        self.course_tabs.currentItemChanged.connect(self.on_course_changed)
        
        self.btn_new_course = PrimaryPushButton(FIF.ADD, "New Course", self)
        self.btn_new_course.clicked.connect(self.add_new_course)
        
        header_layout.addWidget(self.title_label)
        header_layout.addStretch(1)
        header_layout.addWidget(self.course_tabs)
        header_layout.addSpacing(10)
        header_layout.addWidget(self.btn_new_course)
        
        self.vBoxLayout.addLayout(header_layout)
        
        # Action Bar Area
        self.actions_layout = QHBoxLayout()
        self.actions_layout.setSpacing(15)
        self.actions_layout.setAlignment(Qt.AlignLeft)
        
        self.btn_note = PrimaryPushButton(FIF.EDIT, "Take Note", self)
        self.btn_note.clicked.connect(self.take_note)
        
        self.btn_import = PrimaryPushButton(FIF.DOWNLOAD, "Import Files", self)
        self.btn_import.clicked.connect(self.import_files_dialog)
        
        self.btn_refresh = PrimaryPushButton(FIF.SYNC, "Refresh", self)
        self.btn_refresh.clicked.connect(lambda: self.refresh_gallery(self.current_course()))
        
        self.actions_layout.addWidget(self.btn_note)
        self.actions_layout.addWidget(self.btn_import)
        self.actions_layout.addWidget(self.btn_refresh)
        
        self.vBoxLayout.addLayout(self.actions_layout)
        
        self.sub_header = BodyLabel("Drop files anywhere, or use the buttons above to add resources.", self)
        self.sub_header.setStyleSheet("color: #aaaaaa;")
        self.vBoxLayout.addWidget(self.sub_header)
        
        self.vBoxLayout.addSpacing(20)
        
        # Gallery Area
        self.scroll_area = ScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("ScrollArea { background-color: transparent; border: none; }")
        
        self.gallery_widget = QWidget()
        self.gallery_widget.setStyleSheet("background-color: transparent;")
        
        self.gallery_layout = QGridLayout(self.gallery_widget)
        self.gallery_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.gallery_layout.setSpacing(20)
        
        self.scroll_area.setWidget(self.gallery_widget)
        self.vBoxLayout.addWidget(self.scroll_area)
        
        self.load_courses()

    def load_courses(self):
        courses = get_all_courses()
        
        self.course_tabs.clear()
        
        if not courses:
            courses = ["Inbox"]
            
        for idx, course in enumerate(courses):
            self.course_tabs.addItem(routeKey=course, text=course)
            
        if courses:
            self.course_tabs.setCurrentItem(courses[0])

    def add_new_course(self):
        name, ok = QInputDialog.getText(self, "Create New Course", "Enter the new course name:")
        if ok and name.strip():
            new_course = name.strip()
            self.course_tabs.addItem(routeKey=new_course, text=new_course)
            self.course_tabs.setCurrentItem(new_course)

    def current_course(self):
        return getattr(self, '_current_course', "Inbox")

    def take_note(self):
        from gui.zen_writer import ZenWriter
        self.writer = ZenWriter(self.current_course())
        self.writer.saveCompleted.connect(lambda: self.refresh_gallery(self.current_course()))
        self.writer.show()

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_gallery(self.current_course())
                
    def import_files_dialog(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Select Files to Import", "", "All Files (*)")
        if file_paths:
            self._execute_import(file_paths)

    def on_course_changed(self, routeKey: str):
        self._current_course = routeKey
        self.title_label.setText(f"Course: {routeKey}")
        self.refresh_gallery(routeKey)

    def refresh_gallery(self, course: str):
        # Clear existing
        for i in reversed(range(self.gallery_layout.count())): 
            widget = self.gallery_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
                
        files = get_files_for_course(course)
        if not files:
            empty = SubtitleLabel("No files here yet. Drag and Drop to import.", self)
            empty.setStyleSheet("color: #555;")
            self.gallery_layout.addWidget(empty, 0, 0)
            return

        row, col = 0, 0
        max_cols = 5
        for f in files:
            card = ClickableCardWidget(f['path'], self)
            card.setFixedSize(160, 210)
            card.setCursor(Qt.PointingHandCursor)
            
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(15, 20, 15, 15)
            c_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
            
            icon = FIF.DOCUMENT
            if f['category'] == 'PDFs': icon = FIF.CALENDAR
            elif f['category'] == 'Images': icon = FIF.PHOTO
            elif f['category'] == 'Notes': icon = FIF.EDIT
            
            icon_widget = IconWidget(icon)
            icon_widget.setFixedSize(50, 50)
            c_layout.addWidget(icon_widget, alignment=Qt.AlignHCenter)
            
            c_layout.addSpacing(15)
            
            basename = os.path.basename(f['path'])
            display_name, suffix = split_filename_for_display(basename)
            
            name = BodyLabel(display_name)
            name.setWordWrap(True)
            name.setAlignment(Qt.AlignCenter)
            name.setStyleSheet("color: #e0e0e0; font-size: 13px; font-weight: bold;")
            c_layout.addWidget(name)
            
            if suffix:
                suf_lbl = SubtitleLabel(suffix)
                suf_lbl.setAlignment(Qt.AlignCenter)
                suf_lbl.setStyleSheet("color: #777; font-size: 10px;")
                c_layout.addWidget(suf_lbl)
            
            self.gallery_layout.addWidget(card, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.sub_header.setText("Drop to Import!")
            self.sub_header.setStyleSheet("color: #0078d7; font-weight: bold;")

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        file_paths = [url.toLocalFile() for url in urls if os.path.isfile(url.toLocalFile())]
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

        self.sub_header.setText("Drop files anywhere, or use the buttons above to add resources.")
        self.sub_header.setStyleSheet("color: #aaaaaa;")
        
        msg = f"Imported {imported_count} files."
        if skipped_count:
            msg += f" (Skipped {skipped_count} duplicates)"
            
        self.refresh_gallery(target_course)
        
        InfoBar.success(
            title='Import Complete',
            content=msg,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=3000,
            parent=self
        )
