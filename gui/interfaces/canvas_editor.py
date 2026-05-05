import os
import uuid
from PySide6.QtCore import Qt, QPointF, QRectF, Signal, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPainter, QBrush, QColor, QPen, QPainterPath, QUndoStack, QUndoCommand
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, 
                             QGraphicsItem, QGraphicsRectItem, QGraphicsEllipseItem,
                             QGraphicsTextItem, QFrame, QHBoxLayout, QGraphicsPathItem)

from qfluentwidgets import (TransparentToolButton, FluentIcon as FIF, PrimaryPushButton, 
                            CaptionLabel, LineEdit, ToolButton)
from core.canvas_engine import MboardData, CanvasManager
from gui.components.connector_item import StickyArrowItem

class DrawingPathItem(QGraphicsPathItem):
    def __init__(self, path=None, pen_color=QColor(255, 255, 255), pen_width=2, is_highlighter=False):
        super().__init__(path)
        pen = QPen(pen_color, pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        self.setPen(pen)
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
        
        if is_highlighter:
            self.setOpacity(0.5)
            # Highlighter should be behind other things usually, or use a specific composition mode
            self.setZValue(-1)

class LaserPathItem(QGraphicsPathItem):
    def __init__(self, path=None):
        super().__init__(path)
        pen = QPen(QColor(255, 50, 50), 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        self.setPen(pen)
        self.setZValue(100) # Always on top
        
        # Auto-destruct timer
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.start_fade)
        self.timer.start(2000) # Start fading after 2s

    def start_fade(self):
        self.fade_opacity = 1.0
        self.fade_timer = QTimer()
        self.fade_timer.timeout.connect(self.tick_fade)
        self.fade_timer.start(50) # 20 fps fade

    def tick_fade(self):
        self.fade_opacity -= 0.05
        if self.fade_opacity <= 0:
            self.fade_timer.stop()
            self.cleanup()
        else:
            self.setOpacity(self.fade_opacity)

    def cleanup(self):
        if self.scene():
            self.scene().removeItem(self)

class EditableTextItem(QGraphicsTextItem):
    def __init__(self, text, parent=None, item_id=None):
        super().__init__(text, parent)
        self.id = item_id or str(uuid.uuid4())
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsFocusable)
        self.setTextInteractionFlags(Qt.NoTextInteraction) # Start as draggable
        
        font = self.font()
        font.setPointSize(14)
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

class ResizeHandle(QGraphicsRectItem):
    def __init__(self, parent, handle_type):
        super().__init__(-5, -5, 10, 10, parent)
        self.handle_type = handle_type
        self.setBrush(QBrush(QColor(0, 120, 215)))
        self.setPen(QPen(QColor(255, 255, 255), 1))
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemSendsGeometryChanges)
        self.hide()
        
        if handle_type in (0, 3): # TL, BR
            self.setCursor(Qt.SizeFDiagCursor)
        else: # TR, BL
            self.setCursor(Qt.SizeBDiagCursor)

    def mousePressEvent(self, event):
        self.press_pos = event.scenePos()
        parent = self.parentItem()
        if parent:
            self.init_rect = parent.rect()
            self.init_pos = parent.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        parent = self.parentItem()
        if not parent: return
        
        delta = event.scenePos() - self.press_pos
        rect = self.init_rect
        p_pos = self.init_pos
        
        if self.handle_type == 0: # Top Left
            new_w = max(20, rect.width() - delta.x())
            new_h = max(20, rect.height() - delta.y())
            parent.setRect(0, 0, new_w, new_h)
            parent.setPos(p_pos.x() + (rect.width() - new_w), p_pos.y() + (rect.height() - new_h))
        elif self.handle_type == 1: # Top Right
            new_w = max(20, rect.width() + delta.x())
            new_h = max(20, rect.height() - delta.y())
            parent.setRect(0, 0, new_w, new_h)
            parent.setY(p_pos.y() + (rect.height() - new_h))
        elif self.handle_type == 2: # Bottom Left
            new_w = max(20, rect.width() - delta.x())
            new_h = max(20, rect.height() + delta.y())
            parent.setRect(0, 0, new_w, new_h)
            parent.setX(p_pos.x() + (rect.width() - new_w))
        elif self.handle_type == 3: # Bottom Right
            new_w = max(20, rect.width() + delta.x())
            new_h = max(20, rect.height() + delta.y())
            parent.setRect(0, 0, new_w, new_h)
            
        parent.update_handles()

class ResizableItem:
    """ Mixin for resizable items """
    def init_handles(self):
        self.handles = [ResizeHandle(self, i) for i in range(4)]
        self.update_handles()

    def update_handles(self):
        rect = self.rect()
        self.handles[0].setPos(rect.left(), rect.top())
        self.handles[1].setPos(rect.right(), rect.top())
        self.handles[2].setPos(rect.left(), rect.bottom())
        self.handles[3].setPos(rect.right(), rect.bottom())

    def set_handles_visible(self, visible):
        for h in self.handles:
            h.setVisible(visible)

class ResizableRectItem(QGraphicsRectItem, ResizableItem):
    def __init__(self, x, y, w, h, parent=None, item_id=None):
        super().__init__(0, 0, w, h, parent)
        self.id = item_id or str(uuid.uuid4())
        self.setPos(x, y)
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemSendsGeometryChanges)
        self.init_handles()

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedChange:
            self.set_handles_visible(value)
        return super().itemChange(change, value)

class ResizableEllipseItem(QGraphicsEllipseItem, ResizableItem):
    def __init__(self, x, y, w, h, parent=None, item_id=None):
        super().__init__(0, 0, w, h, parent)
        self.id = item_id or str(uuid.uuid4())
        self.setPos(x, y)
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemSendsGeometryChanges)
        self.init_handles()

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedChange:
            self.set_handles_visible(value)
        return super().itemChange(change, value)

class StickyNoteItem(ResizableRectItem):
    def __init__(self, x, y, w, h, text="Quick Note", item_id=None):
        super().__init__(x, y, w, h, item_id=item_id)
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

# --- UNDO/REDO COMMANDS ---
class AddItemCommand(QUndoCommand):
    def __init__(self, scene, item):
        super().__init__(f"Add {type(item).__name__}")
        self.scene = scene
        self.item = item
    def redo(self):
        self.scene.addItem(self.item)
    def undo(self):
        self.scene.removeItem(self.item)

class DeleteItemsCommand(QUndoCommand):
    def __init__(self, scene, items):
        super().__init__("Delete Items")
        self.scene = scene
        self.items = items
    def redo(self):
        for item in self.items:
            self.scene.removeItem(item)
    def undo(self):
        for item in self.items:
            self.scene.addItem(item)

class TransformCommand(QUndoCommand):
    """ Handles both Move and Resize via start/end state """
    def __init__(self, item, old_pos, old_rect, new_pos, new_rect):
        super().__init__("Transform")
        self.item = item
        self.old_pos = old_pos
        self.old_rect = old_rect
        self.new_pos = new_pos
        self.new_rect = new_rect
    def redo(self):
        self.item.setPos(self.new_pos)
        if hasattr(self.item, 'setRect'):
            self.item.setRect(self.new_rect)
        if hasattr(self.item, 'update_handles'):
            self.item.update_handles()
        if self.item.scene() and hasattr(self.item.scene(), 'update_arrows'):
            self.item.scene().update_arrows()

    def undo(self):
        self.item.setPos(self.old_pos)
        if hasattr(self.item, 'setRect'):
            self.item.setRect(self.old_rect)
        if hasattr(self.item, 'update_handles'):
            self.item.update_handles()
        if self.item.scene() and hasattr(self.item.scene(), 'update_arrows'):
            self.item.scene().update_arrows()

class MboardTool:
    SELECT = "select"
    PEN = "pen"
    HIGHLIGHTER = "highlighter"
    LASER = "laser"
    ERASER_STROKE = "eraser_stroke"
    TEXT = "text"
    STICKY = "sticky"
    RECT = "rect"
    CIRCLE = "circle"
    ARROW = "arrow"

class MboardScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(-5000, -5000, 10000, 10000)
        self.setBackgroundBrush(QBrush(QColor(30, 30, 30)))
        
        self.current_tool = MboardTool.SELECT
        self.current_item = None
        self.drawing_path = None
        self.template = "grid" # grid, dots, lined, cornell, blank
        
    def set_template(self, template):
        self.template = template
        self.update()

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        
        if self.template == "blank":
            return

        painter.setRenderHint(QPainter.Antialiasing, False)
        
        if self.template == "grid":
            pen = QPen(QColor(45, 45, 45), 1)
            painter.setPen(pen)
            left = int(rect.left()) - (int(rect.left()) % 20)
            top = int(rect.top()) - (int(rect.top()) % 20)
            for x in range(left, int(rect.right()), 20):
                painter.drawLine(x, int(rect.top()), x, int(rect.bottom()))
            for y in range(top, int(rect.bottom()), 20):
                painter.drawLine(int(rect.left()), y, int(rect.right()), y)
        
        elif self.template == "dots":
            pen = QPen(QColor(60, 60, 60), 2)
            painter.setPen(pen)
            left = int(rect.left()) - (int(rect.left()) % 30)
            top = int(rect.top()) - (int(rect.top()) % 30)
            for x in range(left, int(rect.right()), 30):
                for y in range(top, int(rect.bottom()), 30):
                    painter.drawPoint(x, y)
                    
        elif self.template == "lined":
            pen = QPen(QColor(50, 50, 70), 1)
            painter.setPen(pen)
            top = int(rect.top()) - (int(rect.top()) % 25)
            for y in range(top, int(rect.bottom()), 25):
                painter.drawLine(int(rect.left()), y, int(rect.right()), y)
            # Vertical margin line
            margin_pen = QPen(QColor(100, 40, 40), 1)
            painter.setPen(margin_pen)
            painter.drawLine(100, int(rect.top()), 100, int(rect.bottom()))

        elif self.template == "cornell":
            # Grid background first
            pen = QPen(QColor(40, 40, 40), 1)
            painter.setPen(pen)
            left = int(rect.left()) - (int(rect.left()) % 20)
            top = int(rect.top()) - (int(rect.top()) % 20)
            for x in range(left, int(rect.right()), 20):
                painter.drawLine(x, int(rect.top()), x, int(rect.bottom()))
            for y in range(top, int(rect.bottom()), 20):
                painter.drawLine(int(rect.left()), y, int(rect.right()), y)
            
            # Cornell lines
            cornell_pen = QPen(QColor(150, 150, 150), 2)
            painter.setPen(cornell_pen)
            # Cue column
            painter.drawLine(-200, -5000, -200, 5000)
            # Summary area
            painter.drawLine(-5000, 3000, 5000, 3000)

    def mousePressEvent(self, event):
        if self.current_tool == MboardTool.SELECT:
            # Capture state for transform undo
            items = self.items(event.scenePos())
            if items:
                self.transform_target = items[0]
                # Find the resizable parent if we clicked a handle
                if isinstance(self.transform_target, ResizeHandle):
                    self.transform_target = self.transform_target.parentItem()
                
                if self.transform_target.flags() & QGraphicsItem.ItemIsSelectable:
                    self.old_pos = self.transform_target.pos()
                    self.old_rect = self.transform_target.rect() if hasattr(self.transform_target, 'rect') else None
            else:
                self.transform_target = None

        if self.current_tool in (MboardTool.PEN, MboardTool.HIGHLIGHTER, MboardTool.LASER):
            self.drawing_path = QPainterPath()
            self.drawing_path.moveTo(event.scenePos())
            
            if self.current_tool == MboardTool.LASER:
                self.current_item = LaserPathItem(self.drawing_path)
            else:
                is_high = self.current_tool == MboardTool.HIGHLIGHTER
                color = QColor(255, 255, 255) if not is_high else QColor(255, 255, 0)
                width = 3 if not is_high else 20
                self.current_item = DrawingPathItem(self.drawing_path, color, width, is_high)
            
            self.addItem(self.current_item)
        elif self.current_tool == MboardTool.ARROW:
            start_item = self.itemAt(event.scenePos(), self.parent().view.transform())
            if start_item and not isinstance(start_item, (MboardScene, StickyArrowItem, DrawingPathItem)):
                # If we clicked on a resize handle, ignore it or find the parent
                if isinstance(start_item, ResizeHandle):
                    start_item = start_item.parentItem()
                
                self.current_item = StickyArrowItem(start_item)
                self.addItem(self.current_item)
        elif self.current_tool == MboardTool.ERASER_STROKE:
            self.erase_at(event.scenePos())
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drawing_path and self.current_item and isinstance(self.current_item, (DrawingPathItem, LaserPathItem)):
            self.drawing_path.lineTo(event.scenePos())
            self.current_item.setPath(self.drawing_path)
        elif isinstance(self.current_item, StickyArrowItem):
            self.current_item.set_temp_end(event.scenePos())
        elif self.current_tool == MboardTool.ERASER_STROKE:
            if event.buttons() & Qt.LeftButton:
                self.erase_at(event.scenePos())
        else:
            super().mouseMoveEvent(event)
            if event.buttons() & Qt.LeftButton:
                self.update_arrows()

    def mouseReleaseEvent(self, event):
        if isinstance(self.current_item, StickyArrowItem):
            end_item = self.itemAt(event.scenePos(), self.parent().view.transform())
            if end_item and end_item != self.current_item.start_item and not isinstance(end_item, (MboardScene, StickyArrowItem, DrawingPathItem)):
                self.current_item.set_end_item(end_item)
                # Remove before push to avoid double-add in redo()
                self.removeItem(self.current_item)
                self.parent().undo_stack.push(AddItemCommand(self, self.current_item))
            else:
                self.removeItem(self.current_item)
        elif self.current_item:
            # Drawing paths: item was added in mousePress
            if isinstance(self.current_item, LaserPathItem):
                pass # Laser pointer doesn't go to undo stack (it auto-destructs)
            else:
                self.removeItem(self.current_item)
                self.parent().undo_stack.push(AddItemCommand(self, self.current_item))
        elif hasattr(self, 'transform_target') and self.transform_target:
            # Check if moved or resized
            new_pos = self.transform_target.pos()
            new_rect = self.transform_target.rect() if hasattr(self.transform_target, 'rect') else None
            if new_pos != self.old_pos or new_rect != self.old_rect:
                self.parent().undo_stack.push(TransformCommand(self.transform_target, self.old_pos, self.old_rect, new_pos, new_rect))
                
        self.drawing_path = None
        self.current_item = None
        super().mouseReleaseEvent(event)

    def erase_at(self, pos):
        items = self.items(pos)
        for item in items:
            # We only erase paths for now as requested (Stroke Eraser)
            if isinstance(item, (DrawingPathItem, LaserPathItem)):
                self.removeItem(item)
        self.update_arrows()

    def update_arrows(self):
        for item in self.items():
            if isinstance(item, StickyArrowItem):
                item.update_path()

class MboardView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setRenderHint(QPainter.TextAntialiasing)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.NoFrame)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.zoom_level = 1.0

    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            zoom_in_factor = 1.25
            zoom_out_factor = 1 / zoom_in_factor
            if event.angleDelta().y() > 0:
                zoom_factor = zoom_in_factor
            else:
                zoom_factor = zoom_out_factor
            self.scale(zoom_factor, zoom_factor)
            self.zoom_level *= zoom_factor
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
            
        self.undo_stack = QUndoStack(self)
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
        
        # Bookmarks Sidebar (Hidden by default)
        self.bookmarks_panel = QFrame(self)
        self.bookmarks_panel.setFixedWidth(200)
        self.bookmarks_panel.setStyleSheet("background: rgba(35, 35, 35, 230); border-left: 1px solid #444;")
        self.bookmarks_panel.hide()
        
        self.bookmarks_layout = QVBoxLayout(self.bookmarks_panel)
        self.bookmarks_layout.addWidget(CaptionLabel("FOCUS BOOKMARKS", self))
        self.add_bookmark_btn = PrimaryPushButton("Add Current View", self)
        self.add_bookmark_btn.clicked.connect(self.add_bookmark)
        self.bookmarks_layout.addWidget(self.add_bookmark_btn)
        self.bookmarks_list_layout = QVBoxLayout()
        self.bookmarks_layout.addLayout(self.bookmarks_list_layout)
        self.bookmarks_layout.addStretch()
        
        # Main UI structure with sidebar
        main_content_layout = QHBoxLayout()
        main_content_layout.setContentsMargins(0, 0, 0, 0)
        main_content_layout.setSpacing(0)
        
        # Re-organize view into layout
        self.layout.removeWidget(self.view)
        main_content_layout.addWidget(self.view)
        main_content_layout.addWidget(self.bookmarks_panel)
        self.layout.addLayout(main_content_layout)
        
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
        self.btn_pen = self.add_tool(FIF.EDIT, "Pen", self.set_pen_mode)
        self.btn_highlighter = self.add_tool(FIF.HIGHTLIGHT, "Highlighter", self.set_highlighter_mode)
        self.btn_laser = self.add_tool(FIF.SEND, "Laser Pointer", self.set_laser_mode)
        self.btn_eraser = self.add_tool(FIF.DELETE, "Eraser", self.set_eraser_mode)
        self.btn_text = self.add_tool(FIF.FONT, "Text", self.add_text_item)
        self.btn_sticky = self.add_tool(FIF.DOCUMENT, "Sticky", self.add_sticky_item)
        self.btn_rect = self.add_tool(FIF.LAYOUT, "Rectangle", lambda: self.add_shape_item("rect"))
        self.btn_circle = self.add_tool(FIF.GLOBE, "Circle", lambda: self.add_shape_item("circle"))
        self.btn_arrow = self.add_tool(FIF.SEND_FILL, "Arrow", self.set_arrow_mode)
        
        toolbar_layout.addStretch()
        
        self.btn_undo = self.add_tool(FIF.LEFT_ARROW, "Undo", self.undo_stack.undo)
        self.btn_redo = self.add_tool(FIF.RIGHT_ARROW, "Redo", self.undo_stack.redo)
        
        toolbar_layout.addSpacing(10)
        
        self.btn_zoom_in = self.add_tool(FIF.ADD, "Zoom In", self.zoom_in)
        self.btn_zoom_out = self.add_tool(FIF.REMOVE, "Zoom Out", self.zoom_out)
        
        self.btn_bookmark = self.add_tool(FIF.TAG, "Bookmarks", self.toggle_bookmarks)
        self.btn_template = self.add_tool(FIF.SETTING, "Template", self.cycle_templates)
        
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
        self.scene.current_tool = MboardTool.SELECT
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

    def set_pen_mode(self):
        self.scene.current_tool = MboardTool.PEN
        self.view.setDragMode(QGraphicsView.DragMode.NoDrag)

    def set_highlighter_mode(self):
        self.scene.current_tool = MboardTool.HIGHLIGHTER
        self.view.setDragMode(QGraphicsView.DragMode.NoDrag)

    def set_laser_mode(self):
        self.scene.current_tool = MboardTool.LASER
        self.view.setDragMode(QGraphicsView.DragMode.NoDrag)

    def set_eraser_mode(self):
        self.scene.current_tool = MboardTool.ERASER_STROKE
        self.view.setDragMode(QGraphicsView.DragMode.NoDrag)

    def set_arrow_mode(self):
        self.scene.current_tool = MboardTool.ARROW
        self.view.setDragMode(QGraphicsView.DragMode.NoDrag)

    def toggle_bookmarks(self):
        if self.bookmarks_panel.isVisible():
            self.bookmarks_panel.hide()
        else:
            self.bookmarks_panel.show()
            self.refresh_bookmarks_ui()

    def add_bookmark(self):
        from qfluentwidgets import LineEdit
        dialog = QWidget() # Simple for now
        center = self.view.mapToScene(self.view.viewport().rect().center())
        zoom = self.view.transform().m11()
        
        name = f"View {len(self.data.viewport.get('bookmarks', [])) + 1}"
        if "bookmarks" not in self.data.viewport:
            self.data.viewport["bookmarks"] = []
            
        self.data.viewport["bookmarks"].append({
            "name": name,
            "x": center.x(),
            "y": center.y(),
            "zoom": zoom
        })
        self.refresh_bookmarks_ui()

    def refresh_bookmarks_ui(self):
        # Clear existing
        while self.bookmarks_list_layout.count():
            item = self.bookmarks_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        for bm in self.data.viewport.get("bookmarks", []):
            btn = PrimaryPushButton(bm["name"], self)
            btn.clicked.connect(lambda checked=False, b=bm: self.jump_to_bookmark(b))
            self.bookmarks_list_layout.addWidget(btn)

    def jump_to_bookmark(self, bm):
        self.view.resetTransform()
        self.view.scale(bm["zoom"], bm["zoom"])
        self.view.centerOn(QPointF(bm["x"], bm["y"]))

    def cycle_templates(self):
        templates = ["grid", "dots", "lined", "cornell", "blank"]
        idx = templates.index(self.scene.template)
        next_idx = (idx + 1) % len(templates)
        self.scene.set_template(templates[next_idx])
        
        from qfluentwidgets import InfoBar, InfoBarPosition
        InfoBar.info("Template Changed", f"Now using {templates[next_idx]}", parent=self, duration=1000)

    def zoom_in(self):
        self.view.scale(1.25, 1.25)
        self.view.zoom_level *= 1.25

    def zoom_out(self):
        self.view.scale(0.8, 0.8)
        self.view.zoom_level *= 0.8

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Keep minimap in position or resize it
        pass

    def add_text_item(self):
        item = EditableTextItem("Double click to edit")
        item.setPos(self.view.mapToScene(self.view.viewport().rect().center()))
        self.undo_stack.push(AddItemCommand(self.scene, item))
        
        # Auto-focus and highlight
        item.setTextInteractionFlags(Qt.TextEditorInteraction)
        item.setFocus()
        cursor = item.textCursor()
        cursor.select(cursor.SelectionType.Document)
        item.setTextCursor(cursor)
        
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
            
        self.undo_stack.push(AddItemCommand(self.scene, item))
        self.set_select_mode()

    def add_sticky_item(self):
        pos = self.view.mapToScene(self.view.viewport().rect().center())
        item = StickyNoteItem(pos.x(), pos.y(), 150, 150)
        self.undo_stack.push(AddItemCommand(self.scene, item))
        self.set_select_mode()

    def save_board(self):
        # Sync title
        self.data.title = self.title_edit.text() or "Untitled Board"
        
        # Update elements list from scene
        self.data.elements = []
        for item in self.scene.items():
            if isinstance(item, QGraphicsTextItem):
                self.data.elements.append({
                    "id": getattr(item, "id", None),
                    "type": "text",
                    "content": item.toPlainText(),
                    "x": item.scenePos().x(),
                    "y": item.scenePos().y(),
                    "color": item.defaultTextColor().name()
                })
            elif isinstance(item, StickyNoteItem):
                self.data.elements.append({
                    "id": getattr(item, "id", None),
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
                    "id": getattr(item, "id", None),
                    "type": "rect",
                    "x": item.scenePos().x(),
                    "y": item.scenePos().y(),
                    "w": item.rect().width(),
                    "h": item.rect().height(),
                    "color": item.brush().color().name(QColor.HexArgb)
                })
            elif isinstance(item, ResizableEllipseItem):
                self.data.elements.append({
                    "id": getattr(item, "id", None),
                    "type": "circle",
                    "x": item.scenePos().x(),
                    "y": item.scenePos().y(),
                    "w": item.rect().width(),
                    "h": item.rect().height(),
                    "color": item.brush().color().name(QColor.HexArgb)
                })
            elif isinstance(item, DrawingPathItem):
                path = item.path()
                points = []
                for i in range(path.elementCount()):
                    el = path.elementAt(i)
                    points.append((el.x, el.y))
                
                self.data.elements.append({
                    "type": "path",
                    "points": points,
                    "color": item.pen().color().name(QColor.HexArgb),
                    "width": item.pen().width(),
                    "is_highlighter": item.opacity() < 1.0
                })
            elif isinstance(item, StickyArrowItem):
                if item.start_item and item.end_item:
                    self.data.elements.append({
                        "type": "arrow",
                        "start_id": getattr(item.start_item, "id", None),
                        "end_id": getattr(item.end_item, "id", None)
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
                item = EditableTextItem(e.get("content", ""), item_id=e.get("id"))
                item.setDefaultTextColor(QColor(e.get("color", "white")))
                item.setPos(x, y)
                self.scene.addItem(item)
            elif etype == "sticky":
                w, h = e.get("w", 150), e.get("h", 150)
                item = StickyNoteItem(x, y, w, h, e.get("content", "Quick Note"), item_id=e.get("id"))
                item.setBrush(QBrush(QColor(e.get("color", "rgba(255, 255, 100, 200)"))))
                self.scene.addItem(item)
            elif etype == "rect":
                w, h = e.get("w", 150), e.get("h", 100)
                item = ResizableRectItem(x, y, w, h, item_id=e.get("id"))
                item.setBrush(QBrush(QColor(e.get("color", "rgba(0, 210, 255, 100)"))))
                item.setPen(QPen(QColor(0, 210, 255), 2))
                self.scene.addItem(item)
            elif etype == "circle":
                w, h = e.get("w", 100), e.get("h", 100)
                item = ResizableEllipseItem(x, y, w, h, item_id=e.get("id"))
                item.setBrush(QBrush(QColor(e.get("color", "rgba(255, 100, 100, 100)"))))
                item.setPen(QPen(QColor(255, 100, 100), 2))
                self.scene.addItem(item)
            elif etype == "path":
                points = e.get("points", [])
                if points:
                    path = QPainterPath()
                    path.moveTo(QPointF(points[0][0], points[0][1]))
                    for pt in points[1:]:
                        path.lineTo(QPointF(pt[0], pt[1]))
                    
                    item = DrawingPathItem(path, QColor(e.get("color", "white")), 
                                           e.get("width", 2), e.get("is_highlighter", False))
                    self.scene.addItem(item)
            elif etype == "arrow":
                # Will reconnect in second pass
                pass
        
        # Second pass to connect arrows
        item_map = {getattr(item, "id", ""): item for item in self.scene.items() if hasattr(item, "id")}
        for e in self.data.elements:
            if e.get("type") == "arrow":
                start = item_map.get(e.get("start_id"))
                end = item_map.get(e.get("end_id"))
                if start and end:
                    arrow = StickyArrowItem(start, end)
                    self.scene.addItem(arrow)

    def keyPressEvent(self, event):
        # 1. Check if we are typing in a text field or editing a note
        focused_widget = self.focusWidget()
        focus_item = self.scene.focusItem()
        
        is_typing = False
        if isinstance(focused_widget, LineEdit) and focused_widget.hasFocus():
            is_typing = True
        elif isinstance(focus_item, QGraphicsTextItem) and focus_item.textInteractionFlags() & Qt.TextEditorInteraction:
            is_typing = True
            
        if is_typing:
            super().keyPressEvent(event)
            return

        key = event.key()
        modifiers = event.modifiers()

        # Undo / Redo (Ctrl+Z, Ctrl+Shift+Z, Ctrl+Y)
        if modifiers & Qt.ControlModifier:
            if key == Qt.Key_Z:
                if modifiers & Qt.ShiftModifier:
                    self.undo_stack.redo()
                else:
                    self.undo_stack.undo()
                return
            elif key == Qt.Key_Y:
                self.undo_stack.redo()
                return

        # Tool Shortcuts (Single Key)
        if modifiers == Qt.NoModifier:
            if key == Qt.Key_S:
                self.set_select_mode()
            elif key == Qt.Key_H:
                self.set_highlighter_mode()
            elif key == Qt.Key_P:
                self.set_pen_mode()
            elif key == Qt.Key_L:
                self.set_laser_mode()
            elif key == Qt.Key_E:
                self.set_eraser_mode()
            elif key == Qt.Key_T:
                self.add_text_item()
            elif key == Qt.Key_B:
                self.toggle_bookmarks()
            elif key in (Qt.Key_Delete, Qt.Key_Backspace):
                items = self.scene.selectedItems()
                if items:
                    self.undo_stack.push(DeleteItemsCommand(self.scene, items))
            else:
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def close_editor(self):
        self.save_board()
        self.closed.emit()
        self.hide()
