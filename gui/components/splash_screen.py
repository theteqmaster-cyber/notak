from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QColor, QGuiApplication
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGraphicsDropShadowEffect
from qfluentwidgets import ProgressBar, SubtitleLabel

class SplashScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.setFixedSize(500, 450)
        
        # Main container with premium styling
        self.container = QWidget(self)
        self.container.setObjectName("SplashContainer")
        self.container.setStyleSheet("""
            #SplashContainer {
                background-color: #121212;
                border-radius: 30px;
                border: 1px solid #333;
            }
            QLabel {
                color: white;
            }
        """)
        
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(25)
        
        # Header text
        self.header = SubtitleLabel("NOTAK", self)
        self.header.setAlignment(Qt.AlignCenter)
        self.header.setStyleSheet("""
            color: #d4af37; 
            font-weight: bold; 
            letter-spacing: 10px; 
            font-size: 20px;
            margin-bottom: 10px;
        """)
        layout.addWidget(self.header)
        
        # Logo with subtle glow effect simulation via shadow if needed, but icon.png has it
        self.logo = QLabel(self)
        pixmap = QPixmap("icon.png")
        if not pixmap.isNull():
            self.logo.setPixmap(pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.logo)
        
        layout.addStretch(1)
        
        # Progress Bar
        self.progress = ProgressBar(self)
        self.progress.setFixedWidth(300)
        self.progress.setValue(0)
        # Custom gold theme for progress bar
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255, 255, 255, 0.1);
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #d4af37;
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.progress, 0, Qt.AlignHCenter)
        
        # Status Message
        self.status = QLabel("Starting Academic OS...", self)
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet("color: rgba(255, 255, 255, 0.4); font-size: 13px; font-style: italic;")
        layout.addWidget(self.status)
        
        # Center on screen
        self.centerOnScreen()
        
        # Shadow effect for the whole container
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(50)
        shadow.setXOffset(0)
        shadow.setYOffset(15)
        shadow.setColor(QColor(0, 0, 0, 200))
        self.container.setGraphicsEffect(shadow)
        
        # Outer layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20) # Space for shadow
        main_layout.addWidget(self.container)

    def centerOnScreen(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        size = self.geometry()
        x = (screen.width() - size.width()) // 2
        y = (screen.height() - size.height()) // 2
        self.move(x, y)

    def setProgress(self, value):
        self.progress.setValue(value)
        
    def setStatus(self, text):
        self.status.setText(text)
