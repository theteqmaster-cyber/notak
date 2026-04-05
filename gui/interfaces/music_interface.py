import os
import random
from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, 
                             QListWidget, QListWidgetItem, QLabel)
from PySide6.QtGui import QPixmap
from qfluentwidgets import (SubtitleLabel, PrimaryPushButton, TransparentPushButton, 
                            Slider, IconWidget, FluentIcon as FIF, ScrollArea, BodyLabel, 
                            SegmentedWidget, CaptionLabel, CardWidget, SearchLineEdit)
import datetime
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
from mutagen.mp4 import MP4
from io import BytesIO

class SongItemWidget(QWidget):
    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = path
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(15, 8, 15, 8)
        self.layout.setSpacing(15)
        
        # Mini Art
        self.thumb = QLabel()
        self.thumb.setFixedSize(40, 40)
        self.thumb.setStyleSheet("border-radius: 4px; background: rgba(255,255,255,0.05);")
        self.layout.addWidget(self.thumb)
        
        # Info Stack
        info = QVBoxLayout()
        info.setSpacing(2)
        self.title_lbl = BodyLabel(os.path.basename(path))
        self.title_lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: #eee;")
        self.artist_lbl = CaptionLabel("Unknown Artist")
        self.artist_lbl.setStyleSheet("color: #aaa; font-size: 12px;")
        info.addWidget(self.title_lbl)
        info.addWidget(self.artist_lbl)
        self.layout.addLayout(info)
        
        self.layout.addStretch(1)
        
        # Duration
        self.dur_lbl = CaptionLabel("--:--")
        self.dur_lbl.setStyleSheet("color: #999; font-size: 12px;")
        self.layout.addWidget(self.dur_lbl)
        
        self.load_metadata()

    def load_metadata(self):
        try:
            if self.path.endswith('.mp3'):
                audio = MP3(self.path, ID3=ID3)
                if 'TIT2' in audio: self.title_lbl.setText(str(audio['TIT2']))
                if 'TPE1' in audio: self.artist_label_text = str(audio['TPE1'])
                else: self.artist_label_text = "Unknown Artist"
                self.artist_lbl.setText(self.artist_label_text)
                
                # Thumb
                for tag in audio.tags.values():
                    if isinstance(tag, APIC):
                        img = QPixmap()
                        img.loadFromData(tag.data)
                        self.thumb.setPixmap(img.scaled(40, 40, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
                        break
                self.set_duration(audio.info.length)
                
            elif self.path.endswith('.m4a'):
                audio = MP4(self.path)
                if '\xa9nam' in audio: self.title_lbl.setText(audio['\xa9nam'][0])
                if '\xa9ART' in audio: self.artist_lbl.setText(audio['\xa9ART'][0])
                if 'covr' in audio:
                    img = QPixmap()
                    img.loadFromData(audio['covr'][0])
                    self.thumb.setPixmap(img.scaled(40, 40, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
                self.set_duration(audio.info.length)
        except:
            pass

    def set_duration(self, length):
        mins = int(length // 60)
        secs = int(length % 60)
        self.dur_lbl.setText(f"{mins:02}:{secs:02}")

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
        
        # Header Area
        header_h = QHBoxLayout()
        header_h.setContentsMargins(0, 0, 0, 10)
        self.title = SubtitleLabel("Music Hub", self)
        self.title.setStyleSheet("font-size: 26px; font-weight: bold;")
        header_h.addWidget(self.title)
        header_h.addStretch(1)
        
        # Search Bar
        self.song_search = SearchLineEdit(self)
        self.song_search.setPlaceholderText("Search songs...")
        self.song_search.setFixedWidth(200)
        self.song_search.textChanged.connect(self.filter_playlist)
        header_h.addWidget(self.song_search)
        
        # Action Buttons moved to Header
        self.btn_clear = TransparentPushButton(FIF.DELETE, "Clear")
        self.btn_clear.clicked.connect(self.clear_playlist)
        self.btn_add = PrimaryPushButton(FIF.MUSIC, "Import Music", self)
        self.btn_add.clicked.connect(self.import_music)
        
        header_h.addWidget(self.btn_clear)
        header_h.addWidget(self.btn_add)
        
        self.layout.addLayout(header_h)
        
        # 1. Main Playlist Area In the Middle (Expanded)
        self.playlist_widget = QListWidget()
        self.playlist_widget.setObjectName("PlaylistWidget")
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
        self.layout.addWidget(self.playlist_widget, 1) # STRETCH=1 to fill
        
        # 2. Anchored Footer Area at the Bottom
        self.now_playing_card = QWidget()
        self.now_playing_card.setFixedHeight(120) 
        self.now_playing_card.setStyleSheet("""
            background: rgba(0, 0, 0, 0.85); 
            border-radius: 12px; 
            border: 1px solid rgba(255, 255, 255, 0.08); /* Minimal outer border */
        """)
        self.layout.addWidget(self.now_playing_card)
        
        # Main Footer Horizontal Layout
        self.footer_layout = QHBoxLayout(self.now_playing_card)
        self.footer_layout.setContentsMargins(15, 10, 15, 10)
        self.footer_layout.setSpacing(20)
        
        # --- LEFT: TRACK INFO ---
        left_box = QWidget()
        left_box.setStyleSheet("border: none; background: transparent;")
        left_layout = QHBoxLayout(left_box)
        left_layout.setContentsMargins(0,0,0,0)
        left_layout.setSpacing(15)
        
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(60, 60)
        self.cover_label.setStyleSheet("border-radius: 6px; background: transparent;")
        pix = QPixmap("assets/art/music_placeholder.png").scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.cover_label.setPixmap(pix)
        left_layout.addWidget(self.cover_label)
        
        track_info_v = QVBoxLayout()
        track_info_v.setContentsMargins(0,0,0,0)
        track_info_v.setSpacing(2)
        self.track_name_label = BodyLabel("No Track Selected")
        self.track_name_label.setStyleSheet("font-size: 15px; font-weight: bold; color: white;")
        self.artist_label = CaptionLabel("Unknown Artist")
        self.artist_label.setStyleSheet("color: #aaa; font-size: 12px;")
        
        self.viz_container = QWidget()
        self.viz_container.setFixedHeight(20)
        self.viz_layout = QHBoxLayout(self.viz_container)
        self.viz_layout.setContentsMargins(0,0,0,0)
        self.viz_layout.setSpacing(3)
        self.viz_bars = []
        for _ in range(8):
            bar = QWidget()
            bar.setFixedWidth(3)
            bar.setFixedHeight(3)
            bar.setStyleSheet("background: #0078d4; border-radius: 1px;")
            self.viz_bars.append(bar)
            self.viz_layout.addWidget(bar)
            
        track_info_v.addWidget(self.track_name_label)
        track_info_v.addWidget(self.artist_label)
        track_info_v.addWidget(self.viz_container)
        left_layout.addLayout(track_info_v)
        
        self.footer_layout.addWidget(left_box)
        
        # --- CENTER: CONTROLS & PROGRESS ---
        center_box = QWidget()
        center_box.setStyleSheet("border: none; background: transparent;")
        center_v = QVBoxLayout(center_box)
        center_v.setContentsMargins(0,0,0,0)
        center_v.setSpacing(5)
        
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
        center_v.addLayout(ctrl_layout)
        
        # Progress
        prog_row = QHBoxLayout()
        self.current_time_label = CaptionLabel("00:00")
        self.total_time_label = CaptionLabel("00:00")
        self.progress_slider = Slider(Qt.Horizontal)
        self.progress_slider.setRange(0, 100)
        self.progress_slider.sliderMoved.connect(self.seek_position)
        self.progress_slider.setStyleSheet("border: none;") # Remove outline
        prog_row.addWidget(self.current_time_label)
        prog_row.addWidget(self.progress_slider)
        prog_row.addWidget(self.total_time_label)
        center_v.addLayout(prog_row)
        
        self.footer_layout.addWidget(center_box, 1) # STRETCH=1
        
        # --- RIGHT: SETTINGS ---
        right_box = QWidget()
        right_box.setStyleSheet("border: none; background: transparent;")
        right_layout = QHBoxLayout(right_box)
        right_layout.setContentsMargins(0,0,0,0)
        right_layout.setSpacing(10)
        
        # Heart button
        self.btn_like = TransparentPushButton(FIF.HEART, "")
        self.btn_like.setCheckable(True)
        self.btn_like.setFixedSize(32, 32)
        right_layout.addWidget(self.btn_like)
        
        # Modes
        self.mode_tabs = SegmentedWidget()
        self.mode_tabs.setFixedWidth(180)
        self.mode_tabs.setStyleSheet("border: none; background: transparent;")
        self.mode_tabs.addItem(str(LOOP_ALL), "L")
        self.mode_tabs.addItem(str(LOOP_ONE), "1")
        self.mode_tabs.addItem(str(SHUFFLE), "S")
        self.mode_tabs.setCurrentItem(str(LOOP_ALL))
        self.mode_tabs.currentItemChanged.connect(self.change_mode)
        right_layout.addWidget(self.mode_tabs)
        
        # Vol
        vol_icon = IconWidget(FIF.VOLUME)
        vol_icon.setFixedSize(14, 14)
        self.volume_slider = Slider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setFixedWidth(80)
        self.volume_slider.valueChanged.connect(self.change_volume)
        self.volume_slider.setStyleSheet("border: none;") # Remove outline
        right_layout.addWidget(vol_icon)
        right_layout.addWidget(self.volume_slider)
        
        self.footer_layout.addWidget(right_box)

        self.load_playlist()

        # Visualizer Timer
        self.viz_timer = QTimer(self)
        self.viz_timer.timeout.connect(self.update_visualizer)
        self.viz_timer.start(100) # 10fps for smooth pulse
        
        # Connect multimedia signals
        self.player.positionChanged.connect(self.update_position)
        self.player.durationChanged.connect(self.update_duration)
        self.player.playbackStateChanged.connect(self.handle_playback_change)

    def filter_playlist(self, text):
        search_text = text.lower()
        for i in range(self.playlist_widget.count()):
            item = self.playlist_widget.item(i)
            widget = self.playlist_widget.itemWidget(item)
            if widget:
                matches = search_text in widget.path.lower() or search_text in widget.title_lbl.text().lower()
                item.setHidden(not matches)

    def update_visualizer(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            for bar in self.viz_bars:
                h = random.randint(5, 35)
                bar.setFixedHeight(h)
        else:
            for bar in self.viz_bars:
                bar.setFixedHeight(4)

    def handle_playback_change(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.btn_play.hide()
            self.btn_pause.show()
        else:
            self.btn_play.show()
            self.btn_pause.hide()

    def change_volume(self, value):
        self.audio_output.setVolume(value / 100.0)

    def update_position(self, position):
        if not self.progress_slider.isSliderDown():
            self.progress_slider.setValue(position)
        self.current_time_label.setText(self.format_time(position))

    def update_duration(self, duration):
        self.progress_slider.setRange(0, duration)
        self.total_time_label.setText(self.format_time(duration))

    def seek_position(self, position):
        self.player.setPosition(position)

    def format_time(self, ms):
        seconds = (ms // 1000) % 60
        minutes = (ms // (1000 * 60)) % 60
        return f"{minutes:02}:{seconds:02}"

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
            current = self.playlist_widget.currentRow()
            if self.playlist_widget.count() > 1:
                next_row = current
                while next_row == current:
                    next_row = random.randint(0, self.playlist_widget.count() - 1)
            else:
                next_row = 0
            self.playlist_widget.setCurrentRow(next_row)
            self.play_selected_track(self.playlist_widget.currentItem())
        else: # LOOP_ALL
            next_row = (self.playlist_widget.currentRow() + 1) % self.playlist_widget.count()
            self.playlist_widget.setCurrentRow(next_row)
            self.play_selected_track(self.playlist_widget.currentItem())

    def play_next_manual(self):
        if self.playlist_widget.count() == 0:
            return
            
        if self.playback_mode == SHUFFLE:
            # Pick a random track that isn't the current one if possible
            current = self.playlist_widget.currentRow()
            if self.playlist_widget.count() > 1:
                next_row = current
                while next_row == current:
                    next_row = random.randint(0, self.playlist_widget.count() - 1)
            else:
                next_row = 0
        else:
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
            # Create the custom widget
            item = QListWidgetItem()
            item.setData(Qt.UserRole, f)
            sw = SongItemWidget(f)
            item.setSizeHint(sw.sizeHint())
            self.playlist_widget.addItem(item)
            self.playlist_widget.setItemWidget(item, sw)
        self.save_playlist()

    def play_selected_track(self, item):
        if not item:
            return
        path = item.data(Qt.UserRole)
        if os.path.exists(path):
            self.player.setSource(QUrl.fromLocalFile(path))
            self.update_metadata(path)
            self.player.play()
            self.playlist_widget.setCurrentItem(item)
        else:
            self.track_name_label.setText("File not found.")

    def update_metadata(self, path):
        # Center Album Art Fix: Remove background, use KeepAspectRatio
        self.track_name_label.setText(os.path.basename(path))
        self.artist_label.setText("Unknown Artist")
        pix = QPixmap("assets/art/music_placeholder.png").scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.cover_label.setPixmap(pix)
        self.cover_label.setStyleSheet("border-radius: 6px; background: transparent;")
        
        try:
            if path.endswith('.mp3'):
                audio = MP3(path, ID3=ID3)
                if 'TIT2' in audio: self.track_name_label.setText(str(audio['TIT2']))
                if 'TPE1' in audio: self.artist_label.setText(str(audio['TPE1']))
                # Artwork
                for tag in audio.tags.values():
                    if isinstance(tag, APIC):
                        data = tag.data
                        img = QPixmap()
                        img.loadFromData(data)
                        self.cover_label.setPixmap(img.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                        break
            elif path.endswith('.m4a'):
                audio = MP4(path)
                if '\xa9nam' in audio: self.track_name_label.setText(audio['\xa9nam'][0])
                if '\xa9ART' in audio: self.artist_label.setText(audio['\xa9ART'][0])
                if 'covr' in audio:
                    data = audio['covr'][0]
                    img = QPixmap()
                    img.loadFromData(data)
                    self.cover_label.setPixmap(img.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception as e:
            print(f"Metadata error: {e}")

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
                            item = QListWidgetItem()
                            item.setData(Qt.UserRole, p)
                            sw = SongItemWidget(p)
                            item.setSizeHint(sw.sizeHint())
                            self.playlist_widget.addItem(item)
                            self.playlist_widget.setItemWidget(item, sw)
            except:
                pass
