import os
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import QPainter, QBrush, QColor, QPen
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, 
                             QGraphicsItem, QGraphicsRectItem, QGraphicsEllipseItem,
                             QGraphicsTextItem, QFrame, QHBoxLayout)

from qfluentwidgets import (TransparentToolButton, FluentIcon as FIF, PrimaryPushButton, 
                            CaptionLabel, LineEdit)
from core.canvas_engine import MboardData, CanvasManager

class EditableTextItem(QGraphicsTextItem):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsFocusable)
        self.setTextInteractionFlags(Qt.NoTextInteraction) # Start as draggable
        
        font = self.font()
        font.setPointSize(14)
        font.setBold(True)
        self.setFont(font)
        self.setDefaultTextColor(QColor("white"))

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setTextInteractionFlags(Qt.TextEditorInteraction)
            self.setFocus()
            super().mouseDoubleClickEvent(event)
        else:
            super().mouseDoubleClickEvent(event)

    def focusOutEvent(self, event):
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        # Deselect text on focus out
        cursor = self.textCursor()
        cursor.clearSelection()
        self.setTextCursor(cursor)
        super().focusOutEvent(event)

class ResizeHandle(QGraphicsEllipseItem):
    def __init__(self, parent=None):
        super().__init__(-5, -5, 10, 10, parent)
        self.setBrush(QBrush(QColor(255, 255, 255)))
        self.setPen(QPen(QColor(0, 0, 0), 1))
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemSendsGeometryChanges)
        self.setCursor(Qt.SizeFDiagCursor)
        self.hide() # Only show when parent is selected

    def mouseMoveEvent(self, event):
        if self.flags() & QGraphicsItem.ItemIsMovable:
            parent = self.parentItem()
            if parent:
                new_pos = event.pos()
                # Enforce minimum size
                rect = parent.rect()
                new_w = max(20, new_pos.x())
                new_h = max(20, new_pos.y())
                parent.setRect(0, 0, new_w, new_h)
                self.setPos(new_w, new_h)
        super().mouseMoveEvent(event)

class ResizableRectItem(QGraphicsRectItem):
    def __init__(self, x, y, w, h, parent=None):
        super().__init__(0, 0, w, h, parent)
        self.setPos(x, y)
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemSendsGeometryChanges)
        self.handle = ResizeHandle(self)
        self.update_handle_pos()

    def update_handle_pos(self):
        rect = self.rect()
        self.handle.setPos(rect.width(), rect.height())

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedChange:
            self.handle.setVisible(value)
        return super().itemChange(change, value)

class ResizableEllipseItem(QGraphicsEllipseItem):
    def __init__(self, x, y, w, h, parent=None):
        super().__init__(0, 0, w, h, parent)
        self.setPos(x, y)
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemSendsGeometryChanges)
        self.handle = ResizeHandle(self)
        self.update_handle_pos()

    def update_handle_pos(self):
        rect = self.rect()
        self.handle.setPos(rect.width(), rect.height())

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedChange:
            self.handle.setVisible(value)
        return super().itemChange(change, value)

class StickyNoteItem(ResizableRectItem):
    def __init__(self, x, y, w, h, text="Quick Note"):
        super().__init__(x, y, w, h)
        self.setBrush(QBrush(QColor(255, 255, 100, 200)))
        self.setPen(QPen(QColor(200, 200, 0), 2))
        
        self.text_item = EditableTextItem(text, self)
        self.text_item.setDefaultTextColor(QColor("black"))
        self.text_item.setPos(10, 10)
        self.update_text_width()

    def setRect(self, *args):
        super().setRect(*args)
        self.update_text_width()

    def update_text_width(self):
        if hasattr(self, 'text_item'):
            self.text_item.setTextWidth(self.rect().width() - 20)

    def mouseDoubleClickEvent(self, event):
        self.text_item.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.text_item.setFocus()
        super().mouseDoubleClickEvent(event)

class MboardScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(-5000, -5000, 10000, 10000)
        self.setBackgroundBrush(QBrush(QColor(30, 30, 30)))
        
    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        
        # Draw grid
        pen = QPen(QColor(45, 45, 45), 1)
        painter.setPen(pen)
        
        left = int(rect.left()) - (int(rect.left()) % 20)
        top = int(rect.top()) - (int(rect.top()) % 20)
        
        # Vertical lines
        for x in range(left, int(rect.right()), 20):
            painter.drawLine(x, int(rect.top()), x, int(rect.bottom()))
            
        # Horizontal lines
        for y in range(top, int(rect.bottom()), 20):
            painter.drawLine(int(rect.left()), y, int(rect.right()), y)

class MboardView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setRenderHint(QPainter.TextAntialiasing)
        
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.NoFrame)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag) # Default to panning for whiteboard feel
        
        self.zoom_level = 1.0

    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            zoom_in_factor = 1.25
            zoom_out_factor = 1 / zoom_in_factor
            
            if event.angleDelta().y() > 0:
                zoom_factor = zoom_in_factor
                self.zoom_level *= zoom_factor
            else:
                zoom_factor = zoom_out_factor
                self.zoom_level *= zoom_factor
                
            self.scale(zoom_factor, zoom_factor)
        else:
            super().wheelEvent(event)

class MboardEditor(QWidget):
    closed = Signal()

    def __init__(self, board_path=None, parent=None):
        super().__init__(parent)
        self.manager = CanvasManager()
        self.board_path = board_path
        self.data = None
        
        if self.board_path:
            self.data = self.manager.load_board(self.board_path)
        else:
            self.data = MboardData("New Board")
            
        self.initUI()
        self.load_elements_into_scene()
        self.setObjectName("MboardEditor")
        self.setStyleSheet("background-color: #1e1e1e;")

    def initUI(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Top Bar
        self.top_bar = QFrame()
        self.top_bar.setFixedHeight(50)
        self.top_bar.setStyleSheet("background-color: #252525; border-bottom: 1px solid #333;")
        top_layout = QHBoxLayout(self.top_bar)
        top_layout.setContentsMargins(15, 0, 15, 0)
        
        self.btn_back = TransparentToolButton(FIF.LEFT_ARROW, self)
        self.btn_back.clicked.connect(self.close_editor)
        top_layout.addWidget(self.btn_back)
        
        self.title_edit = LineEdit(self)
        self.title_edit.setText(self.data.title)
        self.title_edit.setFixedWidth(250)
        self.title_edit.setStyleSheet("font-size: 14px; font-weight: bold; background: transparent; border: none; color: white;")
        self.title_edit.placeholderText = "Enter board title..."
        top_layout.addWidget(self.title_edit)
        
        top_layout.addStretch(1)
        
        self.btn_save = PrimaryPushButton("Save", self)
        self.btn_save.setFixedWidth(80)
        self.btn_save.clicked.connect(self.save_board)
        top_layout.addWidget(self.btn_save)
        
        self.layout.addWidget(self.top_bar)
        
        # Scene & View
        self.scene = MboardScene(self)
        self.view = MboardView(self.scene, self)
        self.layout.addWidget(self.view)
        
        # Floating Toolbar (Overlay logic would go here, for now simple bottom bar)
        self.toolbar = QFrame(self)
        self.toolbar.setFixedHeight(60)
        self.toolbar.setStyleSheet("""
            QFrame {
                background-color: rgba(40, 40, 40, 0.8);
                border: 1px solid #444;
                border-radius: 30px;
            }
        """)
        toolbar_layout = QHBoxLayout(self.toolbar)
        toolbar_layout.setContentsMargins(20, 0, 20, 0)
        toolbar_layout.setSpacing(15)
        
        # Tools
        self.btn_cursor = self.add_tool(FIF.SEARCH, "Select", self.set_select_mode)
        self.btn_text = self.add_tool(FIF.EDIT, "Text", self.add_text_item)
        self.btn_sticky = self.add_tool(FIF.DOCUMENT, "Sticky", self.add_sticky_item)
        self.btn_rect = self.add_tool(FIF.LAYOUT, "Rectangle", lambda: self.add_shape_item("rect"))
        self.btn_circle = self.add_tool(FIF.GLOBE, "Circle", lambda: self.add_shape_item("circle"))
        
        # Internal timer or listener for changes could go here for auto-save thumbnails
        
        # Positioning toolbar
        self.layout.addWidget(self.toolbar, alignment=Qt.AlignHCenter)

    def add_tool(self, icon, tooltip, callback):
        btn = TransparentToolButton(icon, self.toolbar)
        btn.setToolTip(tooltip)
        btn.setFixedSize(40, 40)
        btn.clicked.connect(callback)
        self.toolbar.layout().addWidget(btn)
        return btn

    def set_select_mode(self):
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

    def add_text_item(self):
        item = EditableTextItem("Double click to edit")
        item.setPos(self.view.mapToScene(self.view.viewport().rect().center()))
        self.scene.addItem(item)
        self.set_select_mode() # Keep panning active

    def add_shape_item(self, shape_type):
        pos = self.view.mapToScene(self.view.viewport().rect().center())
        if shape_type == "rect":
            item = ResizableRectItem(pos.x(), pos.y(), 150, 100)
            item.setBrush(QBrush(QColor(0, 210, 255, 100)))
            item.setPen(QPen(QColor(0, 210, 255), 2))
        else:
            item = ResizableEllipseItem(pos.x(), pos.y(), 100, 100)
            item.setBrush(QBrush(QColor(255, 100, 100, 100)))
            item.setPen(QPen(QColor(255, 100, 100), 2))
            
        self.scene.addItem(item)
        self.set_select_mode()

    def add_sticky_item(self):
        pos = self.view.mapToScene(self.view.viewport().rect().center())
        item = StickyNoteItem(pos.x(), pos.y(), 150, 150)
        self.scene.addItem(item)
        self.set_select_mode()

    def save_board(self):
        # Sync title
        self.data.title = self.title_edit.text() or "Untitled Board"
        
        # Update elements list from scene
        self.data.elements = []
        for item in self.scene.items():
            if isinstance(item, QGraphicsTextItem):
                self.data.elements.append({
                    "type": "text",
                    "content": item.toPlainText(),
                    "x": item.scenePos().x(),
                    "y": item.scenePos().y(),
                    "color": item.defaultTextColor().name()
                })
            elif isinstance(item, StickyNoteItem):
                self.data.elements.append({
                    "type": "sticky",
                    "x": item.scenePos().x(),
                    "y": item.scenePos().y(),
                    "w": item.rect().width(),
                    "h": item.rect().height(),
                    "content": item.text_item.toPlainText(),
                    "color": item.brush().color().name(QColor.HexArgb)
                })
            elif isinstance(item, ResizableRectItem):
                # Distinguish sticky vs shape by color/size or just store type
                self.data.elements.append({
                    "type": "rect",
                    "x": item.scenePos().x(),
                    "y": item.scenePos().y(),
                    "w": item.rect().width(),
                    "h": item.rect().height(),
                    "color": item.brush().color().name(QColor.HexArgb)
                })
            elif isinstance(item, ResizableEllipseItem):
                self.data.elements.append({
                    "type": "circle",
                    "x": item.scenePos().x(),
                    "y": item.scenePos().y(),
                    "w": item.rect().width(),
                    "h": item.rect().height(),
                    "color": item.brush().color().name(QColor.HexArgb)
                })

        if not self.board_path:
            # First time save
            self.board_path = self.manager.save_board(self.data, self.data.title)
        else:
            self.manager.save_board(self.data, os.path.basename(self.board_path))
            
        from PySide6.QtCore import QTimer
        QTimer.singleShot(500, self.generate_thumbnail)
        
        from qfluentwidgets import InfoBar, InfoBarPosition
        InfoBar.success(
            title='Board Saved',
            content="Changes saved to StudyVault.",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=2000,
            parent=self
        )

    def generate_thumbnail(self):
        if not self.board_path:
            return
            
        thumb_path = self.board_path.replace(".mboard", ".png")
        
        # Get scene bounding rect
        rect = self.scene.itemsBoundingRect()
        if rect.isEmpty():
            rect = QRectF(-100, -100, 200, 200)
        
        # Add some padding
        rect.adjust(-50, -50, 50, 50)
        
        from PySide6.QtGui import QImage
        image = QImage(320, 420, QImage.Format_ARGB32)
        image.fill(QColor(30,30,30))
        
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        self.scene.render(painter, QRectF(image.rect()), rect)
        painter.end()
        
        image.save(thumb_path)

    def load_elements_into_scene(self):
        # The Nuclear Option: Re-create the entire scene to prevent memory issues and stale data
        # We disconnect and destroy the old scene safely
        if hasattr(self, 'scene') and self.scene:
            self.scene.clearSelection()
            # We don't call self.scene.clear() which was causing crashes
            self.scene.setParent(None)
        
        self.scene = MboardScene(self)
        self.view.setScene(self.scene)
        
        if not self.data or not self.data.elements:
            return
        
        for e in self.data.elements:
            etype = e.get("type")
            x, y = e.get("x", 0), e.get("y", 0)
            
            if etype == "text":
                item = EditableTextItem(e.get("content", ""))
                item.setDefaultTextColor(QColor(e.get("color", "white")))
                item.setPos(x, y)
                self.scene.addItem(item)
            elif etype == "sticky":
                w, h = e.get("w", 150), e.get("h", 150)
                item = StickyNoteItem(x, y, w, h, e.get("content", "Quick Note"))
                item.setBrush(QBrush(QColor(e.get("color", "rgba(255, 255, 100, 200)"))))
                self.scene.addItem(item)
            elif etype == "rect":
                w, h = e.get("w", 150), e.get("h", 100)
                item = ResizableRectItem(x, y, w, h)
                item.setBrush(QBrush(QColor(e.get("color", "rgba(0, 210, 255, 100)"))))
                item.setPen(QPen(QColor(0, 210, 255), 2))
                self.scene.addItem(item)
            elif etype == "circle":
                w, h = e.get("w", 100), e.get("h", 100)
                item = ResizableEllipseItem(x, y, w, h)
                item.setBrush(QBrush(QColor(e.get("color", "rgba(255, 100, 100, 100)"))))
                item.setPen(QPen(QColor(255, 100, 100), 2))
                self.scene.addItem(item)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            # Delete selected items
            for item in self.scene.selectedItems():
                self.scene.removeItem(item)
        else:
            super().keyPressEvent(event)

    def close_editor(self):
        self.save_board()
        self.closed.emit()
        self.hide()
