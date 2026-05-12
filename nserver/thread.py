"""
nserver/thread.py
QThread wrapper that runs the Flask+SocketIO server without blocking the Qt event loop.
"""

import threading
import os
import subprocess
import time
from PySide6.QtCore import QThread, Signal


class NServerThread(QThread):
    """
    Runs the Flask/SocketIO server in a daemon thread.
    Emits `started_signal` once the server is up,
    and `stopped_signal` once it shuts down.
    """
    started_signal = Signal(str, int)   # (host_ip, port)
    stopped_signal = Signal()
    error_signal   = Signal(str)

    def __init__(self, host: str, port: int, parent=None):
        super().__init__(parent)
        self._host = host
        self._port = port
        self._socketio = None
        self._stop_event = threading.Event()

    def _clean_port(self):
        """Forcefully free the port if it's being held by a lingering process."""
        try:
            # Find PID using the port (Linux/macOS)
            cmd = ["fuser", "-k", "-n", "tcp", str(self._port)]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.5) # Give OS time to actually close it
        except Exception:
            pass

    def run(self):
        self._clean_port()
        try:
            # Import here so Flask only initialises inside the thread
            from nserver.server import create_app
            app, socketio = create_app()
            self._socketio = socketio

            self.started_signal.emit(self._host, self._port)

            # allow_unsafe_werkzeug=True is needed when running inside Qt
            socketio.run(
                app,
                host=self._host,
                port=self._port,
                use_reloader=False,
                log_output=False,
                allow_unsafe_werkzeug=True,
            )
        except Exception as e:
            self.error_signal.emit(str(e))
        finally:
            self.stopped_signal.emit()

    def stop(self):
        """Ask the server to shut down gracefully."""
        try:
            if self._socketio:
                import requests
                # 1. Try graceful shutdown via endpoint
                try:
                    requests.post(f"http://127.0.0.1:{self._port}/_shutdown", timeout=1)
                except Exception:
                    pass
                
                # 2. Give it a moment to release the port
                import time
                time.sleep(0.5)
            
            # 3. Stop the thread event loop
            self.quit()
            if not self.wait(2000): # Wait up to 2s
                self.terminate()    # Force kill if still stuck
                self.wait()
        except Exception:
            self.terminate()
            self.wait()
