import os
import subprocess
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout

from qfluentwidgets import (ScrollArea, TitleLabel, SearchLineEdit, 
                            SubtitleLabel, IconWidget, FluentIcon as FIF,
                            BodyLabel, CardWidget)

from core.database import search_files
from core.importer import split_filename_for_display

class SearchResultCard(CardWidget):
    clicked = Signal(str)
    
    def __init__(self, file_data, parent=None):
        super().__init__(parent)
        self.file_path = file_data['path']
        self.setCursor(Qt.PointingHandCursor)
        
        self.v_layout = QVBoxLayout(self)
        self.v_layout.setContentsMargins(15, 15, 15, 15)
        
        # Header: Icon and Name
        self.h_header = QHBoxLayout()
        
        icon = FIF.DOCUMENT
        if file_data['category'] == 'PDFs': icon = FIF.CALENDAR
        elif file_data['category'] == 'Images': icon = FIF.PHOTO
        elif file_data['category'] == 'Notes': icon = FIF.EDIT
        
        self.icon_widget = IconWidget(icon)
        self.icon_widget.setFixedSize(24, 24)
        self.h_header.addWidget(self.icon_widget)
        
        basename = os.path.basename(self.file_path)
        display_name, _ = split_filename_for_display(basename)
        
        self.name_lbl = BodyLabel(display_name)
        self.name_lbl.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.h_header.addWidget(self.name_lbl)
        self.h_header.addStretch(1)
        
        # Course Tag
        self.course_lbl = CaptionLabel(file_data['course'])
        self.course_lbl.setStyleSheet("color: #0078d4; background: rgba(0, 120, 212, 0.1); padding: 2px 8px; border-radius: 4px;")
        self.h_header.addWidget(self.course_lbl)
        
        self.v_layout.addLayout(self.h_header)
        
        # Snippet
        snippet_text = file_data.get('snippet', '')
        if snippet_text:
            self.snippet_lbl = BodyLabel(snippet_text)
            self.snippet_lbl.setWordWrap(True)
            self.snippet_lbl.setStyleSheet("color: #aaaaaa; font-size: 12px; margin-top: 5px;")
            self.v_layout.addWidget(self.snippet_lbl)
            
        self.setStyleSheet("""
            SearchResultCard {
                background: rgba(0, 0, 0, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
            }
            SearchResultCard:hover {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
        """)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.file_path)

from qfluentwidgets import CaptionLabel

class DeepSearchInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("DeepSearchInterface")
        self.setStyleSheet("background: transparent;")
        
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(40, 40, 40, 40)
        self.vBoxLayout.setSpacing(20)
        self.vBoxLayout.setAlignment(Qt.AlignTop)
        
        # Header
        self.title_label = TitleLabel("Deep Search", self)
        self.title_label.setStyleSheet("font-weight: bold;")
        self.vBoxLayout.addWidget(self.title_label)
        
        self.sub_label = BodyLabel("Search through all your notes and study materials instantly.")
        self.sub_label.setStyleSheet("color: #888;")
        self.vBoxLayout.addWidget(self.sub_label)
        
        # Search Bar
        self.search_bar = SearchLineEdit(self)
        self.search_bar.setPlaceholderText("Search for keywords (e.g., 'database indexing')")
        self.search_bar.setClearButtonEnabled(True)
        self.search_bar.setFixedWidth(500)
        self.search_bar.textChanged.connect(self.on_search_changed)
        self.vBoxLayout.addWidget(self.search_bar)
        
        self.vBoxLayout.addSpacing(10)
        
        # Results Area
        self.scroll_area = ScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("ScrollArea { background-color: transparent; border: none; }")
        
        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setSpacing(10)
        self.results_layout.setAlignment(Qt.AlignTop)
        
        self.scroll_area.setWidget(self.results_container)
        self.vBoxLayout.addWidget(self.scroll_area)
        
        self.results_info = BodyLabel("", self)
        self.results_info.setStyleSheet("color: #666;")
        self.vBoxLayout.addWidget(self.results_info)

    def on_search_changed(self, text):
        query = text.strip()
        if not query:
            self.clear_results()
            self.results_info.setText("")
            return
            
        results = search_files(query)
        self.display_results(results)
        self.results_info.setText(f"Found {len(results)} matches.")

    def clear_results(self):
        for i in reversed(range(self.results_layout.count())):
            widget = self.results_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

    def display_results(self, results):
        self.clear_results()
        
        for res in results:
            card = SearchResultCard(res, self)
            card.clicked.connect(self.open_result)
            self.results_layout.addWidget(card)

    def open_result(self, path):
        try:
            subprocess.Popen(['xdg-open', path])
        except Exception as e:
            print(f"Error opening result: {e}")
