"""
NodeItem: Custom QGraphicsItem for visual nodes on the canvas.
"""
from PySide6.QtWidgets import QGraphicsItem, QGraphicsDropShadowEffect, QStyleOptionGraphicsItem, QWidget
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QObject
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath

from model.node_data import NodeData, NodeType, OperationType


# Color constants per UI_UX_Design.md
COLORS = {
    'data_header': QColor("#E3F2FD"),      # Soft Blue
    'operation_header': QColor("#E8F5E9"), # Soft Mint
    'result_header': QColor("#FFD700"),    # Gold
    'body': QColor("#FFFFFF"),             # White
    'border': QColor("#E0E0E0"),           # Light grey
    'error': QColor("#F44336"),            # Red
    'socket': QColor("#546E7A"),           # Slate grey
    'text': QColor("#333333"),             # Dark text
}

NODE_WIDTH = 160
NODE_HEIGHT = 80
HEADER_HEIGHT = 28
SOCKET_RADIUS = 6
CORNER_RADIUS = 8


class NodeSignals(QObject):
    """Signals for NodeItem."""
    selected = Signal(object)  # Emits NodeData
    position_changed = Signal(str)  # Emits node_id
    connection_started = Signal(str, int, QPointF)  # node_id, socket_index, scene_pos
    connection_dropped = Signal(str, int, QPointF)  # node_id, socket_index, scene_pos


class NodeItem(QGraphicsItem):
    """
    Visual representation of a node on the canvas.
    Rounded rectangle with header, body, and input/output sockets.
    """
    
    def __init__(self, node_data: NodeData, parent=None):
        super().__init__(parent)
        self.node_data = node_data
        self.signals = NodeSignals()
        
        # Make item interactive
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        
        # Visual state
        self._hovered = False
        self._dragging_socket = -1  # Which output socket is being dragged (-1 = none)
        
        # Subscribe to data changes
        self.node_data.add_change_callback(self._on_data_changed)
    
    def _on_data_changed(self, node: NodeData) -> None:
        """Handle data changes from the model."""
        self.update()
    
    def boundingRect(self) -> QRectF:
        """Define the bounding box for the item."""
        # Add margin for shadow
        margin = 10
        return QRectF(-margin, -margin, NODE_WIDTH + 2*margin, NODE_HEIGHT + 2*margin)
    
    def _get_header_color(self) -> QColor:
        """Get header color based on node type."""
        if self.node_data.error_state:
            return COLORS['error']
        if self.node_data.node_type == NodeType.DATA:
            return COLORS['data_header']
        elif self.node_data.node_type == NodeType.RESULT:
            return COLORS['result_header']
        else:
            return COLORS['operation_header']
    
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None) -> None:
        """Draw the node."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Shadow effect (simple manual shadow)
        shadow_offset = 4 if self._hovered else 2
        shadow_path = QPainterPath()
        shadow_path.addRoundedRect(shadow_offset, shadow_offset, NODE_WIDTH, NODE_HEIGHT, CORNER_RADIUS, CORNER_RADIUS)
        painter.fillPath(shadow_path, QColor(0, 0, 0, 40))
        
        # Main body
        body_rect = QRectF(0, 0, NODE_WIDTH, NODE_HEIGHT)
        body_path = QPainterPath()
        body_path.addRoundedRect(body_rect, CORNER_RADIUS, CORNER_RADIUS)
        
        # Fill body
        painter.fillPath(body_path, COLORS['body'])
        
        # Header
        header_path = QPainterPath()
        header_path.addRoundedRect(0, 0, NODE_WIDTH, HEADER_HEIGHT, CORNER_RADIUS, CORNER_RADIUS)
        # Clip bottom corners of header
        header_path.addRect(0, HEADER_HEIGHT - CORNER_RADIUS, NODE_WIDTH, CORNER_RADIUS)
        painter.fillPath(header_path, self._get_header_color())
        
        # Border
        border_color = COLORS['error'] if self.node_data.error_state else COLORS['border']
        if self.isSelected():
            border_color = QColor("#2196F3")  # Blue selection
        pen = QPen(border_color, 2 if self.isSelected() else 1)
        painter.setPen(pen)
        painter.drawPath(body_path)
        
        # Header text (node name)
        painter.setPen(COLORS['text'])
        font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(QRectF(8, 4, NODE_WIDTH - 16, HEADER_HEIGHT - 4), 
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                        self.node_data.name[:18])  # Truncate long names
        
        # Body text (shape info)
        font = QFont("Segoe UI", 9)
        painter.setFont(font)
        body_text = self.node_data.shape_str
        if self.node_data.error_state:
            body_text = "Error"
        painter.drawText(QRectF(8, HEADER_HEIGHT + 4, NODE_WIDTH - 16, NODE_HEIGHT - HEADER_HEIGHT - 8),
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                        body_text)
        
        # Draw sockets
        self._draw_sockets(painter)
    
    def _draw_sockets(self, painter: QPainter) -> None:
        """Draw input and output sockets."""
        painter.setBrush(COLORS['socket'])
        painter.setPen(QPen(COLORS['socket'].darker(120), 1))
        
        # Input sockets (left side)
        for i in range(self.node_data.input_count):
            pos = self.get_input_socket_pos(i)
            painter.drawEllipse(pos, SOCKET_RADIUS, SOCKET_RADIUS)
        
        # Output socket (right side) - all nodes except RESULT type have output
        if self.node_data.node_type != NodeType.RESULT or self.node_data.operation == OperationType.RESULT:
            # Actually all nodes can have output except pure result display
            if self.node_data.node_type != NodeType.RESULT:
                pos = self.get_output_socket_pos()
                painter.setBrush(COLORS['socket'])
                painter.drawEllipse(pos, SOCKET_RADIUS, SOCKET_RADIUS)
    
    def get_input_socket_pos(self, index: int) -> QPointF:
        """Get scene position of input socket at index."""
        count = self.node_data.input_count
        if count == 0:
            return QPointF(0, NODE_HEIGHT / 2)
        spacing = (NODE_HEIGHT - HEADER_HEIGHT) / (count + 1)
        y = HEADER_HEIGHT + spacing * (index + 1)
        return QPointF(0, y)
    
    def get_output_socket_pos(self) -> QPointF:
        """Get scene position of output socket."""
        return QPointF(NODE_WIDTH, NODE_HEIGHT / 2)
    
    def get_input_socket_scene_pos(self, index: int) -> QPointF:
        """Get scene position of input socket."""
        return self.mapToScene(self.get_input_socket_pos(index))
    
    def get_output_socket_scene_pos(self) -> QPointF:
        """Get scene position of output socket."""
        return self.mapToScene(self.get_output_socket_pos())
    
    def hoverEnterEvent(self, event) -> None:
        """Handle mouse hover enter."""
        self._hovered = True
        self.update()
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event) -> None:
        """Handle mouse hover leave."""
        self._hovered = False
        self.update()
        super().hoverLeaveEvent(event)
    
    def itemChange(self, change, value):
        """Handle item changes."""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.signals.position_changed.emit(self.node_data.id)
        elif change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            if value:
                self.signals.selected.emit(self.node_data)
        return super().itemChange(change, value)
    
    def mousePressEvent(self, event) -> None:
        """Handle mouse press - check if clicking on socket."""
        pos = event.pos()
        
        # Check output socket
        if self.node_data.node_type != NodeType.RESULT:
            output_pos = self.get_output_socket_pos()
            if (pos - output_pos).manhattanLength() < SOCKET_RADIUS * 2:
                self._dragging_socket = 0  # Output socket
                self.signals.connection_started.emit(
                    self.node_data.id, 
                    -1,  # -1 means output socket
                    self.get_output_socket_scene_pos()
                )
                return
        
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event) -> None:
        """Handle mouse release."""
        if self._dragging_socket >= 0:
            self._dragging_socket = -1
        super().mouseReleaseEvent(event)
    
    def get_clicked_input_socket(self, scene_pos: QPointF) -> int:
        """Check if scene position is over an input socket. Returns socket index or -1."""
        local_pos = self.mapFromScene(scene_pos)
        for i in range(self.node_data.input_count):
            socket_pos = self.get_input_socket_pos(i)
            if (local_pos - socket_pos).manhattanLength() < SOCKET_RADIUS * 3:
                return i
        return -1
