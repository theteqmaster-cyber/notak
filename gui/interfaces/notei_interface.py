import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout

from qfluentwidgets import (ScrollArea, TitleLabel, PrimaryPushButton,
                            SubtitleLabel, IconWidget, FluentIcon as FIF,
                            BodyLabel)

from core.database import get_connection
from core.importer import split_filename_for_display
from gui.components.marquee_label import MarqueeLabel

def get_notei_files():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM files 
        WHERE course = 'Notei' AND deleted_at IS NULL 
        ORDER BY created_at DESC
    """)
    res = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return res

class NoteiInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("NoteiInterface")
        self.setStyleSheet("background: transparent;")
        
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(40, 40, 40, 40)
        self.vBoxLayout.setSpacing(20)
        self.vBoxLayout.setAlignment(Qt.AlignTop)
        
        # Header Area
        header_layout = QHBoxLayout()
        self.title_label = TitleLabel("Notei - General Notes", self)
        self.title_label.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch(1)
        
        self.btn_note = PrimaryPushButton(FIF.EDIT, "Take General Note", self)
        self.btn_note.clicked.connect(self.take_note)
        header_layout.addWidget(self.btn_note)
        
        self.vBoxLayout.addLayout(header_layout)
        
        self.sub_header = BodyLabel("A place for your quick, general thoughts not tied to any specific course.", self)
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
        
    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_gallery()

    def take_note(self):
        from gui.zen_writer import ZenWriter
        # Use 'Notei' as a fixed internal course name
        self.writer = ZenWriter("Notei")
        self.writer.saveCompleted.connect(self.refresh_gallery)
        self.writer.show()

    def refresh_gallery(self):
        from gui.interfaces.vault_interface import ClickableCardWidget
        
        # Clear existing
        for i in reversed(range(self.gallery_layout.count())): 
            widget = self.gallery_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
                
        files = get_notei_files()
        if not files:
            empty = SubtitleLabel("No general notes yet. Write something!", self)
            empty.setStyleSheet("color: #555;")
            self.gallery_layout.addWidget(empty, 0, 0)
            return

        row, col = 0, 0
        max_cols = 5
        for f in files:
            card = ClickableCardWidget(f['path'], 'Notes', self)
            card.setFixedSize(160, 210)
            card.deleted.connect(self.refresh_gallery)
            
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(15, 20, 15, 15)
            c_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
            
            icon_widget = IconWidget(FIF.EDIT)
            icon_widget.setFixedSize(50, 50)
            c_layout.addWidget(icon_widget, alignment=Qt.AlignHCenter)
            
            c_layout.addSpacing(15)
            
            basename = os.path.basename(f['path'])
            display_name, suffix = split_filename_for_display(basename)
            
            name = MarqueeLabel(display_name)
            name.setFixedWidth(130) # Card width is 160, margin is 15x2
            name.setAlignment(Qt.AlignCenter)
            name.setStyleSheet("color: #e0e0e0; font-size: 13px; font-weight: bold; background: transparent; border: none;")
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
