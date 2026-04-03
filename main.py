import sys
import os
os.environ["QT_API"] = "pyside6"
os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
from PySide6.QtWidgets import QApplication

# Ensure the core database exists and is initialized
from core.database import initialize_db

def main():
    # 1. Create Application Context
    app = QApplication(sys.argv)
    app.setStyle("Fusion") 

    # 2. Init Database
    initialize_db()
    
    # 3. Init GUI AFTER the app is created to prevent QWidget pre-initialization
    from gui.main_window import MainWindow
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
