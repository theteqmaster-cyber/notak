import sys
import os
os.environ["QT_API"] = "pyside6"
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication

def main():
    # 1. Lock DPI Scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion") 

    # 2. Show Premium Splash Screen
    from gui.components.splash_screen import SplashScreen
    splash = SplashScreen()
    splash.show()
    app.processEvents()

    # 3. Initialize core services and track progress
    # We use app.processEvents() to keep the splash screen responsive
    splash.setStatus("Accessing StudyVault...")
    splash.setProgress(20)
    app.processEvents()
    
    from core.database import initialize_db, purge_old_deleted_items
    initialize_db()
    splash.setProgress(40)
    app.processEvents()
    
    splash.setStatus("Syncing Library Metadata...")
    purge_old_deleted_items(30)
    splash.setProgress(60)
    app.processEvents()
    
    splash.setStatus("Building Academic Command Center...")
    from gui.main_window import MainWindow
    window = MainWindow() # This performs heavy UI setup
    splash.setProgress(90)
    app.processEvents()
    
    splash.setStatus("Ready to Study.")
    splash.setProgress(100)
    app.processEvents()
    
    # 4. Sequential transition to main window for maximum stability
    # Using a slightly longer delay and deleteLater for safer object cleanup
    def start_main_app():
        window.show()
        splash.hide() # Hide first to prevent flickering
        splash.deleteLater() # Safe cleanup
        
    QTimer.singleShot(1200, start_main_app)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
