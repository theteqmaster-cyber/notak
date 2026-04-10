import os
import re
import datetime
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit, QLabel, QHBoxLayout
from PySide6.QtCore import QTimer, Qt, Signal

from core.database import insert_file, get_connection
from core.importer import VAULT_DIR, get_file_hash

class ZenWriter(QWidget):
    # Pass updated note data through signal
    saveCompleted = Signal(dict)

    def __init__(self, course_name="Uncategorized", cloud_data=None):
        super().__init__()
        self.course_name = course_name
        self.current_file_path = None
        self.db_id = None
        
        # Cloud Integration
        self.cloud_data = cloud_data 
        self.is_cloud = cloud_data is not None
        
        self.setWindowTitle(f"Zen Writer - {course_name if not self.is_cloud else 'Cloud Note'}")
        self.resize(800, 600)
        self.setStyleSheet("background-color: transparent; color: #d4d4d4;") 
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(40, 20, 40, 40)
        
        self.top_bar = QHBoxLayout()
        self.status_label = QLabel("READY")
        self.status_label.setStyleSheet("""
            color: rgba(255, 255, 255, 0.4); 
            font-size: 11px; 
            font-weight: bold; 
            letter-spacing: 1px;
            background: rgba(255, 255, 255, 0.05);
            padding: 4px 12px;
            border-radius: 10px;
        """)
        self.top_bar.addStretch()
        self.top_bar.addWidget(self.status_label)
        self.main_layout.addLayout(self.top_bar)
        
        self.editor = QPlainTextEdit()
        self.editor.setStyleSheet("""
            QPlainTextEdit {
                font-family: 'Inter', 'Segoe UI', 'Roboto';
                font-size: 19px;
                line-height: 1.8;
                border: none;
                background: transparent;
                padding: 10px;
            }
        """)
        self.editor.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        placeholder = "Start cloud sync session..." if self.is_cloud else "Local note fragment..."
        self.editor.setPlaceholderText(placeholder)
        
        if self.is_cloud:
            self.editor.blockSignals(True)
            self.editor.setPlainText(cloud_data.get('content', ''))
            self.editor.blockSignals(False)
            
        self.editor.textChanged.connect(self.on_text_changed)
        self.main_layout.addWidget(self.editor)
        
        self.save_timer = QTimer(self)
        self.save_timer.setInterval(2000) 
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self.auto_save)
        
    def on_text_changed(self):
        self.status_label.setText("EDITING...")
        self.status_label.setStyleSheet("color: #ffaa00; background: rgba(255, 170, 0, 0.1); padding: 4px 12px; border-radius: 10px;")
        self.save_timer.start()
        
    def auto_save(self):
        text = self.editor.toPlainText().strip()
        if not text:
            return
            
        if self.is_cloud:
            self.save_to_cloud(text)
        else:
            self.save_to_local(text)

    def save_to_cloud(self, text):
        from core.supabase_service import SupabaseService
        self.status_label.setText("SYNCING...")
        first_line = text.split('\n')[0][:100]
        
        try:
            success = SupabaseService().update_note(self.cloud_data['id'], first_line, text)
            if success:
                self.status_label.setText("CLOUD SYNCED ✓")
                self.status_label.setStyleSheet("color: #00ff88; background: rgba(0, 255, 136, 0.1); padding: 4px 12px; border-radius: 10px;")
                
                # Update local data reflection
                self.cloud_data['title'] = first_line
                self.cloud_data['content'] = text
                # Force signal with updated payload for real-time dashboard patching
                self.saveCompleted.emit(self.cloud_data)
            else:
                self.status_label.setText("SYNC FAILED")
                self.status_label.setStyleSheet("color: #ff4444; background: rgba(255, 68, 68, 0.1); padding: 4px 12px; border-radius: 10px;")
        except:
            self.status_label.setText("OFFLINE")

    def save_to_local(self, text):
        first_line = text.split('\n')[0][:50]
        safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', first_line).strip('_')
        if not safe_name: safe_name = "untitled_note"
        date_str = datetime.datetime.now().strftime("%d_%b_%y").lower()
        filename = f"{safe_name}_{date_str}_sf26.md"
        dest_dir = os.path.join(VAULT_DIR, self.course_name, "Notes")
        os.makedirs(dest_dir, exist_ok=True)
        new_path = os.path.join(dest_dir, filename)
        
        try:
            if self.current_file_path and self.current_file_path != new_path:
                if os.path.exists(self.current_file_path): os.remove(self.current_file_path)
            self.current_file_path = new_path
            with open(new_path, 'w') as f: f.write(text)
            file_hash = get_file_hash(new_path)
            if self.db_id is None:
                self.db_id = insert_file(path=new_path, file_hash=file_hash, course=self.course_name, category="Notes", text_content=text)
            else:
                conn = get_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE files SET path = ?, file_hash = ? WHERE id = ?", (new_path, file_hash, self.db_id))
                    cursor.execute("UPDATE search_index SET text_content = ? WHERE file_id = ?", (text, self.db_id))
                    conn.commit()
                finally: conn.close()
            self.status_label.setText("LOCAL SAVED ✓")
            self.status_label.setStyleSheet("color: #0088ff; background: rgba(0, 136, 255, 0.1); padding: 4px 12px; border-radius: 10px;")
            self.saveCompleted.emit({'title': first_line, 'content': text})
        except: self.status_label.setText("SAVE ERROR")
