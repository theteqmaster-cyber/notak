import os
import subprocess
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout

from qfluentwidgets import (ScrollArea, TitleLabel, SearchLineEdit,
                            SubtitleLabel, IconWidget, FluentIcon as FIF,
                            BodyLabel, CardWidget, CaptionLabel,
                            TransparentPushButton, PrimaryPushButton)

from core.database import search_files
from core.importer import split_filename_for_display
from gui.components.marquee_label import MarqueeLabel

PAGE_SIZE = 15   # results per page


class SearchResultCard(CardWidget):
    clicked = Signal(str)

    def __init__(self, file_data, parent=None):
        super().__init__(parent)
        self.file_path = file_data['path']
        self.setCursor(Qt.PointingHandCursor)

        v = QVBoxLayout(self)
        v.setContentsMargins(15, 12, 15, 12)

        h = QHBoxLayout()

        icon = FIF.EDIT if file_data['category'] == 'Notes' else \
               FIF.PHOTO if file_data['category'] == 'Images' else FIF.DOCUMENT

        iw = IconWidget(icon)
        iw.setFixedSize(20, 20)
        h.addWidget(iw)

        basename = os.path.basename(self.file_path)
        display_name, _ = split_filename_for_display(basename)

        name_lbl = MarqueeLabel(display_name)
        name_lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        name_lbl.setStyleSheet("font-weight: bold; font-size: 13px; background: transparent; border: none;")
        name_lbl.setFixedWidth(220)
        h.addWidget(name_lbl)
        h.addStretch(1)

        course_lbl = CaptionLabel(file_data.get('course', ''))
        course_lbl.setStyleSheet(
            "color: #0078d4; background: rgba(0,120,212,0.1); padding: 2px 8px; border-radius: 4px;"
        )
        h.addWidget(course_lbl)
        v.addLayout(h)

        snippet = file_data.get('snippet', '')
        if snippet:
            s = BodyLabel(snippet)
            s.setWordWrap(True)
            s.setStyleSheet("color: #888; font-size: 11px; margin-top: 3px;")
            v.addWidget(s)

        self.setStyleSheet("""
            SearchResultCard {
                background: rgba(0,0,0,0.6);
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 8px;
            }
            SearchResultCard:hover {
                background: rgba(255,255,255,0.08);
                border: 1px solid rgba(128,90,213,0.4);
            }
        """)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.file_path)


class DeepSearchInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("DeepSearchInterface")
        self.setStyleSheet("background: transparent;")

        self._all_results = []   # full result list from DB
        self._page = 0           # current page index (0-based)

        # Debounce timer — waits 300 ms after the user stops typing
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(300)
        self._debounce.timeout.connect(self._run_search)

        root = QVBoxLayout(self)
        root.setContentsMargins(40, 30, 40, 20)
        root.setSpacing(15)
        root.setAlignment(Qt.AlignTop)

        # ── Header ────────────────────────────────────────────────────────
        self.title_label = TitleLabel("Deep Search", self)
        self.title_label.setStyleSheet("font-weight: bold;")
        root.addWidget(self.title_label)

        self.sub_label = BodyLabel("Search through all your notes and study materials instantly.")
        self.sub_label.setStyleSheet("color: #888;")
        root.addWidget(self.sub_label)

        # ── Search bar ────────────────────────────────────────────────────
        self.search_bar = SearchLineEdit(self)
        self.search_bar.setPlaceholderText("Search for keywords… (e.g. 'database indexing')")
        self.search_bar.setClearButtonEnabled(True)
        self.search_bar.setFixedWidth(500)
        self.search_bar.textChanged.connect(self._on_text_changed)
        root.addWidget(self.search_bar)

        # ── Results area ──────────────────────────────────────────────────
        self.scroll_area = ScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("ScrollArea { background-color: transparent; border: none; }")

        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setSpacing(8)
        self.results_layout.setAlignment(Qt.AlignTop)
        self.scroll_area.setWidget(self.results_container)
        root.addWidget(self.scroll_area)

        # ── Footer: count + pagination ─────────────────────────────────────
        footer = QHBoxLayout()
        footer.setSpacing(10)

        self.results_info = CaptionLabel("", self)
        self.results_info.setStyleSheet("color: #555;")
        footer.addWidget(self.results_info)

        footer.addStretch(1)

        self.btn_prev = TransparentPushButton(FIF.LEFT_ARROW, "Prev")
        self.btn_prev.setFixedHeight(32)
        self.btn_prev.clicked.connect(self._prev_page)
        self.btn_prev.setEnabled(False)
        footer.addWidget(self.btn_prev)

        self.page_label = CaptionLabel("", self)
        self.page_label.setStyleSheet("color: #777; min-width: 60px;")
        self.page_label.setAlignment(Qt.AlignCenter)
        footer.addWidget(self.page_label)

        self.btn_next = TransparentPushButton(FIF.RIGHT_ARROW, "Next")
        self.btn_next.setFixedHeight(32)
        self.btn_next.clicked.connect(self._next_page)
        self.btn_next.setEnabled(False)
        footer.addWidget(self.btn_next)

        root.addLayout(footer)

    # ── internal helpers ──────────────────────────────────────────────────

    def _on_text_changed(self, text):
        """Restart the debounce timer on each keystroke."""
        self._debounce.stop()
        if text.strip():
            self._debounce.start()
        else:
            self._all_results = []
            self._page = 0
            self._clear_results()
            self.results_info.setText("")
            self.page_label.setText("")
            self._update_nav()

    def _run_search(self):
        query = self.search_bar.text().strip()
        if not query:
            return
        self._all_results = search_files(query)
        self._page = 0
        self._render_page()

    def _render_page(self):
        self._clear_results()
        total = len(self._all_results)
        if total == 0:
            self.results_info.setText("No results found.")
            self.page_label.setText("")
            self._update_nav()
            return

        start = self._page * PAGE_SIZE
        end   = min(start + PAGE_SIZE, total)
        page_results = self._all_results[start:end]

        for res in page_results:
            card = SearchResultCard(res, self.results_container)
            card.clicked.connect(self.open_result)
            self.results_layout.addWidget(card)

        total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
        self.results_info.setText(
            f"Showing {start + 1}–{end} of {total} results"
        )
        self.page_label.setText(f"{self._page + 1} / {total_pages}")
        self._update_nav()

    def _clear_results(self):
        for i in reversed(range(self.results_layout.count())):
            w = self.results_layout.itemAt(i).widget()
            if w:
                w.deleteLater()

    def _update_nav(self):
        total_pages = (len(self._all_results) + PAGE_SIZE - 1) // PAGE_SIZE if self._all_results else 0
        self.btn_prev.setEnabled(self._page > 0)
        self.btn_next.setEnabled(self._page < total_pages - 1)

    def _prev_page(self):
        if self._page > 0:
            self._page -= 1
            self._render_page()
            self.scroll_area.verticalScrollBar().setValue(0)

    def _next_page(self):
        total_pages = (len(self._all_results) + PAGE_SIZE - 1) // PAGE_SIZE
        if self._page < total_pages - 1:
            self._page += 1
            self._render_page()
            self.scroll_area.verticalScrollBar().setValue(0)

    # ── public API used by Dashboard redirect ─────────────────────────────

    def on_search_changed(self, text):
        """Called externally (e.g. Dashboard) to pre-fill the query."""
        self.search_bar.setText(text)

    # ── file opening ──────────────────────────────────────────────────────

    def open_result(self, path):
        """Smart routing: .md notes → Quick Note; everything else → external."""
        if path.endswith('.md') and os.path.exists(path):
            try:
                mw = self.window()
                if hasattr(mw, 'quickNoteInterface') and hasattr(mw, 'stackedWidget'):
                    mw.stackedWidget.setCurrentWidget(mw.quickNoteInterface)
                    qn = mw.quickNoteInterface
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    qn.writer.editor.blockSignals(True)
                    qn.writer.editor.setMarkdown(content)
                    qn.writer.editor.blockSignals(False)
                    qn.writer.current_file_path = path
                    qn.writer.editor.setReadOnly(False)
                    qn.writer.status_label.setText("LOADED ✓")
                    qn.writer.status_label.setStyleSheet(
                        "color: #0088ff; background: rgba(0,136,255,0.1); "
                        "padding: 4px 12px; border-radius: 10px;"
                    )
                    return
            except Exception as e:
                print(f"Quick Note redirect error: {e}")

        try:
            subprocess.Popen(['xdg-open', path])
        except Exception as e:
            print(f"Error opening result: {e}")
