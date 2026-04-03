import os
import random
from PySide6.QtCore import Qt, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, 
                             QListWidget, QListWidgetItem)
from qfluentwidgets import (SubtitleLabel, PrimaryPushButton, TransparentPushButton, 
                            Slider, IconWidget, FluentIcon as FIF, ScrollArea, BodyLabel, 
                            SegmentedWidget)

# Playback Modes
LOOP_ALL = 0
LOOP_ONE = 1
SHUFFLE = 2

class MusicInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("MusicInterface")
        self.setStyleSheet("background: transparent;")
        
        self.playback_mode = LOOP_ALL
        
        # Audio Engine
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.5)
        self.player.mediaStatusChanged.connect(self.handle_media_status)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(40, 40, 40, 40)
        self.layout.setSpacing(20)
        
        # Header
        self.title = SubtitleLabel("Music Hub", self)
        self.title.setStyleSheet("font-size: 28px; font-weight: bold;")
        self.layout.addWidget(self.title)
        
        # Now Playing Area
        self.now_playing_card = QWidget()
        self.now_playing_card.setStyleSheet("""
            background: rgba(0, 0, 0, 0.5); 
            border-radius: 10px; 
            border: 1px solid rgba(255, 255, 255, 0.1);
        """)
        self.np_layout = QVBoxLayout(self.now_playing_card)
        self.np_layout.setContentsMargins(20, 20, 20, 20)
        
        self.track_name_label = BodyLabel("No Track Selected")
        self.track_name_label.setStyleSheet("font-size: 16px; font-weight: 500;")
        self.np_layout.addWidget(self.track_name_label, alignment=Qt.AlignCenter)
        
        # Controls
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(15)
        ctrl_layout.setAlignment(Qt.AlignCenter)
        
        self.btn_prev = TransparentPushButton(FIF.SKIP_BACK, "")
        self.btn_play = PrimaryPushButton(FIF.PLAY, "")
        self.btn_pause = TransparentPushButton(FIF.PAUSE, "")
        self.btn_next = TransparentPushButton(FIF.SKIP_FORWARD, "")
        
        self.btn_play.clicked.connect(self.player.play)
        self.btn_pause.clicked.connect(self.player.pause)
        self.btn_prev.clicked.connect(self.play_previous)
        self.btn_next.clicked.connect(self.play_next_manual)
        
        ctrl_layout.addWidget(self.btn_prev)
        ctrl_layout.addWidget(self.btn_play)
        ctrl_layout.addWidget(self.btn_pause)
        ctrl_layout.addWidget(self.btn_next)
        self.np_layout.addLayout(ctrl_layout)
        
        # Mode Toggle Row
        self.mode_layout = QHBoxLayout()
        self.mode_layout.setAlignment(Qt.AlignCenter)
        self.mode_tabs = SegmentedWidget()
        self.mode_tabs.addItem(str(LOOP_ALL), "Loop All")
        self.mode_tabs.addItem(str(LOOP_ONE), "Loop 1")
        self.mode_tabs.addItem(str(SHUFFLE), "Shuffle")
        self.mode_tabs.setCurrentItem(str(LOOP_ALL))
        self.mode_tabs.currentItemChanged.connect(self.change_mode)
        
        self.mode_layout.addWidget(self.mode_tabs)
        self.np_layout.addLayout(self.mode_layout)
        
        self.layout.addWidget(self.now_playing_card)
        
        # Playlist Area
        self.playlist_widget = QListWidget()
        self.playlist_widget.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                color: #ddd;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid rgba(255,255,255,0.05);
            }
            QListWidget::item:selected {
                background: rgba(0, 120, 215, 0.2);
                color: white;
            }
        """)
        self.playlist_widget.itemDoubleClicked.connect(self.play_selected_track)
        self.layout.addWidget(self.playlist_widget)
        
        # Bottom Buttons
        bottom_layout = QHBoxLayout()
        self.btn_clear = TransparentPushButton(FIF.DELETE, "Clear Playlist")
        self.btn_clear.clicked.connect(self.clear_playlist)
        self.btn_add = PrimaryPushButton(FIF.MUSIC, "Import Music", self)
        self.btn_add.clicked.connect(self.import_music)
        
        bottom_layout.addWidget(self.btn_clear)
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(self.btn_add)
        self.layout.addLayout(bottom_layout)
        
        self.load_playlist()

    def change_mode(self, item_key):
        self.playback_mode = int(item_key)

    def handle_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.play_next_auto()

    def play_next_auto(self):
        if self.playlist_widget.count() == 0:
            return
            
        if self.playback_mode == LOOP_ONE:
            self.play_selected_track(self.playlist_widget.currentItem())
        elif self.playback_mode == SHUFFLE:
            idx = random.randint(0, self.playlist_widget.count() - 1)
            self.playlist_widget.setCurrentRow(idx)
            self.play_selected_track(self.playlist_widget.currentItem())
        else: # LOOP_ALL
            next_row = (self.playlist_widget.currentRow() + 1) % self.playlist_widget.count()
            self.playlist_widget.setCurrentRow(next_row)
            self.play_selected_track(self.playlist_widget.currentItem())

    def play_next_manual(self):
        if self.playlist_widget.count() == 0:
            return
        next_row = (self.playlist_widget.currentRow() + 1) % self.playlist_widget.count()
        self.playlist_widget.setCurrentRow(next_row)
        self.play_selected_track(self.playlist_widget.currentItem())

    def play_previous(self):
        if self.playlist_widget.count() == 0:
            return
        prev_row = (self.playlist_widget.currentRow() - 1) % self.playlist_widget.count()
        self.playlist_widget.setCurrentRow(prev_row)
        self.play_selected_track(self.playlist_widget.currentItem())

    def import_music(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Import Tracks", "", "Audio Files (*.mp3 *.wav *.m4a)")
        for f in files:
            item = QListWidgetItem(os.path.basename(f))
            item.setData(Qt.UserRole, f)
            self.playlist_widget.addItem(item)
        self.save_playlist()

    def play_selected_track(self, item):
        if not item:
            return
        path = item.data(Qt.UserRole)
        if os.path.exists(path):
            self.player.setSource(QUrl.fromLocalFile(path))
            self.track_name_label.setText(item.text())
            self.player.play()
            self.playlist_widget.setCurrentItem(item)
        else:
            self.track_name_label.setText("File not found.")

    def clear_playlist(self):
        self.playlist_widget.clear()
        self.save_playlist()

    def save_playlist(self):
        with open(".notak_playlist", "w") as f:
            for i in range(self.playlist_widget.count()):
                path = self.playlist_widget.item(i).data(Qt.UserRole)
                f.write(path + "\n")

    def load_playlist(self):
        if os.path.exists(".notak_playlist"):
            try:
                with open(".notak_playlist", "r") as f:
                    paths = [line.strip() for line in f.readlines()]
                    for p in paths:
                        if os.path.exists(p):
                            item = QListWidgetItem(os.path.basename(p))
                            item.setData(Qt.UserRole, p)
                            self.playlist_widget.addItem(item)
            except:
                pass
