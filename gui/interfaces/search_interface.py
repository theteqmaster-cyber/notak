import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout

from qfluentwidgets import (ScrollArea, TitleLabel, SubtitleLabel, SearchLineEdit, 
                            StrongBodyLabel, CardWidget, IconWidget, FluentIcon as FIF,
                            BodyLabel)

from core.database import search_files
from core.importer import split_filename_for_display

class SearchResultCard(CardWidget):
    def __init__(self, result_dict, parent=None):
        super().__init__(parent)
        self.result = result_dict
        self.setFixedHeight(120)
        self.setStyleSheet("""
            SearchResultCard {
                background: rgba(0, 0, 0, 0.5);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
            }
            SearchResultCard:hover {
                background: rgba(0, 0, 0, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        
        top_layout = QHBoxLayout()
        icon = FIF.DOCUMENT
        cat = self.result['category']
        if cat == 'PDFs': icon = FIF.CALENDAR
        elif cat == 'Images': icon = FIF.PHOTO
        elif cat == 'Notes': icon = FIF.EDIT
            
        icon_widget = IconWidget(icon)
        icon_widget.setFixedSize(24, 24)
        top_layout.addWidget(icon_widget)
        
        title_layout = QVBoxLayout()
        basename = os.path.basename(self.result['path'])
        display_name, suffix = split_filename_for_display(basename)
        
        name = StrongBodyLabel(display_name)
        title_layout.addWidget(name)
        if suffix:
            suf_lbl = SubtitleLabel(suffix)
            suf_lbl.setStyleSheet("font-size: 10px; color: #777;")
            title_layout.addWidget(suf_lbl)
            
        top_layout.addLayout(title_layout)
        top_layout.addStretch(1)
        
        course_lbl = SubtitleLabel(f"{self.result['course']} | {cat}")
        course_lbl.setStyleSheet("font-size: 11px; color: #888;")
        top_layout.addWidget(course_lbl)
        
        layout.addLayout(top_layout)
        
        # Snippet processing
        snippet = self.result['text_content']
        # Very simple truncation
        if len(snippet) > 200:
            snippet = snippet[:200] + "..."
            
        # Optional: very simplistic highlight (Fluent UI parses rich text if we enable it, but plain text is safer for large dumps)
        desc = BodyLabel(snippet)
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #b0b0b0; font-size: 13px;")
        layout.addWidget(desc)

class SearchInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("SearchInterface")
        self.setStyleSheet("background: transparent;")
        
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(40, 40, 40, 40)
        self.vBoxLayout.setSpacing(20)
        self.vBoxLayout.setAlignment(Qt.AlignTop)
        
        self.title_label = TitleLabel("Deep Search", self)
        
        self.search_bar = SearchLineEdit(self)
        self.search_bar.setPlaceholderText("Search exact phrases in PDFs, Notes, and OCR Images...")
        self.search_bar.setMinimumWidth(500)
        self.search_bar.returnPressed.connect(self.perform_search)
        self.search_bar.searchSignal.connect(self.perform_search)
        
        self.results_info = SubtitleLabel("Hit enter to search across your entire vault.", self)
        self.results_info.setStyleSheet("color: #888;")
        
        self.vBoxLayout.addWidget(self.title_label)
        self.vBoxLayout.addSpacing(10)
        self.vBoxLayout.addWidget(self.search_bar)
        self.vBoxLayout.addWidget(self.results_info)
        self.vBoxLayout.addSpacing(20)
        
        # Results Area
        self.scroll_area = ScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("ScrollArea { background-color: transparent; border: none; }")
        
        self.results_widget = QWidget()
        self.results_widget.setStyleSheet("background-color: transparent;")
        
        self.results_layout = QVBoxLayout(self.results_widget)
        self.results_layout.setAlignment(Qt.AlignTop)
        self.results_layout.setSpacing(15)
        
        self.scroll_area.setWidget(self.results_widget)
        self.vBoxLayout.addWidget(self.scroll_area)

    def perform_search(self):
        query = self.search_bar.text().strip()
        if not query:
            return
            
        self.results_info.setText(f"Searching for '{query}'...")
        
        # Clear existing
        for i in reversed(range(self.results_layout.count())): 
            widget = self.results_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
                
        results = search_files(query)
        
        if not results:
            self.results_info.setText(f"No results found for '{query}'.")
            return
            
        self.results_info.setText(f"Found {len(results)} exact matches for '{query}'.")
        
        for res in results:
            card = SearchResultCard(res, self.results_widget)
            self.results_layout.addWidget(card)
