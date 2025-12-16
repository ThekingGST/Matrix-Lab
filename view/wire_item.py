"""
WireItem: Cubic Bezier curve connecting node sockets.
"""
from PySide6.QtWidgets import QGraphicsPathItem
from PySide6.QtCore import QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QPainterPath


# Wire colors per UI_UX_Design.md
WIRE_COLOR = QColor("#546E7A")      # Slate Grey
WIRE_ERROR_COLOR = QColor("#F44336") # Red
WIRE_HOVER_COLOR = QColor("#78909C") # Lighter slate


class WireItem(QGraphicsPathItem):
    """
    Visual connection between two node sockets using cubic Bezier curves.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.source_pos = QPointF(0, 0)
        self.target_pos = QPointF(100, 100)
        self.is_error = False
        self._hovered = False
        
        self.setAcceptHoverEvents(True)
        self.setZValue(-1)  # Draw behind nodes
        
        # Make wire selectable
        self.setFlag(QGraphicsPathItem.GraphicsItemFlag.ItemIsSelectable, True)
        
        self._update_path()
    
    def set_positions(self, source: QPointF, target: QPointF) -> None:
        """Update wire endpoints."""
        self.source_pos = source
        self.target_pos = target
        self._update_path()
    
    def set_error(self, is_error: bool) -> None:
        """Set error state (turns wire red)."""
        self.is_error = is_error
        self.update()
    
    def _update_path(self) -> None:
        """Recalculate the Bezier curve path."""
        path = QPainterPath()
        path.moveTo(self.source_pos)
        
        # Calculate control points for smooth curve
        dx = abs(self.target_pos.x() - self.source_pos.x())
        control_offset = max(dx * 0.5, 50)  # Minimum curve offset
        
        ctrl1 = QPointF(self.source_pos.x() + control_offset, self.source_pos.y())
        ctrl2 = QPointF(self.target_pos.x() - control_offset, self.target_pos.y())
        
        path.cubicTo(ctrl1, ctrl2, self.target_pos)
        self.setPath(path)
    
    def paint(self, painter: QPainter, option, widget=None) -> None:
        """Draw the wire."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Choose color
        if self.isSelected():
            color = QColor("#2196F3")  # Blue when selected
        elif self.is_error:
            color = WIRE_ERROR_COLOR
        elif self._hovered:
            color = WIRE_HOVER_COLOR
        else:
            color = WIRE_COLOR
        
        # Draw wire
        width = 4 if self.isSelected() else (3 if self._hovered else 2)
        pen = QPen(color, width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawPath(self.path())
    
    def hoverEnterEvent(self, event) -> None:
        """Handle hover enter."""
        self._hovered = True
        self.update()
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event) -> None:
        """Handle hover leave."""
        self._hovered = False
        self.update()
        super().hoverLeaveEvent(event)


# Import Qt namespace for pen cap style
from PySide6.QtCore import Qt
