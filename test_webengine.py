import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl

def test():
    # Attempt to disable sandbox if it's the cause of the crash
    # os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
    
    app = QApplication(sys.argv)
    view = QWebEngineView()
    view.load(QUrl("https://google.com"))
    view.show()
    print("WebEngine initialized and shown.")
    # Exit after a short time
    from PySide6.QtCore import QTimer
    QTimer.singleShot(2000, lambda: app.quit())
    sys.exit(app.exec())

if __name__ == "__main__":
    import os
    test()
