from PySide6.QtCore import Qt, QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QWidget, QVBoxLayout
from qfluentwidgets import (SubtitleLabel, PrimaryPushButton, TransparentPushButton, 
                            IconWidget, FluentIcon as FIF)

class HydraInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("HydraInterface")
        self.setStyleSheet("background: transparent;")
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(40, 40, 40, 40)
        self.layout.setSpacing(15)
        
        # Header / Status
        self.title = SubtitleLabel("Hydraspace", self)
        self.title.setStyleSheet("font-size: 24px; font-weight: bold;")
        self.layout.addWidget(self.title)
        
        self.web_view = QWebEngineView()
        self.web_view.setStyleSheet("background: transparent;")
        # User's Hydraspace site
        self.web_view.load(QUrl("https://hydra-space-mz6x.vercel.app"))
        
        self.layout.addWidget(self.web_view)
        
        # Toolbar
        self.toolbar = QWidget()
        self.tb_layout = QVBoxLayout(self.toolbar)
        self.tb_layout.setContentsMargins(0, 0, 0, 0)
        # Add back button etc if needed
        # self.layout.addWidget(self.toolbar)
