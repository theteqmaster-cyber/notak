import os
import re
import datetime
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLabel, QHBoxLayout, QFrame
from PySide6.QtGui import QTextCursor, QTextListFormat, QTextCharFormat, QFont
from PySide6.QtCore import QTimer, Qt, Signal

from qfluentwidgets import TransparentPushButton, FluentIcon as FIF, InfoBar, InfoBarPosition

from core.database import insert_file, get_connection
from core.importer import VAULT_DIR, get_file_hash
from core.gemini_service import GeminiService

class ZenWriter(QWidget):
    # Pass updated note data through signal
    saveCompleted = Signal(dict)

    def __init__(self, course_name="Uncategorized", cloud_data=None, existing_file_data=None):
        super().__init__()
        self.course_name = course_name
        self.current_file_path = existing_file_data.get('path') if existing_file_data else None
        self.db_id = existing_file_data.get('id') if existing_file_data else None
        
        # Cloud Integration
        self.cloud_data = cloud_data 
        self.is_cloud = cloud_data is not None
        
        self.active_ai_thread = None
        self.active_ai_worker = None
        
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
        
        # Formatting Toolbar
        self.toolbar_layout = QHBoxLayout()
        self.toolbar_layout.setSpacing(5)
        self.toolbar_layout.setAlignment(Qt.AlignLeft)
        
        self.btn_bold = TransparentPushButton(FIF.FONT_SIZE, "B")
        self.btn_bold.setToolTip("Bold")
        self.btn_bold.clicked.connect(self.toggle_bold)
        
        self.btn_italic = TransparentPushButton(FIF.FONT_SIZE, "I")
        self.btn_italic.setToolTip("Italic")
        self.btn_italic.clicked.connect(self.toggle_italic)
        
        self.btn_underline = TransparentPushButton(FIF.FONT_SIZE, "U")
        self.btn_underline.setToolTip("Underline")
        self.btn_underline.clicked.connect(self.toggle_underline)
        
        self.btn_h1 = TransparentPushButton(FIF.FONT_SIZE, "H1")
        self.btn_h1.setToolTip("Heading 1")
        self.btn_h1.clicked.connect(self.toggle_h1)
        
        self.btn_h2 = TransparentPushButton(FIF.FONT_SIZE, "H2")
        self.btn_h2.setToolTip("Heading 2")
        self.btn_h2.clicked.connect(self.toggle_h2)
        
        self.btn_bullets = TransparentPushButton(FIF.ALIGNMENT, "List")
        self.btn_bullets.setToolTip("Bullet List")
        self.btn_bullets.clicked.connect(self.toggle_bullets)
        
        self.btn_fmrt = TransparentPushButton(FIF.EDIT, "fmrt")
        self.btn_fmrt.setToolTip("AI Format Highlighted Text")
        self.btn_fmrt.setStyleSheet("color: #a371f7; font-weight: bold;")
        self.btn_fmrt.clicked.connect(self.format_selected_text)
        
        self.toolbar_layout.addWidget(self.btn_bold)
        self.toolbar_layout.addWidget(self.btn_italic)
        self.toolbar_layout.addWidget(self.btn_underline)
        self.toolbar_layout.addWidget(self.btn_h1)
        self.toolbar_layout.addWidget(self.btn_h2)
        self.toolbar_layout.addWidget(self.btn_bullets)
        self.toolbar_layout.addStretch()
        self.toolbar_layout.addWidget(self.btn_fmrt)
        
        self.main_layout.addLayout(self.toolbar_layout)
        
        # Separator Line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: rgba(255, 255, 255, 0.1); border: none; height: 1px;")
        self.main_layout.addWidget(line)
        self.main_layout.addSpacing(10)
        
        self.editor = QTextEdit()
        self.editor.setStyleSheet("""
            QTextEdit {
                font-family: 'Inter', 'Segoe UI', 'Roboto';
                font-size: 16px;
                line-height: 1.6;
                border: none;
                background: transparent;
                padding: 10px;
            }
        """)
        placeholder = "Start cloud sync session..." if self.is_cloud else "Write your note here..."
        self.editor.setPlaceholderText(placeholder)
        
        if self.is_cloud:
            self.editor.blockSignals(True)
            self.editor.setMarkdown(cloud_data.get('content', ''))
            self.editor.blockSignals(False)
        elif existing_file_data:
            self.editor.blockSignals(True)
            text_content = existing_file_data.get('text_content', '')
            if not text_content.strip() and self.current_file_path and os.path.exists(self.current_file_path):
                try:
                    with open(self.current_file_path, 'r', encoding='utf-8') as f:
                        text_content = f.read()
                except Exception:
                    pass
            self.editor.setMarkdown(text_content)
            self.editor.blockSignals(False)
            
        self.editor.textChanged.connect(self.on_text_changed)
        self.main_layout.addWidget(self.editor)
        
        self.save_timer = QTimer(self)
        self.save_timer.setInterval(2000) 
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self.auto_save)
        
    def toggle_bold(self):
        fmt = self.editor.currentCharFormat()
        fmt.setFontWeight(QFont.Bold if fmt.fontWeight() != QFont.Bold else QFont.Normal)
        self.editor.mergeCurrentCharFormat(fmt)
        
    def toggle_italic(self):
        fmt = self.editor.currentCharFormat()
        fmt.setFontItalic(not fmt.fontItalic())
        self.editor.mergeCurrentCharFormat(fmt)
        
    def toggle_underline(self):
        fmt = self.editor.currentCharFormat()
        fmt.setFontUnderline(not fmt.fontUnderline())
        self.editor.mergeCurrentCharFormat(fmt)
        
    def toggle_h1(self):
        cursor = self.editor.textCursor()
        fmt = cursor.blockFormat()
        fmt.setHeadingLevel(1 if fmt.headingLevel() != 1 else 0)
        cursor.setBlockFormat(fmt)
        
    def toggle_h2(self):
        cursor = self.editor.textCursor()
        fmt = cursor.blockFormat()
        fmt.setHeadingLevel(2 if fmt.headingLevel() != 2 else 0)
        cursor.setBlockFormat(fmt)
        
    def toggle_bullets(self):
        cursor = self.editor.textCursor()
        if cursor.currentList():
            cursor.setBlockFormat(cursor.blockFormat())
            cursor.createList(QTextListFormat.ListStyleUndefined)
        else:
            cursor.createList(QTextListFormat.ListDisc)
            
    def format_selected_text(self):
        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            InfoBar.warning(
                title="No text selected",
                content="Please highlight some text first to format it.",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return
            
        selected_text = cursor.selectedText()
        # Handle Qt's paragraph separator char replacements
        selected_text = selected_text.replace('\u2029', '\n').replace('\u2028', '\n')
        
        if not selected_text.strip():
            return
            
        self.btn_fmrt.setText("✨ Formatting...")
        self.btn_fmrt.setEnabled(False)
        self.editor.setReadOnly(True)
        self.status_label.setText("AI FORMATTING...")
        self.status_label.setStyleSheet("color: #a371f7; background: rgba(163, 113, 247, 0.1); padding: 4px 12px; border-radius: 10px;")
        
        # Build prompt
        system_prompt = "You are a professional academic text formatter. Output ONLY the properly formatted text without any conversational filler or introductory sentences."
        prompt = f"Format the following text into a clean, professional, academic tone. Fix spelling/grammar. Use proper markdown headings, spacing, and bullets where appropriate. Do not change the original meaning.\n\nText:\n{selected_text}"
        
        self.active_ai_thread, self.active_ai_worker = GeminiService().get_chat_thread(prompt, system_prompt=system_prompt)
        self.active_ai_worker.finished.connect(self.on_format_finished)
        self.active_ai_worker.error.connect(lambda e: self.on_format_finished("", e))
        self.active_ai_thread.start()

    def on_format_finished(self, formatted_text, error_msg=None):
        self.btn_fmrt.setText("fmrt")
        self.btn_fmrt.setEnabled(True)
        self.editor.setReadOnly(False)
        self.status_label.setText("EDITING...")
        self.status_label.setStyleSheet("color: #ffaa00; background: rgba(255, 170, 0, 0.1); padding: 4px 12px; border-radius: 10px;")
        
        if error_msg or not formatted_text.strip():
            InfoBar.error(
                title="Format Failed",
                content=error_msg or "AI returned an empty response.",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=4000,
                parent=self
            )
            return
            
        # Replace selected text with the formatted text
        cursor = self.editor.textCursor()
        # Ensure we still have a selection (should be the same since we made it read-only)
        if cursor.hasSelection():
            cursor.removeSelectedText()
        # Insert as markdown to render the formatting
        cursor.insertMarkdown(formatted_text.strip())
        self.auto_save()
        
    def on_text_changed(self):
        self.status_label.setText("EDITING...")
        self.status_label.setStyleSheet("color: #ffaa00; background: rgba(255, 170, 0, 0.1); padding: 4px 12px; border-radius: 10px;")
        self.save_timer.start()
        
    def auto_save(self):
        text = self.editor.toPlainText().strip()
        markdown_text = self.editor.toMarkdown()
        if not text:
            return
            
        if self.is_cloud:
            self.save_to_cloud(markdown_text, text)
        else:
            self.save_to_local(markdown_text, text)

    def save_to_cloud(self, markdown_text, plain_text):
        from core.supabase_service import SupabaseService
        self.status_label.setText("SYNCING...")
        first_line = plain_text.split('\n')[0][:100]
        
        try:
            success = SupabaseService().update_note(self.cloud_data['id'], first_line, markdown_text)
            if success:
                self.status_label.setText("CLOUD SYNCED ✓")
                self.status_label.setStyleSheet("color: #00ff88; background: rgba(0, 255, 136, 0.1); padding: 4px 12px; border-radius: 10px;")
                
                # Update local data reflection
                self.cloud_data['title'] = first_line
                self.cloud_data['content'] = markdown_text
                # Force signal with updated payload for real-time dashboard patching
                self.saveCompleted.emit(self.cloud_data)
            else:
                self.status_label.setText("SYNC FAILED")
                self.status_label.setStyleSheet("color: #ff4444; background: rgba(255, 68, 68, 0.1); padding: 4px 12px; border-radius: 10px;")
        except:
            self.status_label.setText("OFFLINE")

    def save_to_local(self, markdown_text, plain_text):
        first_line = plain_text.split('\n')[0][:50]
        safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', first_line).strip('_')
        if not safe_name: safe_name = "untitled_note"
        date_str = datetime.datetime.now().strftime("%d_%b_%y").lower()
        filename = f"{safe_name}_{date_str}_sf26.md"
        dest_dir = os.path.join(VAULT_DIR, self.course_name, "Notes")
        os.makedirs(dest_dir, exist_ok=True)
        new_path = os.path.join(dest_dir, filename)
        
        try:
            # If editing existing file, keep its path instead of creating new one
            if self.current_file_path:
                new_path = self.current_file_path
            else:
                self.current_file_path = new_path
                
            with open(new_path, 'w', encoding='utf-8') as f: 
                f.write(markdown_text)
                
            file_hash = get_file_hash(new_path)
            if self.db_id is None:
                self.db_id = insert_file(path=new_path, file_hash=file_hash, course=self.course_name, category="Notes", text_content=markdown_text)
            else:
                conn = get_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE files SET path = ?, file_hash = ? WHERE id = ?", (new_path, file_hash, self.db_id))
                    cursor.execute("UPDATE search_index SET text_content = ? WHERE file_id = ?", (markdown_text, self.db_id))
                    conn.commit()
                finally: conn.close()
            self.status_label.setText("LOCAL SAVED ✓")
            self.status_label.setStyleSheet("color: #0088ff; background: rgba(0, 136, 255, 0.1); padding: 4px 12px; border-radius: 10px;")
            self.saveCompleted.emit({'title': first_line, 'content': markdown_text})
        except: self.status_label.setText("SAVE ERROR")
