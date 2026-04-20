from PySide6.QtCore import Qt, Signal, QSize, QEvent, QTimer
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, 
                             QPlainTextEdit, QLabel, QFrame, QGraphicsDropShadowEffect, QTextBrowser)
from qfluentwidgets import (SubtitleLabel, BodyLabel, CaptionLabel, 
                             TransparentPushButton, FluentIcon as FIF, 
                             CardWidget, IconWidget, ScrollArea)
import datetime

class MessageBubble(QFrame):
    def __init__(self, text, is_user=True, is_error=False, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(18, 12, 18, 12)
        self.layout.setSpacing(0)
        
        self.browser = QTextBrowser()
        self.browser.setReadOnly(True)
        self.browser.setFrameStyle(QFrame.NoFrame)
        self.browser.setAcceptRichText(True)
        self.browser.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.browser.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.browser.setOpenExternalLinks(True)
        self.browser.setHtml(text)
        
        self.layout.addWidget(self.browser)
        self.setFixedWidth(380)
        
        if is_error:
            self.setStyleSheet("""
                QFrame {
                    background: rgba(255, 68, 68, 0.15);
                    border: 1px solid rgba(255, 68, 68, 0.3);
                    border-radius: 12px;
                }
            """)
            self.browser.setStyleSheet("color: #ff6666; font-size: 13px; font-family: 'Segoe UI'; background: transparent; border: none;")
        elif is_user:
            self.setStyleSheet("""
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(0, 120, 215, 0.45), stop:1 rgba(0, 120, 215, 0.15));
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    border-radius: 16px;
                    border-bottom-right-radius: 2px;
                }
            """)
            self.browser.setStyleSheet("color: white; font-size: 14px; font-family: 'Segoe UI'; background: transparent; border: none;")
        else:
            self.setStyleSheet("""
                QFrame {
                    background: rgba(45, 45, 45, 0.85);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 16px;
                    border-bottom-left-radius: 2px;
                }
            """)
            self.browser.setStyleSheet("color: rgba(255, 255, 255, 0.95); font-size: 14px; font-family: 'Segoe UI'; background: transparent; border: none;")

        self.adjust_height()

    def append_text(self, text):
        from PySide6.QtGui import QTextCursor
        self.browser.moveCursor(QTextCursor.End)
        self.browser.insertPlainText(text)
        self.adjust_height()

    def adjust_height(self):
        self.browser.document().setTextWidth(self.browser.width() - 36)
        doc_height = self.browser.document().size().height()
        self.browser.setFixedHeight(int(doc_height) + 12)
        self.setFixedHeight(int(doc_height) + 36)

class GemmaChatView(QWidget):
    closed = Signal()

    def __init__(self, course_name=None, context_text=None, parent=None):
        super().__init__(parent)
        self.course_name = course_name
        self.context_text = context_text
        self.history = []
        
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint | Qt.Window | Qt.WindowStaysOnTopHint)
        
        self.polling_timer = QTimer(self)
        self.polling_timer.timeout.connect(self._sync_chat_buffer)
        
        self.setup_ui()
        
        if course_name:
            self.add_message(f"Hi! I've scanned your **{course_name}** notes. How can I help you today?", is_user=False)
        else:
            self.add_message("Hi! I'm Gemma, your offline AI assistant. Ask me anything!", is_user=False)

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        
        self.container = QFrame()
        self.container.setObjectName("MainContainer")
        self.container.setStyleSheet("""
            #MainContainer {
                background: rgba(20, 20, 20, 0.96);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 28px;
            }
        """)
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setColor(Qt.black)
        shadow.setOffset(0, 15)
        self.container.setGraphicsEffect(shadow)
        
        self.main_layout.addWidget(self.container)
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(25, 25, 25, 25)
        self.layout.setSpacing(15)
        
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(5, 5, 5, 10)
        
        self.icon_badge = QWidget()
        self.icon_badge.setFixedSize(40, 40)
        self.icon_badge.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0078d7, stop:1 #00d2ff); border-radius: 12px;")
        ib_layout = QVBoxLayout(self.icon_badge)
        ib_layout.setContentsMargins(8, 8, 8, 8)
        self.icon_widget = IconWidget(FIF.CHAT)
        self.icon_widget.setStyleSheet("color: white;")
        ib_layout.addWidget(self.icon_widget, alignment=Qt.AlignCenter)
        header_layout.addWidget(self.icon_badge)
        
        title_v = QVBoxLayout()
        title_v.setSpacing(0)
        title_text = "Gemma AI" if not self.course_name else f"Study Hub • {self.course_name}"
        self.title_lbl = SubtitleLabel(title_text)
        self.title_lbl.setStyleSheet("font-size: 19px; font-weight: 900; color: white;")
        self.status_lbl = CaptionLabel("● SECURE & READY")
        self.status_lbl.setStyleSheet("color: #00ffaa; font-weight: bold; letter-spacing: 1.5px; font-size: 8px;")
        title_v.addWidget(self.title_lbl)
        title_v.addWidget(self.status_lbl)
        header_layout.addLayout(title_v)
        header_layout.addStretch()
        
        self.btn_stop = TransparentPushButton(FIF.CLOSE, "")
        self.btn_stop.setFixedSize(36, 36)
        self.btn_stop.setStyleSheet("color: #ff4444; background: rgba(255, 68, 68, 0.1); border-radius: 18px;")
        self.btn_stop.clicked.connect(self.stop_generation)
        self.btn_stop.hide()
        header_layout.addWidget(self.btn_stop)
        
        self.btn_close = TransparentPushButton(FIF.CLOSE, "")
        self.btn_close.setFixedSize(36, 36)
        self.btn_close.setStyleSheet("color: rgba(255,255,255,0.4); border-radius: 18px;")
        self.btn_close.clicked.connect(self.closed.emit)
        header_layout.addWidget(self.btn_close)
        self.layout.addLayout(header_layout)
        
        self.scroll_area = ScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")
        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setAlignment(Qt.AlignTop)
        self.messages_layout.setSpacing(25)
        self.scroll_area.setWidget(self.messages_container)
        self.layout.addWidget(self.scroll_area)
        
        input_frame = QFrame()
        input_frame.setFixedHeight(54)
        input_frame.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 27px;
            }
        """)
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(20, 5, 5, 5)
        
        self.input_edit = QPlainTextEdit()
        self.input_edit.setPlaceholderText("Ask a question about your notes...")
        self.input_edit.setFixedHeight(30)
        self.input_edit.setStyleSheet("background: transparent; border: none; color: white; font-size: 14px;")
        self.input_edit.installEventFilter(self)
        input_layout.addWidget(self.input_edit)
        
        self.btn_send = TransparentPushButton(FIF.SEND, "")
        self.btn_send.setFixedSize(38, 38)
        self.btn_send.setStyleSheet("background: white; color: black; border-radius: 19px;")
        self.btn_send.clicked.connect(self.send_message)
        input_layout.addWidget(self.btn_send)
        self.layout.addWidget(input_frame)

    def eventFilter(self, obj, event):
        if obj is self.input_edit and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return and not event.modifiers() & Qt.ShiftModifier:
                self.send_message()
                return True
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def add_message(self, text, is_user=True, is_error=False):
        bubble = MessageBubble(text, is_user, is_error)
        self.messages_layout.addWidget(bubble, alignment=Qt.AlignRight if is_user else Qt.AlignLeft)
        self.scroll_to_bottom()
        
        if not is_user and not is_error:
            self.history.append({"role": "assistant", "content": text})
        elif is_user:
            self.history.append({"role": "user", "content": text})
        return bubble

    def scroll_to_bottom(self):
        QTimer.singleShot(10, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        ))

    def send_message(self):
        try:
            if hasattr(self, '_current_thread') and self._current_thread and self._current_thread.isRunning():
                return
        except RuntimeError: pass

        text = self.input_edit.toPlainText().strip()
        if not text: return
        
        self.input_edit.clear()
        self.add_message(text, is_user=True)
        
        from core.gemma_service import GemmaService
        service = GemmaService()
        self.status_lbl.setText("● THINKING...")
        self.status_lbl.setStyleSheet("color: #ffaa00; font-weight: bold; letter-spacing: 1.5px; font-size: 8px;")
        
        system_prompt = "You are Gemma, a complete offline assistant. Always finish your thoughts fully."
        if self.course_name and self.context_text:
            system_prompt += f" Notes context: {self.context_text}"
        
        self._current_bubble = self.add_message("", is_user=False)
        thread, worker = service.get_chat_thread(text, system_prompt, self.history[:-1])
        
        self._current_worker = worker
        self._current_thread = thread
        self.btn_stop.show()
        self._watchdog_count = 0
        
        self.polling_timer.start(50)
        thread.start()

    def _sync_chat_buffer(self):
        if not hasattr(self, '_current_worker') or not self._current_worker:
            return
            
        # Check for errors first
        if self._current_worker.error_msg:
            self.polling_timer.stop()
            self.add_message(f"🚨 {self._current_worker.error_msg}", is_user=False, is_error=True)
            self.status_lbl.setText("● OFFLINE • ERROR")
            self.status_lbl.setStyleSheet("color: #ff4444; font-weight: bold; letter-spacing: 1.5px; font-size: 8px;")
            self.btn_stop.hide()
            self._cleanup_thread()
            return

        has_new = False
        while self._current_worker.output_buffer:
            chunk = self._current_worker.output_buffer.pop(0)
            chunk = chunk.replace("**", "").replace("*", "")
            self._current_bubble.append_text(chunk)
            if self.history and self.history[-1]["role"] == "assistant":
                self.history[-1]["content"] += chunk
            has_new = True
            self._watchdog_count = 0 # Reset watchdog on activity
                
        if has_new:
            self.scroll_to_bottom()
        else:
            self._watchdog_count += 1
        
        # Watchdog: If nothing in 10s (200 ticks at 50ms)
        if self._watchdog_count > 200:
            self._current_worker.error_msg = "Gemma is taking too long to respond. Ensure Ollama is running correctly."
            return

        # Draining Check
        if self._current_worker.is_done and not self._current_worker.output_buffer:
            self.polling_timer.stop()
            self.status_lbl.setText("● SECURE & READY")
            self.status_lbl.setStyleSheet("color: #00ffaa; font-weight: bold; letter-spacing: 1.5px; font-size: 8px;")
            self.btn_stop.hide()
            self._cleanup_thread()

    def _cleanup_thread(self):
        if hasattr(self, '_current_thread') and self._current_thread:
            self._current_thread.quit()
            self._current_thread.wait()
            self._current_thread = None
            self._current_worker = None

    def stop_generation(self):
        if hasattr(self, '_current_worker') and self._current_worker:
            self._current_worker.stop()
            self.status_lbl.setText("● STOPPED")
            self.status_lbl.setStyleSheet("color: #ff4444; font-weight: bold; letter-spacing: 1.5px; font-size: 8px;")
            self.btn_stop.hide()

    def closeEvent(self, event):
        self.stop_generation()
        self.polling_timer.stop()
        self._cleanup_thread()
        super().closeEvent(event)
