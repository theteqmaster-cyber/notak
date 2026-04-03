import os
import re
import datetime
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit, QLabel
from PySide6.QtCore import QTimer, Qt, Signal

from core.database import insert_file, get_connection
from core.importer import VAULT_DIR, get_file_hash

class ZenWriter(QWidget):
    saveCompleted = Signal()

    def __init__(self, course_name="Uncategorized"):
        super().__init__()
        self.course_name = course_name
        self.current_file_path = None
        self.db_id = None
        
        self.setWindowTitle(f"Zen Writer - {course_name}")
        self.resize(800, 600)
        self.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        
        self.editor = QPlainTextEdit()
        self.editor.setStyleSheet("""
            QPlainTextEdit {
                font-family: 'Inter', 'Segoe UI', 'Roboto';
                font-size: 16px;
                line-height: 1.6;
                border: none;
                background: transparent;
            }
        """)
        self.editor.setPlaceholderText("Start typing your notes here. The first line becomes the file name...")
        self.editor.textChanged.connect(self.on_text_changed)
        layout.addWidget(self.editor)
        
        # Ghost indicator for save status
        self.status_label = QLabel("Draft")
        self.status_label.setStyleSheet("color: #555; font-size: 12px;")
        self.status_label.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        layout.addWidget(self.status_label)
        
        # Debounce Timer for Auto-Save
        self.save_timer = QTimer(self)
        self.save_timer.setInterval(2000) # 2 seconds
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self.auto_save)
        
    def on_text_changed(self):
        self.status_label.setText("Saving...")
        self.save_timer.start()
        
    def auto_save(self):
        text = self.editor.toPlainText().strip()
        if not text:
            self.status_label.setText("Draft (Empty)")
            return
            
        # Determine filename from first line
        first_line = text.split('\n')[0][:50]
        safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', first_line).strip('_')
        if not safe_name:
            safe_name = "untitled_note"
            
        date_str = datetime.datetime.now().strftime("%d_%b_%y").lower()
        filename = f"{safe_name}_{date_str}_sf26.md"
        
        dest_dir = os.path.join(VAULT_DIR, self.course_name, "Notes")
        os.makedirs(dest_dir, exist_ok=True)
        
        new_path = os.path.join(dest_dir, filename)
        
        try:
            # If the filename changed, cleanup the old file
            if self.current_file_path and self.current_file_path != new_path:
                if os.path.exists(self.current_file_path):
                    os.remove(self.current_file_path)
                    
            self.current_file_path = new_path
            
            with open(new_path, 'w') as f:
                f.write(text)
                
            file_hash = get_file_hash(new_path)
            
            # Simple upsert to database depending on whether we registered it yet
            conn = get_connection()
            cursor = conn.cursor()
            
            if self.db_id is None:
                # Insert
                self.db_id = insert_file(
                    path=new_path, 
                    file_hash=file_hash, 
                    course=self.course_name, 
                    category="Notes", 
                    text_content=text
                )
            else:
                # Update DB to match new content/path/hash
                cursor.execute("""
                    UPDATE files SET path = ?, file_hash = ? WHERE id = ?
                """, (new_path, file_hash, self.db_id))
                cursor.execute("""
                    UPDATE search_index SET text_content = ? WHERE file_id = ?
                """, (text, self.db_id))
                conn.commit()
            
            conn.close()
            
            self.status_label.setText("Saved ✓")
            self.saveCompleted.emit()
        except Exception as e:
            self.status_label.setText(f"Error saving: {e}")
