import os
from PySide6.QtCore import Qt, QSize, QThread, Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                               QLabel, QFileDialog, QScrollArea, QStackedWidget,
                               QProgressBar)
from PySide6.QtGui import QPixmap, QImage

from qfluentwidgets import (TransparentPushButton, FluentIcon as FIF,
                             IconWidget, BodyLabel, CaptionLabel,
                             PrimaryPushButton, RoundMenu, Action)

from gui.zen_writer import ZenWriter

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None


# ── Background PDF loader (prevents UI freeze on large files) ─────────────────

class PdfLoaderThread(QThread):
    page_ready = Signal(int, object)   # (page_num, QImage)
    finished    = Signal(int)          # total pages
    error       = Signal(str)

    def __init__(self, path, zoom=1.5, parent=None):
        super().__init__(parent)
        self.path = path
        self.zoom = zoom

    def run(self):
        try:
            doc = fitz.open(self.path)
            total = doc.page_count
            mat = fitz.Matrix(self.zoom, self.zoom)
            for i in range(total):
                if self.isInterruptionRequested():
                    break
                page = doc.load_page(i)
                pix  = page.get_pixmap(matrix=mat)
                fmt  = QImage.Format_RGBA8888 if pix.alpha else QImage.Format_RGB888
                img  = QImage(bytes(pix.samples), pix.width, pix.height, pix.stride, fmt)
                self.page_ready.emit(i, img.copy())   # copy() keeps data alive
            doc.close()
            self.finished.emit(total)
        except Exception as e:
            self.error.emit(str(e))


# ── Single pane ───────────────────────────────────────────────────────────────

class FocusPane(QFrame):
    def __init__(self, title, parent=None):
        super().__init__(parent=parent)
        self.setStyleSheet("""
            FocusPane {
                background: rgba(0, 0, 0, 0.4);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 15px;
            }
        """)

        self._zoom = 1.5          # current zoom level
        self._pdf_path = None
        self._loader = None

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(6)

        # ── Header bar ────────────────────────────────────────────────────
        self.header = QFrame()
        self.header.setFixedHeight(44)
        self.header.setStyleSheet("background: rgba(128, 90, 213, 0.2); border-radius: 10px;")
        h = QHBoxLayout(self.header)
        h.setContentsMargins(10, 0, 6, 0)
        h.setSpacing(4)

        self.lbl_title = BodyLabel(title)
        self.lbl_title.setStyleSheet("color: white; font-weight: bold;")
        h.addWidget(self.lbl_title)
        h.addStretch()

        # Zoom controls (only visible for PDFs)
        self.zoom_bar = QWidget()
        zb = QHBoxLayout(self.zoom_bar)
        zb.setContentsMargins(0, 0, 0, 0)
        zb.setSpacing(2)
        self.btn_zoom_out = TransparentPushButton(FIF.REMOVE, "")
        self.btn_zoom_out.setFixedSize(28, 28)
        self.btn_zoom_out.setToolTip("Zoom Out")
        self.btn_zoom_out.clicked.connect(self._zoom_out)
        self.lbl_zoom = CaptionLabel("100%")
        self.lbl_zoom.setStyleSheet("color: #aaa; min-width: 38px;")
        self.lbl_zoom.setAlignment(Qt.AlignCenter)
        self.btn_zoom_in = TransparentPushButton(FIF.ADD, "")
        self.btn_zoom_in.setFixedSize(28, 28)
        self.btn_zoom_in.setToolTip("Zoom In")
        self.btn_zoom_in.clicked.connect(self._zoom_in)
        zb.addWidget(self.btn_zoom_out)
        zb.addWidget(self.lbl_zoom)
        zb.addWidget(self.btn_zoom_in)
        self.zoom_bar.setVisible(False)
        h.addWidget(self.zoom_bar)

        self.btn_select = TransparentPushButton(FIF.DOCUMENT, "Select Document")
        self.btn_select.setStyleSheet("color: white;")
        self.btn_select.clicked.connect(self.show_selector_menu)
        h.addWidget(self.btn_select)

        self.btn_close = TransparentPushButton(FIF.CLOSE, "")
        self.btn_close.clicked.connect(self.clear_view)
        h.addWidget(self.btn_close)

        root.addWidget(self.header)

        # ── Progress bar (shown during PDF load) ──────────────────────────
        self.progress = QProgressBar()
        self.progress.setFixedHeight(4)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar { background: rgba(255,255,255,0.05); border-radius: 2px; border: none; }
            QProgressBar::chunk { background: #805ad5; border-radius: 2px; }
        """)
        self.progress.setVisible(False)
        root.addWidget(self.progress)

        # ── Content stack ─────────────────────────────────────────────────
        self.stack = QStackedWidget()

        # 0 — Empty
        empty = QWidget()
        ev = QVBoxLayout(empty)
        ev.addStretch()
        ic = IconWidget(FIF.DOCUMENT)
        ic.setFixedSize(56, 56)
        ev.addWidget(ic, alignment=Qt.AlignCenter)
        ev.addWidget(BodyLabel("No document selected"), alignment=Qt.AlignCenter)
        ev.addStretch()
        self.stack.addWidget(empty)

        # 1 — Note
        self.note_view = QWidget()
        nv = QVBoxLayout(self.note_view)
        nv.setContentsMargins(0, 0, 0, 0)
        self.writer = ZenWriter()
        nv.addWidget(self.writer)
        self.stack.addWidget(self.note_view)

        # 2 — PDF
        self.pdf_scroll = QScrollArea()
        self.pdf_scroll.setWidgetResizable(True)
        self.pdf_scroll.setStyleSheet("background: #1a1a1a; border: none;")
        self.pdf_container = QWidget()
        self.pdf_layout = QVBoxLayout(self.pdf_container)
        self.pdf_layout.setSpacing(8)
        self.pdf_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.pdf_scroll.setWidget(self.pdf_container)
        self.stack.addWidget(self.pdf_scroll)

        # 3 — Image
        self.image_scroll = QScrollArea()
        self.image_scroll.setWidgetResizable(True)
        self.image_scroll.setStyleSheet("background: transparent; border: none;")
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_scroll.setWidget(self.image_label)
        self.stack.addWidget(self.image_scroll)

        root.addWidget(self.stack)
        self.stack.setCurrentIndex(0)

    # ── selector menu ──────────────────────────────────────────────────────

    def show_selector_menu(self):
        menu = RoundMenu(parent=self.btn_select)
        menu.addAction(Action(FIF.EDIT,     "Open Note (.md)", self,
                              triggered=self.select_note))
        menu.addAction(Action(FIF.DOCUMENT, "Open PDF (.pdf)", self,
                              triggered=self.select_pdf))
        menu.addAction(Action(FIF.PHOTO,    "Open Image",      self,
                              triggered=self.select_image))
        menu.exec(self.btn_select.mapToGlobal(self.btn_select.rect().bottomLeft()))

    def clear_view(self):
        self._abort_loader()
        self.stack.setCurrentIndex(0)
        self.lbl_title.setText("Empty View")
        self.zoom_bar.setVisible(False)
        self.progress.setVisible(False)
        self._pdf_path = None

    # ── notes ─────────────────────────────────────────────────────────────

    def select_note(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Note", "", "Markdown Files (*.md)")
        if path:
            self._load_note(path)

    def _load_note(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.writer.editor.setMarkdown(content)
            self.writer.current_file_path = path
            self.lbl_title.setText(os.path.basename(path))
            self.zoom_bar.setVisible(False)
            self.stack.setCurrentIndex(1)
        except Exception as e:
            print(f"Note load error: {e}")

    # ── PDFs ──────────────────────────────────────────────────────────────

    def select_pdf(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select PDF", "", "PDF Files (*.pdf)")
        if path:
            self._load_pdf(path)

    def _load_pdf(self, path):
        if not fitz:
            self.lbl_title.setText("PyMuPDF not installed")
            return

        self._abort_loader()
        self._pdf_path = path
        self._clear_pdf_layout()

        self.lbl_title.setText(os.path.basename(path))
        self.zoom_bar.setVisible(True)
        self._update_zoom_label()

        # Try to get page count for the progress bar
        try:
            doc = fitz.open(path)
            total = doc.page_count
            doc.close()
            self.progress.setRange(0, total)
            self.progress.setValue(0)
            self.progress.setVisible(True)
        except Exception:
            self.progress.setRange(0, 0)   # indeterminate
            self.progress.setVisible(True)

        self.stack.setCurrentIndex(2)

        self._loader = PdfLoaderThread(path, zoom=self._zoom, parent=self)
        self._loader.page_ready.connect(self._on_page_ready)
        self._loader.finished.connect(self._on_load_finished)
        self._loader.error.connect(self._on_load_error)
        self._loader.start()

    def _on_page_ready(self, page_num, img):
        lbl = QLabel()
        lbl.setPixmap(QPixmap.fromImage(img))
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("background: white; margin: 6px; border-radius: 4px;")
        self.pdf_layout.addWidget(lbl)
        self.progress.setValue(page_num + 1)

    def _on_load_finished(self, total):
        self.progress.setVisible(False)

    def _on_load_error(self, msg):
        self.progress.setVisible(False)
        err = QLabel(f"Error loading PDF:\n{msg}")
        err.setStyleSheet("color: #f87171; padding: 20px;")
        err.setWordWrap(True)
        self.pdf_layout.addWidget(err)

    def _abort_loader(self):
        if self._loader and self._loader.isRunning():
            self._loader.requestInterruption()
            self._loader.wait(500)

    def _clear_pdf_layout(self):
        while self.pdf_layout.count():
            item = self.pdf_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

    # ── Zoom ──────────────────────────────────────────────────────────────

    def _zoom_in(self):
        if self._zoom < 4.0:
            self._zoom = round(self._zoom + 0.25, 2)
            self._update_zoom_label()
            if self._pdf_path:
                self._load_pdf(self._pdf_path)

    def _zoom_out(self):
        if self._zoom > 0.5:
            self._zoom = round(self._zoom - 0.25, 2)
            self._update_zoom_label()
            if self._pdf_path:
                self._load_pdf(self._pdf_path)

    def _update_zoom_label(self):
        self.lbl_zoom.setText(f"{int(self._zoom / 1.5 * 100)}%")

    # ── Images ────────────────────────────────────────────────────────────

    def select_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Image", "",
                                              "Images (*.png *.jpg *.jpeg *.bmp *.webp)")
        if path:
            self._load_image(path)

    def _load_image(self, path):
        try:
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                self.image_label.setPixmap(
                    pixmap.scaled(self.width() - 40, self.height() - 100,
                                  Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
                self.lbl_title.setText(os.path.basename(path))
                self.zoom_bar.setVisible(False)
                self.stack.setCurrentIndex(3)
        except Exception as e:
            print(f"Image load error: {e}")


# ── Main interface ─────────────────────────────────────────────────────────────

class FocusInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("FocusInterface")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(10)

        self.pane1 = FocusPane("View 1", self)
        lay.addWidget(self.pane1)

        self.pane2 = FocusPane("View 2", self)
        lay.addWidget(self.pane2)
