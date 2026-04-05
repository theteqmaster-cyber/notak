import os
import subprocess
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea
from qfluentwidgets import (TitleLabel, SubtitleLabel, BodyLabel, CaptionLabel, 
                            TransparentPushButton, FluentIcon as FIF, IconWidget, CardWidget,
                            StrongBodyLabel)

class AboutInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("AboutInterface")
        self.setStyleSheet("background: transparent;")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(60, 60, 60, 60)
        main_layout.setSpacing(40)
        main_layout.setAlignment(Qt.AlignTop)

        # --- Hero Section ---
        hero_layout = QVBoxLayout()
        hero_layout.setSpacing(10)
        
        self.title_label = TitleLabel("NOTAK STUDY HUB", self)
        self.title_label.setStyleSheet("font-size: 56px; font-weight: 900; color: white; letter-spacing: -2px;")
        hero_layout.addWidget(self.title_label)
        
        self.version_label = CaptionLabel("Version 2.0 - Crystal Edition")
        self.version_label.setStyleSheet("color: #0078d4; font-weight: bold; letter-spacing: 2px;")
        hero_layout.addWidget(self.version_label)
        
        main_layout.addLayout(hero_layout)

        # --- Content Grid ---
        grid_layout = QHBoxLayout()
        grid_layout.setSpacing(30)

        # 1. Why Notak?
        why_card = self.create_info_card("WHY NOTAK?", 
            "The university journey is a mess of spaghetti notes and scattered resources. "
            "Notak was built to be the container—the sanctuary—where focus meets elegance. "
            "It's not just a note taker; it's a mental space.")
        grid_layout.addWidget(why_card)

        # 2. Who is it for?
        for_card = self.create_info_card("WHO IS IT FOR?", 
            "Designed for the high-achieving student, the meticulous researcher, and the "
            "deep-thinker. If you feel like your digital notes are a maze, Notak is the exit.")
        grid_layout.addWidget(for_card)
        
        main_layout.addLayout(grid_layout)

        # --- Developer Spotlight ---
        dev_card = CardWidget(self)
        dev_card.setStyleSheet("""
            CardWidget {
                background: rgba(0, 0, 0, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 20px;
            }
        """)
        dev_layout = QHBoxLayout(dev_card)
        dev_layout.setContentsMargins(30, 30, 30, 30)
        dev_layout.setSpacing(30)

        # Profile Icon / Placeholder
        self.dev_icon = IconWidget(FIF.PEOPLE)
        self.dev_icon.setFixedSize(80, 80)
        self.dev_icon.setStyleSheet("color: white;")
        dev_layout.addWidget(self.dev_icon)

        # Dev Info
        info_v = QVBoxLayout()
        info_v.setSpacing(5)
        
        dev_name = SubtitleLabel("Mphathisi Ndlovu")
        dev_name.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        dev_tag = BodyLabel("@theteqmaster")
        dev_tag.setStyleSheet("color: #0078d4;")
        
        info_v.addWidget(dev_name)
        info_v.addWidget(dev_tag)
        info_v.addWidget(BodyLabel("Creator & Lead Architect of the Notak ecosystem."))
        dev_layout.addLayout(info_v)
        
        dev_layout.addStretch(1)

        # Social Buttons
        btn_v = QVBoxLayout()
        self.btn_email = TransparentPushButton(FIF.MESSAGE, "theteqmaster@gmail.com")
        self.btn_web = TransparentPushButton(FIF.GLOBE, "Portfolio Website")
        
        for btn in [self.btn_email, self.btn_web]:
            btn.setFixedWidth(220)
            btn_v.addWidget(btn)
        
        self.btn_email.clicked.connect(lambda: self.open_link("mailto:theteqmaster@gmail.com"))
        self.btn_web.clicked.connect(lambda: self.open_link("https://portfolio-site-for-mphatic-teqmaste.vercel.app/"))
        
        dev_layout.addLayout(btn_v)
        
        main_layout.addWidget(dev_card)

    def create_info_card(self, title, content):
        card = CardWidget(self)
        card.setStyleSheet("""
            CardWidget {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
            }
        """)
        v = QVBoxLayout(card)
        v.setContentsMargins(20, 20, 20, 20)
        v.setSpacing(10)
        
        t_lbl = StrongBodyLabel(title)
        t_lbl.setStyleSheet("color: #0078d4; letter-spacing: 1px;")
        c_lbl = BodyLabel(content)
        c_lbl.setWordWrap(True)
        c_lbl.setStyleSheet("color: #eee; line-height: 1.5;")
        
        v.addWidget(t_lbl)
        v.addWidget(c_lbl)
        return card

    def open_link(self, url):
        try:
            subprocess.Popen(['xdg-open', url])
        except:
            pass
