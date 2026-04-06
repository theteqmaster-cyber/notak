import os
import json
from PySide6.QtCore import Qt, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QLabel, QInputDialog)
from PySide6.QtGui import QPixmap
from qfluentwidgets import (SubtitleLabel, PrimaryPushButton, TransparentPushButton, 
                            Slider, IconWidget, FluentIcon as FIF, BodyLabel, CaptionLabel, SearchLineEdit)

RADIOS_FILE = ".notak_radios.json"

class RadioItemWidget(QWidget):
    def __init__(self, name, url, parent=None):
        super().__init__(parent)
        self.name = name
        self.url = url
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(15, 8, 15, 8)
        self.layout.setSpacing(15)
        
        # Mini Icon
        self.thumb = IconWidget(FIF.WIFI)
        self.thumb.setFixedSize(24, 24)
        self.layout.addWidget(self.thumb)
        
        # Info Stack
        info = QVBoxLayout()
        info.setSpacing(2)
        self.title_lbl = BodyLabel(name)
        self.title_lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: #eee;")
        self.url_lbl = CaptionLabel(url)
        self.url_lbl.setStyleSheet("color: #aaa; font-size: 12px;")
        info.addWidget(self.title_lbl)
        info.addWidget(self.url_lbl)
        self.layout.addLayout(info)
        self.layout.addStretch(1)

class RadioInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("RadioInterface")
        self.setStyleSheet("background: transparent;")
        
        # Audio Engine
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.5)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(40, 40, 40, 40)
        self.layout.setSpacing(20)
        
        # Header Area
        header_h = QHBoxLayout()
        header_h.setContentsMargins(0, 0, 0, 10)
        self.title = SubtitleLabel("Internet Radio", self)
        self.title.setStyleSheet("font-size: 26px; font-weight: bold;")
        header_h.addWidget(self.title)
        header_h.addStretch(1)
        
        self.song_search = SearchLineEdit(self)
        self.song_search.setPlaceholderText("Search stations...")
        self.song_search.setFixedWidth(200)
        self.song_search.textChanged.connect(self.filter_playlist)
        header_h.addWidget(self.song_search)
        
        self.btn_clear = TransparentPushButton(FIF.DELETE, "Clear List")
        self.btn_clear.clicked.connect(self.clear_playlist)
        self.btn_add = PrimaryPushButton(FIF.ADD, "Add Station", self)
        self.btn_add.clicked.connect(self.add_station)
        
        header_h.addWidget(self.btn_clear)
        header_h.addWidget(self.btn_add)
        self.layout.addLayout(header_h)
        
        # Main Area
        self.playlist_widget = QListWidget()
        self.playlist_widget.setObjectName("RadioListWidget")
        self.playlist_widget.setStyleSheet("""
            QListWidget {
                background: rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                color: #ddd;
            }
            QListWidget::item {
                background: rgba(255,255,255,0.05);
                margin-bottom: 4px;
                border-radius: 8px;
            }
            QListWidget::item:hover {
                background: rgba(255, 255, 255, 0.1);
            }
            QListWidget::item:selected {
                background: rgba(0, 120, 215, 0.25);
                border-left: 4px solid #0078d7;
            }
        """)
        self.playlist_widget.itemDoubleClicked.connect(self.play_selected_track)
        self.layout.addWidget(self.playlist_widget, 1)
        
        # Now Playing Footer
        self.now_playing_card = QWidget()
        self.now_playing_card.setFixedHeight(100) 
        self.now_playing_card.setStyleSheet("background: rgba(0, 0, 0, 0.85); border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.08);")
        self.layout.addWidget(self.now_playing_card)
        
        self.footer_layout = QHBoxLayout(self.now_playing_card)
        self.footer_layout.setContentsMargins(20, 10, 20, 10)
        self.footer_layout.setSpacing(20)
        
        # Left Info
        self.track_name_label = BodyLabel("No Station Selected")
        self.track_name_label.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        self.status_label = CaptionLabel("Internet Stream - Offline")
        self.status_label.setStyleSheet("color: #aaa; font-size: 12px;")
        
        info_v = QVBoxLayout()
        info_v.addWidget(self.track_name_label)
        info_v.addWidget(self.status_label)
        self.footer_layout.addLayout(info_v)
        
        self.footer_layout.addStretch(1)
        
        # Center Controls
        ctrl_layout = QHBoxLayout()
        self.btn_play = PrimaryPushButton(FIF.PLAY, "")
        self.btn_pause = TransparentPushButton(FIF.PAUSE, "")
        self.btn_pause.hide()
        
        self.btn_play.clicked.connect(self.player.play)
        self.btn_pause.clicked.connect(self.player.pause)
        self.player.errorOccurred.connect(self.handle_error)
        
        ctrl_layout.addWidget(self.btn_play)
        ctrl_layout.addWidget(self.btn_pause)
        self.footer_layout.addLayout(ctrl_layout)
        
        self.footer_layout.addStretch(1)
        
        # Right Vol
        vol_icon = IconWidget(FIF.VOLUME)
        vol_icon.setFixedSize(14, 14)
        self.volume_slider = Slider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.valueChanged.connect(self.change_volume)
        self.footer_layout.addWidget(vol_icon)
        self.footer_layout.addWidget(self.volume_slider)
        
        # Signals
        self.player.playbackStateChanged.connect(self.handle_playback_change)

        self.stations = []
        self.load_playlist()

    def handle_error(self, error, error_str):
        self.status_label.setText("Connection failed.")
        self.btn_play.show()
        self.btn_pause.hide()

    def handle_playback_change(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.btn_play.hide()
            self.btn_pause.show()
            self.status_label.setText("Streaming Live...")
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self.btn_play.show()
            self.btn_pause.hide()
            self.status_label.setText("Stream Paused")
        else:
            self.btn_play.show()
            self.btn_pause.hide()
            if self.status_label.text() != "Connection failed.":
                self.status_label.setText("Stream Stopped")

    def change_volume(self, value):
        self.audio_output.setVolume(value / 100.0)

    def filter_playlist(self, text):
        search_text = text.lower()
        for i in range(self.playlist_widget.count()):
            item = self.playlist_widget.item(i)
            widget = self.playlist_widget.itemWidget(item)
            if widget:
                matches = search_text in widget.name.lower() or search_text in widget.url.lower()
                item.setHidden(not matches)

    def add_station(self):
        name, ok1 = QInputDialog.getText(self, "Add Radio Station", "Enter Station Name:")
        if ok1 and name.strip():
            url, ok2 = QInputDialog.getText(self, "Add Radio Station", "Enter Stream URL:")
            if ok2 and url.strip():
                self.stations.append({"name": name.strip(), "url": url.strip()})
                self.refresh_list()
                self.save_playlist()

    def clear_playlist(self):
        self.stations = []
        self.refresh_list()
        self.save_playlist()

    def refresh_list(self):
        self.playlist_widget.clear()
        for stat in self.stations:
            item = QListWidgetItem()
            sw = RadioItemWidget(stat['name'], stat['url'])
            # Store data in item for retrieval
            item.setData(Qt.UserRole, stat['url'])
            item.setData(Qt.UserRole + 1, stat['name'])
            item.setSizeHint(sw.sizeHint())
            self.playlist_widget.addItem(item)
            self.playlist_widget.setItemWidget(item, sw)

    def save_playlist(self):
        with open(RADIOS_FILE, "w") as f:
            json.dump(self.stations, f)

    def load_playlist(self):
        if os.path.exists(RADIOS_FILE):
            try:
                with open(RADIOS_FILE, "r") as f:
                    self.stations = json.load(f)
            except:
                self.stations = []
        else:
            # Added some defaults automatically for immediate immersion!
            self.stations = [
                {"name": "Lofi Radio (Deep Focus)", "url": "http://stream.zeno.fm/f3wvbbqmdg8uv"},
                {"name": "Classical Radio - Mozart & Beethoven", "url": "http://strm112.1.fm/classical_mobile_mp3"},
                {"name": "Synthwave Retro Radio", "url": "https://nrj.fastcast4u.com/proxy/nrj?mp=/1"}
            ]
            self.save_playlist()
        self.refresh_list()

    def play_selected_track(self, item):
        if not item:
            return
        url = item.data(Qt.UserRole)
        name = item.data(Qt.UserRole + 1)
        self.track_name_label.setText(name)
        self.status_label.setText("Connecting...")
        self.player.setSource(QUrl(url))
        self.player.play()
