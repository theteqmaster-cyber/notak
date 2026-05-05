import os
from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel

from qfluentwidgets import (ScrollArea, TitleLabel, PrimaryPushButton,
                            SubtitleLabel, IconWidget, FluentIcon as FIF,
                            BodyLabel, CardWidget, RoundMenu, Action)

from core.database import get_connection
from core.importer import split_filename_for_display
from gui.components.marquee_label import MarqueeLabel

from core.canvas_engine import CanvasManager
from gui.interfaces.canvas_editor import MboardEditor

def get_mboard_files():
    manager = CanvasManager()
    return manager.get_all_boards()

class NoteiInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("MboardInterface")
        self.manager = CanvasManager()
        self.editor = None
        self.setStyleSheet("background: transparent;")
        
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(40, 40, 40, 40)
        self.vBoxLayout.setSpacing(20)
        self.vBoxLayout.setAlignment(Qt.AlignTop)
        
        # Header Area
        header_layout = QHBoxLayout()
        self.title_label = TitleLabel("Mboard - Visual Workspace", self)
        self.title_label.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch(1)
        
        self.btn_note = PrimaryPushButton(FIF.ADD, "New Board", self)
        self.btn_note.clicked.connect(self.create_new_board)
        header_layout.addWidget(self.btn_note)
        
        self.vBoxLayout.addLayout(header_layout)
        
        self.sub_header = BodyLabel("Your personal space for visual thinking, mind maps, and concept boards.", self)
        self.sub_header.setStyleSheet("color: #aaaaaa;")
        self.vBoxLayout.addWidget(self.sub_header)
        
        self.vBoxLayout.addSpacing(20)
        
        # Gallery Area
        self.scroll_area = ScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("ScrollArea { background-color: transparent; border: none; }")
        
        self.gallery_widget = QWidget()
        self.gallery_widget.setStyleSheet("background-color: transparent;")
        
        self.gallery_layout = QGridLayout(self.gallery_widget)
        self.gallery_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.gallery_layout.setSpacing(20)
        
        self.scroll_area.setWidget(self.gallery_widget)
        self.vBoxLayout.addWidget(self.scroll_area)
        
    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_gallery()

    def create_new_board(self):
        path = self.manager.create_board("Untitled Board")
        self.open_board(path)

    def open_board(self, path):
        try:
            print(f"DEBUG: Opening board at {path}")
            # Create editor if not exists or update it
            if not self.editor:
                win = self.window()
                self.editor = MboardEditor(path, win)
                self.editor.closed.connect(self.refresh_gallery)
                
                # Make it a popup overlay if no window found, or full size
                if win:
                    self.editor.resize(win.size())
                    self.editor.move(0, 0)
                else:
                    self.editor.resize(1100, 800)
                
            self.editor.board_path = path
            self.editor.data = self.manager.load_board(path)
            self.editor.title_edit.setText(self.editor.data.title)
            self.editor.load_elements_into_scene()
            self.editor.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
            self.editor.showFullScreen() if self.window() and self.window().isFullScreen() else self.editor.show()
            self.editor.raise_()
        except Exception as e:
            print(f"ERROR: Failed to open board: {e}")
            import traceback
            traceback.print_exc()

    def refresh_gallery(self):
        
        # Clear existing
        for i in reversed(range(self.gallery_layout.count())): 
            widget = self.gallery_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
                
        boards = get_mboard_files()
        if not boards:
            empty = SubtitleLabel("No boards yet. Create your first concept map!", self)
            empty.setStyleSheet("color: #555;")
            self.gallery_layout.addWidget(empty, 0, 0)
            return

        row, col = 0, 0
        max_cols = 5
        for b in boards:
            card = CardWidget(self)
            card.setFixedSize(180, 240)
            card.setCursor(Qt.PointingHandCursor)
            card.setStyleSheet("""
                CardWidget {
                    background: rgba(45, 45, 45, 0.4);
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    border-radius: 12px;
                }
                CardWidget:hover {
                    background: rgba(60, 60, 60, 0.6);
                    border: 1px solid rgba(0, 210, 255, 0.3);
                }
            """)
            
            # Use local lambda or a proper method for signals
            # Handle clicks
            card_path = b['path']
            card.mousePressEvent = lambda e, p=card_path: self.on_card_click(e, p)
            
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(10, 10, 10, 10)
            c_layout.setSpacing(10)
            
            # Preview Area
            preview_container = QWidget()
            preview_container.setFixedSize(160, 160)
            preview_container.setStyleSheet("background: #1e1e1e; border-radius: 8px;")
            p_layout = QVBoxLayout(preview_container)
            p_layout.setContentsMargins(0,0,0,0)
            
            thumb_path = b['path'].replace(".mboard", ".png")
            if os.path.exists(thumb_path):
                img_lbl = QLabel()
                pm = QPixmap(thumb_path)
                img_lbl.setPixmap(pm.scaled(160, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                img_lbl.setAlignment(Qt.AlignCenter)
                p_layout.addWidget(img_lbl)
            else:
                icon_widget = IconWidget(FIF.LAYOUT)
                icon_widget.setFixedSize(60, 60)
                p_layout.addWidget(icon_widget, alignment=Qt.AlignCenter)
            
            c_layout.addWidget(preview_container)
            
            name = MarqueeLabel(b['name'])
            name.setFixedWidth(150) 
            name.setAlignment(Qt.AlignCenter)
            name.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: bold; background: transparent; border: none;")
            c_layout.addWidget(name)
            
            mtime = datetime.fromtimestamp(b['mtime']).strftime("%Y-%m-%d")
            time_lbl = SubtitleLabel(mtime)
            time_lbl.setAlignment(Qt.AlignCenter)
            time_lbl.setStyleSheet("color: #888; font-size: 11px;")
            c_layout.addWidget(time_lbl)
            
            self.gallery_layout.addWidget(card, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def on_card_click(self, event, path):
        if event.button() == Qt.LeftButton:
            self.open_board(path)
        elif event.button() == Qt.RightButton:
            self.show_card_menu(event.globalPos(), path)

    def show_card_menu(self, pos, path):
        menu = RoundMenu(parent=self)
        delete_action = Action(FIF.DELETE, "Move to Recycle Bin", self)
        delete_action.triggered.connect(lambda: self.delete_board(path))
        menu.addAction(delete_action)
        menu.exec(pos)

    def delete_board(self, path):
        # Move to .recycle folder
        vault_path = os.path.dirname(os.path.dirname(path))
        recycle_dir = os.path.join(vault_path, ".recycle")
        if not os.path.exists(recycle_dir):
            os.makedirs(recycle_dir)
        
        filename = os.path.basename(path)
        dest = os.path.join(recycle_dir, filename)
        
        # Move .mboard and .png (thumbnail)
        try:
            if os.path.exists(path):
                os.rename(path, dest)
            
            thumb = path.replace(".mboard", ".png")
            if os.path.exists(thumb):
                os.rename(thumb, os.path.join(recycle_dir, os.path.basename(thumb)))
                
            from qfluentwidgets import InfoBar
            InfoBar.success("Board Moved", f"{filename} moved to Recycle Bin.", parent=self)
            self.refresh_gallery()
        except Exception as e:
            from qfluentwidgets import InfoBar
            InfoBar.error("Error", f"Could not delete board: {e}", parent=self)
