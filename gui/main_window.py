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
from gui.interfaces.session_interface import SessionInterface
from core.database import initialize_db, purge_old_deleted_items, insert_session

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
        self.sessionInterface = SessionInterface(self)
        
        self.sessionInterface.sessionStarted.connect(self.start_session_timer)
        self.sessionInterface.sessionCancelled.connect(self.cancel_session_timer)
        
        # Title bar session timer
        self.session_clock = SubtitleLabel("00:00", self)
        self.session_clock.setStyleSheet("color: rgba(255, 255, 255, 0.3); font-size: 14px; margin-left: 20px; font-weight: bold;")
        
        # Title bar clock
        self.title_clock = SubtitleLabel(QTime.currentTime().toString("HH:mm"), self)
        self.title_clock.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-size: 14px; margin-left: 15px;")
        
        self.titleBar.layout().insertWidget(1, self.session_clock)
        self.titleBar.layout().insertWidget(2, self.title_clock)
        
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_title_clock)
        self.clock_timer.start(30000) # Update every 30s

        # Session Timer
        self.session_remaining_seconds = 0
        self.session_timer = QTimer(self)
        self.session_timer.timeout.connect(self.update_session_countdown)
        
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
        self.addSubInterface(self.searchInterface, FIF.SEARCH, 'Deep Search', NavigationItemPosition.TOP)
        self.addSubInterface(self.calendarInterface, FIF.CALENDAR, 'Study Calendar', NavigationItemPosition.TOP)
        self.addSubInterface(self.sessionInterface, FIF.HISTORY, 'Session', NavigationItemPosition.TOP)
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
        self.navigationInterface.setExpandWidth(48)
        self.navigationInterface.setCollapsible(False)
        self.navigationInterface.setMenuButtonVisible(False)


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

    def start_session_timer(self, minutes, intent):
        self.current_session_intent = intent
        self.current_session_duration = minutes
        self.session_remaining_seconds = minutes * 60
        self.update_session_display()
        self.session_timer.start(1000)
        self.session_clock.setStyleSheet("color: #00ff00; font-size: 14px; margin-left: 20px; font-weight: bold;")

    def cancel_session_timer(self):
        self.session_timer.stop()
        self.session_remaining_seconds = 0
        self.session_clock.setText("00:00")
        self.session_clock.setStyleSheet("color: rgba(255, 255, 255, 0.3); font-size: 14px; margin-left: 20px; font-weight: bold;")
        
        if getattr(self, 'current_session_intent', None):
            insert_session(self.current_session_intent, self.current_session_duration, 'cancelled')
            self.sessionInterface.load_history()
            self.current_session_intent = None

    def update_session_countdown(self):
        if self.session_remaining_seconds > 0:
            self.session_remaining_seconds -= 1
            self.update_session_display()
        else:
            self.session_timer.stop()
            self.session_clock.setText("00:00")
            self.session_clock.setStyleSheet("color: #ff0000; font-size: 14px; margin-left: 20px; font-weight: bold;")
            
            if getattr(self, 'current_session_intent', None):
                insert_session(self.current_session_intent, self.current_session_duration, 'finished')
                self.sessionInterface.load_history()
                self.current_session_intent = None

    def update_session_display(self):
        mins = self.session_remaining_seconds // 60
        secs = self.session_remaining_seconds % 60
        self.session_clock.setText(f"{mins:02d}:{secs:02d}")

    def preload(self):
        """Pre-load data for all major interfaces to ensure lightning-fast switching."""
        try:
            # Vault
            self.vaultInterface.reload_current_course()
            
            # Music
            self.musicInterface.load_playlist()
            
            # Calendar
            self.calendarInterface.update_event_list()
            
            # Session
            self.sessionInterface.load_history()
            
            # Radio
            self.radioInterface.load_playlist()
            
            # HydraSpace
            self.hydraInterface.load_initial_data()
        except Exception as e:
            print(f"Preloading notice: {e}")
