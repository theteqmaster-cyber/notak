from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame
from qfluentwidgets import (LineEdit, PrimaryPushButton, TransparentPushButton, 
                             FluentIcon as FIF, SubtitleLabel, CaptionLabel, CardWidget)

class CorrectionWindow(QWidget):
    correctionRequested = Signal(str) # user_notes
    tryAgainRequested = Signal()
    cancelled = Signal()

    def __init__(self, parent=None):
        # We don't set a parent widget to keep it as a standalone window, 
        # but we can keep a reference for centering if needed.
        super().__init__()
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Ingracia Correction Interface")
        self.setFixedSize(350, 240)
        
        # Dark celestial theme
        self.setStyleSheet("""
            CorrectionWindow {
                background-color: #0a0519;
            }
            CardWidget {
                background: rgba(25, 25, 35, 0.95);
                border: 1px solid rgba(0, 255, 170, 0.3);
                border-radius: 12px;
            }
        """)
        
        self.main_layout = QVBoxLayout(self)
        self.container = CardWidget(self)
        self.layout = QVBoxLayout(self.container)
        self.main_layout.addWidget(self.container)
        
        # Header
        hdr = QHBoxLayout()
        title_v = QVBoxLayout()
        title = SubtitleLabel("Celestial Advisor")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #00ffaa;")
        self.status_lbl = CaptionLabel("● READY")
        self.status_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.4); font-weight: bold; font-size: 9px;")
        title_v.addWidget(title)
        title_v.addWidget(self.status_lbl)
        hdr.addLayout(title_v)
        hdr.addStretch()
        self.layout.addLayout(hdr)
        
        self.layout.addWidget(CaptionLabel("Guiding Ingracia's manifestation:"))
        
        self.notes_input = LineEdit()
        self.notes_input.setPlaceholderText("e.g., Clean lines, connect arrows...")
        self.notes_input.setStyleSheet("color: white;")
        self.layout.addWidget(self.notes_input)
        
        self.layout.addStretch()
        
        # Buttons Row 1
        btn_row1 = QHBoxLayout()
        self.btn_correct = PrimaryPushButton("MAGIC CORRECT")
        self.btn_correct.setStyleSheet("background: #00ffaa; color: black; font-weight: bold;")
        self.btn_correct.clicked.connect(self.request_correction)
        btn_row1.addWidget(self.btn_correct)
        self.layout.addLayout(btn_row1)
        
        # Buttons Row 2
        btn_row2 = QHBoxLayout()
        self.btn_try_again = TransparentPushButton(FIF.SYNC, "Try Again")
        self.btn_try_again.clicked.connect(self.tryAgainRequested.emit)
        
        self.btn_cancel = TransparentPushButton(FIF.CLOSE, "Cancel")
        self.btn_cancel.clicked.connect(self.handle_cancel)
        
        btn_row2.addWidget(self.btn_try_again)
        btn_row2.addStretch()
        btn_row2.addWidget(self.btn_cancel)
        self.layout.addLayout(btn_row2)

    def request_correction(self):
        notes = self.notes_input.text().strip()
        self.correctionRequested.emit(notes)

    def set_status(self, text, color="#ffffff"):
        self.status_lbl.setText(text)
        self.status_lbl.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 9px;")

    def handle_cancel(self):
        self.cancelled.emit()
        self.close()

    def show_centered(self, screen_geometry):
        # Center the window on the screen
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)
        self.show()
        self.notes_input.setFocus()
