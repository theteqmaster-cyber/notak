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
import json
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
from mutagen.mp4 import MP4
from io import BytesIO

from gui.components.marquee_label import MarqueeLabel

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
        
        # MARQUEE ACTION for Song Titles in List
        self.title_lbl = MarqueeLabel(os.path.basename(path))
        self.title_lbl.setFixedWidth(200)
        self.title_lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: #eee; background: transparent;")
        
        self.artist_lbl = MarqueeLabel("Unknown Artist")
        self.artist_lbl.setFixedWidth(200)
        self.artist_lbl.setStyleSheet("color: #aaa; font-size: 12px;")
        info.addWidget(self.title_lbl)
        info.addWidget(self.artist_lbl)
        self.layout.addLayout(info)
        
        self.layout.addStretch(1)
        
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
        except: pass

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
        
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.5)
        self.player.mediaStatusChanged.connect(self.handle_media_status)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(40, 40, 40, 40)
        self.layout.setSpacing(20)
        
        header_h = QHBoxLayout()
        header_h.setContentsMargins(0, 0, 0, 10)
        self.title = SubtitleLabel("Music Hub")
        self.title.setStyleSheet("font-size: 26px; font-weight: bold; color: white;")
        header_h.addWidget(self.title)
        header_h.addStretch(1)
        
        self.song_search = SearchLineEdit()
        self.song_search.setFixedWidth(200)
        self.song_search.textChanged.connect(self.filter_playlist)
        header_h.addWidget(self.song_search)
        

        self.btn_clear = TransparentPushButton(FIF.DELETE, "Clear")
        self.btn_clear.clicked.connect(self.clear_playlist)
        self.btn_add = PrimaryPushButton(FIF.MUSIC, "Import Music")
        self.btn_add.clicked.connect(self.import_music)

        header_h.addWidget(self.btn_clear)
        header_h.addWidget(self.btn_add)
        self.layout.addLayout(header_h)
        
        self.playlist_widget = QListWidget()
        self.playlist_widget.setStyleSheet("""
            QListWidget { background: rgba(0, 0, 0, 0.3); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; }
            QListWidget::item { background: rgba(255,255,255,0.05); margin-bottom: 4px; border-radius: 8px; }
            QListWidget::item:selected { background: rgba(0, 120, 215, 0.25); border-left: 4px solid #0078d7; }
        """)
        self.playlist_widget.itemDoubleClicked.connect(self.play_selected_track)
        self.layout.addWidget(self.playlist_widget, 1)
        
        self.now_playing_card = QWidget()
        self.now_playing_card.setFixedHeight(120) 
        self.now_playing_card.setStyleSheet("background: rgba(0, 0, 0, 0.85); border-radius: 12px; border: none;")
        self.layout.addWidget(self.now_playing_card)
        
        self.footer_layout = QHBoxLayout(self.now_playing_card)
        self.footer_layout.setContentsMargins(15, 10, 15, 10)
        self.footer_layout.setSpacing(20)
        
        # --- LEFT: TRACK INFO (MARQUEE) ---
        left_box = QWidget()
        left_box.setFixedWidth(280) # RIGID WIDTH for footer track info
        left_layout = QHBoxLayout(left_box)
        left_layout.setContentsMargins(0,0,0,0)
        
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(60, 60)
        self.cover_label.setStyleSheet("border-radius: 6px; background: transparent;")
        left_layout.addWidget(self.cover_label)
        
        track_info_v = QVBoxLayout()
        track_info_v.setContentsMargins(10,0,0,0)
        
        # MARQUEE for Playback bar
        self.track_name_label = MarqueeLabel("No Track Selected")
        self.track_name_label.setFixedWidth(220)
        self.track_name_label.setStyleSheet("font-size: 15px; font-weight: bold; color: white; background: transparent;")
        self.track_name_label.always_scroll = True
        
        self.artist_label = MarqueeLabel("Unknown Artist")
        self.artist_label.setFixedWidth(220)
        self.artist_label.setStyleSheet("color: #aaa; font-size: 12px; background: transparent;")
        self.artist_label.always_scroll = True
        
        track_info_v.addWidget(self.track_name_label)
        track_info_v.addWidget(self.artist_label)
        left_layout.addLayout(track_info_v)
        self.footer_layout.addWidget(left_box)
        
        # --- CENTER: CONTROLS ---
        center_box = QWidget()
        center_v = QVBoxLayout(center_box)
        ctrl_layout = QHBoxLayout()
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
        
        prog_row = QHBoxLayout()
        self.current_time_label = CaptionLabel("00:00")
        self.total_time_label = CaptionLabel("00:00")
        self.progress_slider = Slider(Qt.Horizontal)
        self.progress_slider.sliderMoved.connect(self.seek_position)
        prog_row.addWidget(self.current_time_label)
        prog_row.addWidget(self.progress_slider)
        prog_row.addWidget(self.total_time_label)
        center_v.addLayout(prog_row)
        self.footer_layout.addWidget(center_box, 1)
        
        # --- RIGHT: SETTINGS ---
        right_box = QWidget()
        right_layout = QHBoxLayout(right_box)
        self.mode_tabs = SegmentedWidget()
        self.mode_tabs.setFixedWidth(180)
        self.mode_tabs.addItem(str(LOOP_ALL), "L")
        self.mode_tabs.addItem(str(LOOP_ONE), "1")
        self.mode_tabs.addItem(str(SHUFFLE), "S")
        self.mode_tabs.setCurrentItem(str(LOOP_ALL))
        self.mode_tabs.currentItemChanged.connect(self.change_mode)
        right_layout.addWidget(self.mode_tabs)
        
        self.volume_slider = Slider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setFixedWidth(80)
        self.volume_slider.valueChanged.connect(self.change_volume)
        right_layout.addWidget(IconWidget(FIF.VOLUME))
        right_layout.addWidget(self.volume_slider)
        self.footer_layout.addWidget(right_box)

        self.load_playlist()
        self.player.positionChanged.connect(self.update_position)
        self.player.durationChanged.connect(self.update_duration)
        self.player.playbackStateChanged.connect(self.handle_playback_change)

    def filter_playlist(self, text):
        search_text = text.lower()
        for i in range(self.playlist_widget.count()):
            item = self.playlist_widget.item(i)
            widget = self.playlist_widget.itemWidget(item)
            if widget: item.setHidden(not (search_text in widget.path.lower() or search_text in widget.title_lbl.text_content.lower()))

    def handle_playback_change(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.btn_play.hide(); self.btn_pause.show()
        else:
            self.btn_play.show(); self.btn_pause.hide()

    def change_volume(self, value): self.audio_output.setVolume(value / 100.0)
    def update_position(self, pos):
        if not self.progress_slider.isSliderDown(): self.progress_slider.setValue(pos)
        self.current_time_label.setText(self.format_time(pos))
    def update_duration(self, dur):
        self.progress_slider.setRange(0, dur)
        self.total_time_label.setText(self.format_time(dur))
    def seek_position(self, pos): self.player.setPosition(pos)
    def format_time(self, ms):
        s = (ms // 1000) % 60; m = (ms // (1000 * 60)) % 60; return f"{m:02}:{s:02}"
    def change_mode(self, key): self.playback_mode = int(key)
    def handle_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia: self.play_next_auto()
    def play_next_auto(self):
        if self.playlist_widget.count() == 0: return
        
        if self.playback_mode == LOOP_ONE:
            self.player.setPosition(0)
            self.player.play()
            return

        self.play_next_manual()

    def play_next_manual(self): 
        if self.playlist_widget.count() == 0: return
        
        if self.playback_mode == SHUFFLE and self.playlist_widget.count() > 1:
            next_row = random.randint(0, self.playlist_widget.count() - 1)
            while next_row == self.playlist_widget.currentRow():
                next_row = random.randint(0, self.playlist_widget.count() - 1)
        else:
            next_row = (self.playlist_widget.currentRow() + 1) % self.playlist_widget.count()
            
        self.playlist_widget.setCurrentRow(next_row)
        self.play_selected_track(self.playlist_widget.currentItem())

    def play_previous(self):
        if self.playlist_widget.count() == 0: return
        prev_row = (self.playlist_widget.currentRow() - 1) % self.playlist_widget.count()
        self.playlist_widget.setCurrentRow(prev_row)
        self.play_selected_track(self.playlist_widget.currentItem())
    def import_music(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Import Tracks", "", "Audio Files (*.mp3 *.wav *.m4a)")
        for f in files:
            item = QListWidgetItem(); item.setData(Qt.UserRole, f)
            sw = SongItemWidget(f); item.setSizeHint(sw.sizeHint())
            self.playlist_widget.addItem(item); self.playlist_widget.setItemWidget(item, sw)
        self.save_playlist()
    def play_selected_track(self, item):
        if not item: return
        path = item.data(Qt.UserRole)
        if os.path.exists(path):
            self.player.setSource(QUrl.fromLocalFile(path))
            self.update_metadata(path)
            self.player.play()
            self.update_song_stats(path)

    def update_song_stats(self, path):
        # Update timestamp and increment play count
        playlist = self._read_playlist_data()
        now = datetime.datetime.now().isoformat()
        found = False
        for entry in playlist:
            if entry['path'] == path:
                entry['last_played'] = now
                # Initialize play_count if it doesn't exist, then increment
                entry['play_count'] = entry.get('play_count', 0) + 1
                found = True
                break
        if not found:
            playlist.append({'path': path, 'last_played': now, 'play_count': 1})
        
        self.save_playlist_data(playlist)
        
        # We don't want to re-order the UI IMMEDIATELY while something is playing
        # because it resets the currentIndex and breaks 'Next' button flow (creates a 2-song loop).
        # The re-sorting will happen when the playlist is reloaded or if we explicitly refresh it.
        # For now, let's just make sure the current item remains selected without resetting row to 0.
        pass

    def update_metadata(self, path):
        self.track_name_label.setText(os.path.basename(path))
        self.artist_label.setText("Unknown Artist")
        self.cover_label.setPixmap(QPixmap())
        try:
            if path.endswith('.mp3'):
                audio = MP3(path, ID3=ID3)
                if 'TIT2' in audio: self.track_name_label.setText(str(audio['TIT2']))
                if 'TPE1' in audio: self.artist_label.setText(str(audio['TPE1']))
                for tag in audio.tags.values():
                    if isinstance(tag, APIC):
                        img = QPixmap()
                        img.loadFromData(tag.data)
                        self.cover_label.setPixmap(img.scaled(60, 60, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
                        break
            elif path.endswith('.m4a'):
                audio = MP4(path)
                if '\xa9nam' in audio: self.track_name_label.setText(audio['\xa9nam'][0])
                if '\xa9ART' in audio: self.artist_label.setText(audio['\xa9ART'][0])
                if 'covr' in audio:
                    img = QPixmap()
                    img.loadFromData(audio['covr'][0])
                    self.cover_label.setPixmap(img.scaled(60, 60, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
        except: pass

    def clear_playlist(self):
        self.playlist_widget.clear()
        if os.path.exists(".notak_playlist.json"):
            os.remove(".notak_playlist.json")
        if os.path.exists(".notak_playlist"):
            os.remove(".notak_playlist")

    def _read_playlist_data(self):
        if os.path.exists(".notak_playlist.json"):
            try:
                with open(".notak_playlist.json", "r") as f:
                    data = json.load(f)
                    # Migrating old data if play_count is missing
                    for entry in data:
                        if 'play_count' not in entry:
                            entry['play_count'] = 0
                    return data
            except: return []
        # Legacy support
        elif os.path.exists(".notak_playlist"):
            with open(".notak_playlist", "r") as f:
                return [{'path': p.strip(), 'last_played': '', 'play_count': 0} for p in f.readlines()]
        return []

    def save_playlist(self):
        playlist = []
        # Current paths in widget
        for i in range(self.playlist_widget.count()):
            path = self.playlist_widget.item(i).data(Qt.UserRole)
            playlist.append({'path': path, 'last_played': '', 'play_count': 0})
        
        # Merge with existing stats
        existing = {e['path']: (e.get('last_played', ''), e.get('play_count', 0)) for e in self._read_playlist_data()}
        for entry in playlist:
            if entry['path'] in existing:
                entry['last_played'], entry['play_count'] = existing[entry['path']]
        
        self.save_playlist_data(playlist)

    def save_playlist_data(self, data):
        with open(".notak_playlist.json", "w") as f:
            json.dump(data, f, indent=4)

    def load_playlist(self):
        data = self._read_playlist_data()
        # Sort by play_count descending (primary), then last_played descending (secondary)
        data.sort(key=lambda x: (x.get('play_count', 0), x.get('last_played', '')), reverse=True)
        
        self.playlist_widget.clear()
        for entry in data:
            p = entry['path']
            if os.path.exists(p):
                item = QListWidgetItem()
                item.setData(Qt.UserRole, p)
                sw = SongItemWidget(p)
                item.setSizeHint(sw.sizeHint())
                self.playlist_widget.addItem(item)
                self.playlist_widget.setItemWidget(item, sw)


