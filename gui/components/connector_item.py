from PySide6.QtCore import Qt, QPointF, QLineF
from PySide6.QtGui import QPen, QPainterPath, QColor, QPolygonF
from PySide6.QtWidgets import QGraphicsPathItem, QGraphicsItem

class StickyArrowItem(QGraphicsPathItem):
    def __init__(self, start_item, end_item=None):
        super().__init__()
        self.start_item = start_item
        self.end_item = end_item
        self.setPen(QPen(QColor(200, 200, 200), 2))
        self.setZValue(-1) # Behind elements
        
        # Temporary end point for dragging
        self.temp_end = None
        
        if self.start_item:
            self.update_path()

    def set_end_item(self, item):
        self.end_item = item
        self.update_path()

    def set_temp_end(self, pos):
        self.temp_end = pos
        self.update_path()

    def update_path(self):
        if not self.start_item:
            return
            
        start_pos = self.start_item.sceneBoundingRect().center()
        
        if self.end_item:
            end_pos = self.end_item.sceneBoundingRect().center()
        elif self.temp_end:
            end_pos = self.temp_end
        else:
            return

        line = QLineF(start_pos, end_pos)
        
        # Calculate intersection points to avoid drawing inside shapes
        # For now, simple center-to-center
        path = QPainterPath()
        path.moveTo(start_pos)
        path.lineTo(end_pos)
        
        # Draw arrowhead
        angle = line.angle()
        arrow_size = 10
        
        p1 = end_pos + QPointF(arrow_size * -1, arrow_size * 0.5)
        p2 = end_pos + QPointF(arrow_size * -1, arrow_size * -0.5)
        
        # Rotate points
        import math
        rad = math.radians(-angle)
        
        def rotate(p, center, angle_rad):
            dx = p.x() - center.x()
            dy = p.y() - center.y()
            nx = dx * math.cos(angle_rad) - dy * math.sin(angle_rad)
            ny = dx * math.sin(angle_rad) + dy * math.cos(angle_rad)
            return QPointF(center.x() + nx, center.y() + ny)

        rp1 = rotate(p1, end_pos, rad)
        rp2 = rotate(p2, end_pos, rad)
        
        path.moveTo(end_pos)
        path.lineTo(rp1)
        path.lineTo(rp2)
        path.lineTo(end_pos)
        
        self.setPath(path)
