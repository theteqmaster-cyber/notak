import os
import sys

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap, QPalette, QBrush
from PySide6.QtWidgets import QApplication, QLabel

from qfluentwidgets import (NavigationItemPosition, setTheme, Theme, FluentWindow,
                            SubtitleLabel, setFont, SplashScreen)
from qfluentwidgets import FluentIcon as FIF

from gui.interfaces.home_interface import HomeInterface
from gui.interfaces.vault_interface import VaultInterface
from gui.interfaces.calendar_interface import CalendarInterface
from gui.interfaces.music_interface import MusicInterface

class MainWindow(FluentWindow):

    def __init__(self):
        super().__init__()
        self.initWindow()

        # Background Layer
        self.background_label = QLabel(self)
        self.background_label.setObjectName("GlobalBackground")
        self.background_label.lower()
        self.background_label.setAlignment(Qt.AlignCenter)
        self._current_bg_path = None

        # instantiate sub interfaces
        self.homeInterface = HomeInterface(self)
        self.vaultInterface = VaultInterface(self)
        self.calendarInterface = CalendarInterface(self)
        self.musicInterface = MusicInterface(self)
        
        # Connect signals
        self.homeInterface.backgroundChanged.connect(self.setBackgroundImage)

        # Wire up navigation
        self.initNavigation()
        
        # Load persisted background
        self.loadPersistedBackground()

    def initNavigation(self):
        # add navigation items to sidebar
        self.addSubInterface(self.homeInterface, FIF.HOME, 'Dashboard', NavigationItemPosition.TOP)
        self.addSubInterface(self.vaultInterface, FIF.FOLDER, 'My Vault', NavigationItemPosition.TOP)
        self.addSubInterface(self.calendarInterface, FIF.CALENDAR, 'Study Calendar', NavigationItemPosition.TOP)
        self.addSubInterface(self.musicInterface, FIF.MUSIC, 'Music Hub', NavigationItemPosition.TOP)

        # Bottom settings or about could go here
        
        # Adjust aesthetics
        self.navigationInterface.setAcrylicEnabled(False)
        self.navigationInterface.setExpandWidth(220)

    def initWindow(self):
        self.resize(1100, 800)
        self.setWindowTitle('Notak - Study Hub')
        # Dark theme
        setTheme(Theme.DARK)
        self.setObjectName("NotakWindow")

    def setBackgroundImage(self, image_path):
        if not os.path.exists(image_path):
            return
        
        self._current_bg_path = image_path
        self.updateBackground()
        
        # Extra CSS to ensure panels are semi-transparent
        style = """
            #NotakWindow .NavigationPanel, #NotakWindow .NavigationInterface {
                background: rgba(0, 0, 0, 0.4) !important;
                border: none;
            }
            .StackedWidget, .ScrollArea, .QWidget {
                background: transparent;
            }
        """
        self.setStyleSheet(style)
        
        # Persist
        with open(".notak_config", "w") as f:
            f.write(image_path)

    def updateBackground(self):
        if self._current_bg_path and os.path.exists(self._current_bg_path):
            pixmap = QPixmap(self._current_bg_path)
            if not pixmap.isNull():
                # Scale to fill (Crop & Center)
                scaled = pixmap.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                self.background_label.setPixmap(scaled)
                self.background_label.resize(self.size())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.updateBackground()

    def loadPersistedBackground(self):
        if os.path.exists(".notak_config"):
            try:
                with open(".notak_config", "r") as f:
                    path = f.read().strip()
                    if path:
                        self.background_label.setVisible(True)
                        self.setBackgroundImage(path)
            except:
                pass
