from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSpacerItem, QSizePolicy
from qfluentwidgets import (SubtitleLabel, LineEdit, PasswordLineEdit, PrimaryPushButton, 
                            TextBrowser, InfoBar, InfoBarPosition, CaptionLabel, IconWidget, FluentIcon as FIF)

from core.supabase_service import SupabaseService

class LoginView(QWidget):
    login_success = Signal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.supabase = SupabaseService()
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignCenter)
        
        # Centered Container
        self.card = QWidget()
        self.card.setFixedWidth(360)
        self.card.setStyleSheet("background: rgba(0,0,0,0.3); border-radius: 15px; border: 1px solid rgba(255,255,255,0.05);")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(30, 40, 30, 40)
        card_layout.setSpacing(15)
        
        # Logo/Icon
        icon_h = QHBoxLayout()
        icon_h.addStretch()
        self.logo = IconWidget(FIF.GLOBE)
        self.logo.setFixedSize(48, 48)
        icon_h.addWidget(self.logo)
        icon_h.addStretch()
        card_layout.addLayout(icon_h)
        
        self.title = SubtitleLabel("HydraSpace Login")
        self.title.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self.title)
        
        self.desc = CaptionLabel("Study online. Focus offline.")
        self.desc.setAlignment(Qt.AlignCenter)
        self.desc.setStyleSheet("color: gray;")
        card_layout.addWidget(self.desc)
        
        card_layout.addSpacing(10)
        
        # Inputs
        self.email_input = LineEdit()
        self.email_input.setPlaceholderText("Email Address")
        card_layout.addWidget(self.email_input)
        
        self.pass_input = PasswordLineEdit()
        self.pass_input.setPlaceholderText("Password")
        card_layout.addWidget(self.pass_input)
        
        card_layout.addSpacing(10)
        
        # Login Button
        self.btn_login = PrimaryPushButton("Sign In")
        self.btn_login.clicked.connect(self.handle_login)
        card_layout.addWidget(self.btn_login)
        
        self.main_layout.addWidget(self.card)

    def handle_login(self):
        email = self.email_input.text()
        password = self.pass_input.text()
        
        if not email or not password:
            self.show_error("Please enter email and password.")
            return
            
        self.btn_login.setEnabled(False)
        self.btn_login.setText("Signing in...")
        
        success, message = self.supabase.sign_in(email, password)
        
        if success:
            self.login_success.emit()
        else:
            self.show_error(f"Login failed: {message}")
            self.btn_login.setEnabled(True)
            self.btn_login.setText("Sign In")

    def show_error(self, message):
        InfoBar.error(
            title='Authentication Error',
            content=message,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self.window()
        )
