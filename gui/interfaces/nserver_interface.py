"""
gui/interfaces/nserver_interface.py
Desktop control panel for the NServer local network web server.
Shows Start/Stop, network URL, QR code, and live connected-clients list.
"""

import io
import socket as _socket
import os

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem
)

from qfluentwidgets import (
    SubtitleLabel, PrimaryPushButton, PushButton, CaptionLabel,
    BodyLabel, CardWidget, FluentIcon as FIF, StrongBodyLabel,
    InfoBar, InfoBarPosition, ScrollArea
)


NSERVER_PORT = 8765


def _get_local_ip() -> str:
    """Best-effort: get the LAN IP (not 127.0.0.1)."""
    try:
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _make_qr_pixmap(url: str, size: int = 180) -> QPixmap:
    """Generate a QR code pixmap for the given URL."""
    try:
        import qrcode
        from PIL import Image
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=6,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img: Image.Image = qr.make_image(fill_color="#ffffff", back_color="#0a0a0f")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        pm = QPixmap()
        pm.loadFromData(buf.getvalue())
        return pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    except Exception as e:
        print(f"[NServer] QR generation failed: {e}")
        return QPixmap()


class NServerInterface(QWidget):
    """Sidebar panel that controls the local network web server."""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("NServerInterface")
        self.setStyleSheet("background: transparent;")

        self._thread = None
        self._running = False
        self._local_ip = _get_local_ip()
        self._url = f"http://{self._local_ip}:{NSERVER_PORT}"

        # ── Root layout ──────────────────────────────────────────
        root = QVBoxLayout(self)
        root.setContentsMargins(36, 32, 36, 32)
        root.setSpacing(20)

        # Header
        hdr = QHBoxLayout()
        title = SubtitleLabel("NServer")
        title.setStyleSheet("font-size:26px;font-weight:900;color:white;")
        hdr.addWidget(title)
        hdr.addStretch(1)

        self.status_pill = CaptionLabel("● Offline")
        self.status_pill.setStyleSheet(
            "color: rgba(255,100,100,0.9); font-weight: bold; "
            "background: rgba(239,68,68,0.12); border-radius:10px; padding: 4px 12px;"
        )
        hdr.addWidget(self.status_pill)
        root.addLayout(hdr)

        sub = CaptionLabel("Local network access — share Notak with any device on your Wi-Fi")
        sub.setStyleSheet("color: rgba(255,255,255,0.35);")
        root.addWidget(sub)

        # ── Two-column layout ─────────────────────────────────────
        cols = QHBoxLayout()
        cols.setSpacing(20)

        # LEFT: controls + QR
        left = QVBoxLayout()
        left.setSpacing(16)

        # Control card
        ctrl_card = CardWidget()
        ctrl_card.setStyleSheet("CardWidget{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:14px;}")
        ctrl_inner = QVBoxLayout(ctrl_card)
        ctrl_inner.setContentsMargins(20, 20, 20, 20)
        ctrl_inner.setSpacing(14)

        ctrl_lbl = CaptionLabel("SERVER CONTROL")
        ctrl_lbl.setStyleSheet("color:rgba(255,255,255,0.3);font-weight:bold;letter-spacing:1px;")
        ctrl_inner.addWidget(ctrl_lbl)

        self.btn_start = PrimaryPushButton(FIF.PLAY, "Start NServer")
        self.btn_start.setFixedHeight(42)
        self.btn_start.clicked.connect(self.start_server)
        ctrl_inner.addWidget(self.btn_start)

        self.btn_stop = PushButton(FIF.CANCEL, "Stop NServer")
        self.btn_stop.setFixedHeight(42)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_server)
        ctrl_inner.addWidget(self.btn_stop)

        left.addWidget(ctrl_card)

        # URL card
        url_card = CardWidget()
        url_card.setStyleSheet("CardWidget{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:14px;}")
        url_inner = QVBoxLayout(url_card)
        url_inner.setContentsMargins(20, 16, 20, 16)
        url_inner.setSpacing(8)

        url_lbl = CaptionLabel("NETWORK ADDRESS")
        url_lbl.setStyleSheet("color:rgba(255,255,255,0.3);font-weight:bold;letter-spacing:1px;")
        url_inner.addWidget(url_lbl)

        self.url_label = StrongBodyLabel(self._url)
        self.url_label.setStyleSheet(
            "font-size:15px;color:#06b6d4;font-weight:700;"
            "background:rgba(6,182,212,0.08);border-radius:8px;padding:8px 12px;"
        )
        self.url_label.setWordWrap(True)
        url_inner.addWidget(self.url_label)

        port_info = CaptionLabel(f"Port {NSERVER_PORT} · Same Wi-Fi required")
        port_info.setStyleSheet("color:rgba(255,255,255,0.25);")
        url_inner.addWidget(port_info)

        left.addWidget(url_card)

        # QR card
        qr_card = CardWidget()
        qr_card.setStyleSheet("CardWidget{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:14px;}")
        qr_inner = QVBoxLayout(qr_card)
        qr_inner.setContentsMargins(20, 16, 20, 16)
        qr_inner.setSpacing(8)
        qr_inner.setAlignment(Qt.AlignCenter)

        qr_lbl = CaptionLabel("SCAN TO CONNECT")
        qr_lbl.setStyleSheet("color:rgba(255,255,255,0.3);font-weight:bold;letter-spacing:1px;")
        qr_inner.addWidget(qr_lbl, alignment=Qt.AlignCenter)

        self.qr_label = QLabel()
        self.qr_label.setAlignment(Qt.AlignCenter)
        self.qr_label.setFixedSize(180, 180)
        self.qr_label.setStyleSheet("background: #0a0a0f; border-radius:10px;")
        pm = _make_qr_pixmap(self._url)
        if not pm.isNull():
            self.qr_label.setPixmap(pm)
        else:
            self.qr_label.setText("QR unavailable")
            self.qr_label.setStyleSheet("color:#aaa;font-size:12px;")
        qr_inner.addWidget(self.qr_label, alignment=Qt.AlignCenter)

        hint = CaptionLabel("Point your phone camera at the QR code")
        hint.setStyleSheet("color:rgba(255,255,255,0.25);font-size:11px;")
        qr_inner.addWidget(hint, alignment=Qt.AlignCenter)

        left.addWidget(qr_card)
        left.addStretch(1)

        cols.addLayout(left, 0)

        # RIGHT: active clients
        right = QVBoxLayout()
        right.setSpacing(12)

        clients_card = CardWidget()
        clients_card.setStyleSheet("CardWidget{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:14px;}")
        clients_inner = QVBoxLayout(clients_card)
        clients_inner.setContentsMargins(20, 20, 20, 20)
        clients_inner.setSpacing(12)

        ch = QHBoxLayout()
        clients_lbl = CaptionLabel("ACTIVE USERS")
        clients_lbl.setStyleSheet("color:rgba(255,255,255,0.3);font-weight:bold;letter-spacing:1px;")
        ch.addWidget(clients_lbl)
        ch.addStretch(1)
        self.client_count_lbl = CaptionLabel("0 online")
        self.client_count_lbl.setStyleSheet("color:#10b981;font-weight:bold;")
        ch.addWidget(self.client_count_lbl)
        clients_inner.addLayout(ch)

        self.clients_list = QListWidget()
        self.clients_list.setStyleSheet("""
            QListWidget { background: transparent; border: none; }
            QListWidget::item { background: rgba(255,255,255,0.03); border-radius:8px;
                                margin-bottom: 4px; padding: 8px 12px; color: #ddd; }
            QListWidget::item:hover { background: rgba(255,255,255,0.07); }
        """)
        self.clients_list.setMinimumHeight(300)
        clients_inner.addWidget(self.clients_list)

        right.addWidget(clients_card)

        # Info card
        info_card = CardWidget()
        info_card.setStyleSheet("CardWidget{background:rgba(124,58,237,0.08);border:1px solid rgba(124,58,237,0.2);border-radius:14px;}")
        info_inner = QVBoxLayout(info_card)
        info_inner.setContentsMargins(20, 16, 20, 16)
        info_inner.setSpacing(6)

        info_title = StrongBodyLabel("🌐 Web Access Features")
        info_title.setStyleSheet("color:#a78bfa;font-size:14px;")
        info_inner.addWidget(info_title)

        features = [
            "📚 Study Hub — Browse & preview vault files",
            "✏️  Notes — Create & save markdown notes",
            "🔍 Deep Search — Full-text search",
            "🎵 Music Hub — Stream your playlist (mp3, m4a, wav)",
            "📻 Radio — Live internet radio streams",
            "📅 Calendar — View & add study events",
            "⏱️  Sessions — Study timer & history",
            "🖊️  Mboard — Pen canvas with undo/redo",
        ]
        for feat in features:
            fl = CaptionLabel(feat)
            fl.setStyleSheet("color:rgba(255,255,255,0.55);font-size:12px;")
            info_inner.addWidget(fl)

        right.addWidget(info_card)
        right.addStretch(1)

        cols.addLayout(right, 1)
        root.addLayout(cols)

        # ── Refresh timer ─────────────────────────────────────────
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_clients)
        # Not started until server is running
        QTimer.singleShot(1000, self.start_server)

    # ── Server lifecycle ───────────────────────────────────────────
    def start_server(self):
        if self._running:
            return
        try:
            from nserver.thread import NServerThread
            self._thread = NServerThread(host="0.0.0.0", port=NSERVER_PORT, parent=self)
            self._thread.started_signal.connect(self._on_started)
            self._thread.stopped_signal.connect(self._on_stopped)
            self._thread.error_signal.connect(self._on_error)
            self._thread.start()
        except Exception as e:
            InfoBar.error(
                title="NServer Error",
                content=str(e),
                parent=self.window(),
                position=InfoBarPosition.TOP_RIGHT,
            )

    def stop_server(self):
        if self._thread:
            self._thread.stop()
        self._on_stopped()

    def _on_started(self, host, port):
        self._running = True
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.status_pill.setText("● Online")
        self.status_pill.setStyleSheet(
            "color: rgba(100,255,150,0.9); font-weight: bold; "
            "background: rgba(16,185,129,0.12); border-radius:10px; padding: 4px 12px;"
        )
        self._refresh_timer.start(5000)
        InfoBar.success(
            title="NServer Running",
            content=f"Listening on {self._url}",
            parent=self.window(),
            position=InfoBarPosition.TOP_RIGHT,
        )

    def _on_stopped(self):
        self._running = False
        self._thread = None
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.status_pill.setText("● Offline")
        self.status_pill.setStyleSheet(
            "color: rgba(255,100,100,0.9); font-weight: bold; "
            "background: rgba(239,68,68,0.12); border-radius:10px; padding: 4px 12px;"
        )
        self._refresh_timer.stop()
        self.clients_list.clear()
        self.client_count_lbl.setText("0 online")

    def _on_error(self, msg):
        InfoBar.error(
            title="NServer Error",
            content=msg,
            parent=self.window(),
            position=InfoBarPosition.TOP_RIGHT,
        )
        self._on_stopped()

    def _refresh_clients(self):
        """Poll the server for active clients and update the list."""
        if not self._running:
            return
        try:
            import urllib.request, json
            req = urllib.request.Request(
                f"http://127.0.0.1:{NSERVER_PORT}/api/status/clients",
                headers={"User-Agent": "Notak-Desktop/1.0"}
            )
            with urllib.request.urlopen(req, timeout=2) as r:
                clients = json.loads(r.read())
            self._update_clients_list(clients)
        except Exception:
            pass   # server might be starting up

    def _update_clients_list(self, clients: list):
        self.clients_list.clear()
        self.client_count_lbl.setText(f"{len(clients)} online")

        if not clients:
            item = QListWidgetItem("No devices connected yet")
            item.setForeground(Qt.gray)
            self.clients_list.addItem(item)
            return

        for c in clients:
            page  = c.get("page", "?")
            ip    = c.get("ip", "?")
            user  = c.get("username", "Guest")
            label = f"👤 {user}  •  /{page}  •  {ip}"
            self.clients_list.addItem(QListWidgetItem(label))

    def closeEvent(self, event):
        if self._running:
            self.stop_server()
        super().closeEvent(event)
