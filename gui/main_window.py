import os
import sys

from PySide6.QtCore import Qt, QSize, QTimer, QTime
from PySide6.QtGui import QIcon, QPixmap, QPalette, QBrush
from PySide6.QtWidgets import QApplication, QLabel

from qfluentwidgets import (NavigationItemPosition, setTheme, Theme, FluentWindow,
                            SubtitleLabel, setFont, SplashScreen)
from qfluentwidgets import FluentIcon as FIF

from gui.interfaces.home_interface import HomeInterface
from gui.interfaces.vault_interface import VaultInterface
from gui.interfaces.calendar_interface import CalendarInterface
from gui.interfaces.music_interface import MusicInterface
from gui.interfaces.notei_interface import NoteiInterface
from gui.interfaces.recycle_bin_interface import RecycleBinInterface
from gui.interfaces.search_interface import DeepSearchInterface
from gui.interfaces.about_interface import AboutInterface
from gui.interfaces.games_interface import GamesInterface
from gui.interfaces.radio_interface import RadioInterface
from gui.interfaces.hydraspace_interface import HydraSpaceInterface
from core.database import initialize_db, purge_old_deleted_items

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
        self.noteiInterface = NoteiInterface(self)
        self.noteiInterface.setObjectName("Mboard") # Internal rename
        self.recycleBinInterface = RecycleBinInterface(self)
        self.searchInterface = DeepSearchInterface(self)
        self.aboutInterface = AboutInterface(self)
        self.gamesInterface = GamesInterface(self)
        self.radioInterface = RadioInterface(self)
        self.hydraInterface = HydraSpaceInterface(self)
        
        # Title bar clock
        self.title_clock = SubtitleLabel(QTime.currentTime().toString("HH:mm"), self)
        self.title_clock.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-size: 14px; margin-left: 20px;")
        self.titleBar.layout().insertWidget(1, self.title_clock)
        
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_title_clock)
        self.clock_timer.start(30000) # Update every 30s
        
        # Connect signals
        self.homeInterface.backgroundChanged.connect(self.setBackgroundImage)
        self.homeInterface.searchRequested.connect(self.handle_search_request)

        # Wire up navigation
        self.initNavigation()
        
        # Load persisted background
        self.loadPersistedBackground()

    def initNavigation(self):
        # add navigation items to sidebar
        self.addSubInterface(self.homeInterface, FIF.HOME, 'Dashboard', NavigationItemPosition.TOP)
        self.addSubInterface(self.vaultInterface, FIF.FOLDER, 'My Vault', NavigationItemPosition.TOP)
        self.addSubInterface(self.searchInterface, FIF.SEARCH, 'Deep Search', NavigationItemPosition.TOP)
        self.addSubInterface(self.calendarInterface, FIF.CALENDAR, 'Study Calendar', NavigationItemPosition.TOP)
        self.addSubInterface(self.musicInterface, FIF.MUSIC, 'Music Hub', NavigationItemPosition.TOP)
        self.addSubInterface(self.radioInterface, FIF.WIFI, 'Internet Radio', NavigationItemPosition.TOP)
        self.addSubInterface(self.noteiInterface, FIF.LAYOUT, 'Mboard', NavigationItemPosition.TOP)
        self.addSubInterface(self.hydraInterface, FIF.GLOBE, 'HydraSpace', NavigationItemPosition.TOP)
        
        self.navigationInterface.addSeparator() # Visual separation for non-study tools
        
        self.addSubInterface(self.gamesInterface, FIF.GAME, 'Games Haven', NavigationItemPosition.TOP)
        
        self.addSubInterface(self.recycleBinInterface, FIF.DELETE, 'Recycle Bin', NavigationItemPosition.TOP)
        self.addSubInterface(self.aboutInterface, FIF.INFO, 'About Notak', NavigationItemPosition.TOP)
        
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
            #NotakWindow {
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

    def handle_search_request(self, text):
        # Switch to search interface
        self.switchTo(self.searchInterface)
        if text:
            self.searchInterface.search_bar.setText(text)
            self.searchInterface.on_search_changed(text)

    def update_title_clock(self):
        self.title_clock.setText(QTime.currentTime().toString("HH:mm"))
