from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPen, QBrush
from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsItem, QGraphicsTextItem

# We re-implement the resizing logic here to keep it standalone and avoid circular imports
from gui.interfaces.canvas_editor import ResizeHandle, ResizableItem

class SelectionAreaItem(QGraphicsRectItem, ResizableItem):
    def __init__(self, x, y, w, h):
        super().__init__(0, 0, w, h)
        self.setPos(x, y)
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemSendsGeometryChanges)
        
        # Styling
        self.setPen(QPen(QColor(0, 255, 170), 2, Qt.DashLine))
        self.setBrush(QBrush(QColor(0, 255, 170, 30)))
        
        # Label
        self.label = QGraphicsTextItem("SELECTION AREA", self)
        self.label.setDefaultTextColor(QColor(0, 255, 170))
        font = self.label.font()
        font.setPointSize(8)
        font.setBold(True)
        self.label.setFont(font)
        self.label.setPos(5, 5)
        
        self.init_handles()
        self.set_handles_visible(True)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedChange:
            # Keep handles always visible for this specific item while active
            self.set_handles_visible(True)
        return super().itemChange(change, value)

    def setRect(self, *args):
        super().setRect(*args)
        if hasattr(self, 'update_handles'):
            self.update_handles()
