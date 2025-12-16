"""
Canvas: The main workbench with infinite grid, panning, and zooming.
"""
from typing import Dict, Optional, Tuple
from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QWidget
)
from PySide6.QtCore import Qt, QPointF, Signal, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QWheelEvent, QMouseEvent

from model.node_data import NodeData, NodeType, OperationType
from model.graph import Graph
from view.node_item import NodeItem
from view.wire_item import WireItem


# Canvas colors per UI_UX_Design.md
CANVAS_BG = QColor("#F5F7FA")
GRID_COLOR = QColor("#E1E4E8")
GRID_SIZE = 20


class CanvasScene(QGraphicsScene):
    """
    Custom scene with grid background.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackgroundBrush(CANVAS_BG)
    
    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        """Draw grid lines."""
        super().drawBackground(painter, rect)
        
        painter.setPen(QPen(GRID_COLOR, 0.5))
        
        # Calculate grid bounds
        left = int(rect.left()) - (int(rect.left()) % GRID_SIZE)
        top = int(rect.top()) - (int(rect.top()) % GRID_SIZE)
        
        # Draw vertical lines
        x = left
        while x < rect.right():
            painter.drawLine(x, int(rect.top()), x, int(rect.bottom()))
            x += GRID_SIZE
        
        # Draw horizontal lines
        y = top
        while y < rect.bottom():
            painter.drawLine(int(rect.left()), y, int(rect.right()), y)
            y += GRID_SIZE


class CanvasView(QGraphicsView):
    """
    Main canvas view with pan/zoom and node management.
    """
    
    node_selected = Signal(object)  # Emits NodeData or None
    
    def __init__(self, graph: Graph, parent=None):
        super().__init__(parent)
        
        self.graph = graph
        self._scene = CanvasScene(self)
        self._scene.setSceneRect(-5000, -5000, 10000, 10000)
        self.setScene(self._scene)
        
        # Node and wire tracking
        self._node_items: Dict[str, NodeItem] = {}
        self._wire_items: Dict[Tuple[str, str, int], WireItem] = {}
        
        # Interaction state
        self._panning = False
        self._pan_start = QPointF()
        self._temp_wire: Optional[WireItem] = None
        self._connecting_from: Optional[Tuple[str, int]] = None  # (node_id, socket_index)
        
        # View settings
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        
        # Selection handling
        self._scene.selectionChanged.connect(self._on_selection_changed)
    
    def add_node(self, node_data: NodeData, pos: QPointF = None) -> NodeItem:
        """Add a node to the canvas."""
        # Add to graph model
        self.graph.add_node(node_data)
        
        # Create visual item
        node_item = NodeItem(node_data)
        if pos:
            node_item.setPos(pos)
        
        # Connect signals
        node_item.signals.position_changed.connect(self._on_node_moved)
        node_item.signals.connection_started.connect(self._on_connection_started)
        
        # Add to scene
        self._scene.addItem(node_item)
        self._node_items[node_data.id] = node_item
        
        return node_item
    
    def remove_node(self, node_id: str) -> None:
        """Remove a node from the canvas."""
        if node_id in self._node_items:
            # Remove connected wires first
            wires_to_remove = [
                key for key in self._wire_items 
                if key[0] == node_id or key[1] == node_id
            ]
            for key in wires_to_remove:
                self._remove_wire(key)
            
            # Remove node item
            item = self._node_items.pop(node_id)
            self._scene.removeItem(item)
            
            # Remove from graph
            self.graph.remove_node(node_id)
    
    def connect_nodes(self, source_id: str, target_id: str, input_index: int) -> bool:
        """
        Create a connection between two nodes.
        Returns False if connection failed (cycle, invalid, etc.)
        """
        if not self.graph.connect(source_id, target_id, input_index):
            return False
        
        # Create wire visual
        wire = WireItem()
        key = (source_id, target_id, input_index)
        self._wire_items[key] = wire
        self._scene.addItem(wire)
        
        # Update wire positions
        self._update_wire(key)
        
        # Trigger computation
        self.graph.propagate_from(source_id)
        
        return True
    
    def _update_wire(self, key: Tuple[str, str, int]) -> None:
        """Update wire position based on connected nodes."""
        source_id, target_id, input_index = key
        wire = self._wire_items.get(key)
        if not wire:
            return
        
        source_item = self._node_items.get(source_id)
        target_item = self._node_items.get(target_id)
        
        if source_item and target_item:
            source_pos = source_item.get_output_socket_scene_pos()
            target_pos = target_item.get_input_socket_scene_pos(input_index)
            wire.set_positions(source_pos, target_pos)
            
            # Check for error state
            target_node = self.graph.nodes.get(target_id)
            if target_node and target_node.error_state:
                wire.set_error(True)
            else:
                wire.set_error(False)
    
    def _remove_wire(self, key: Tuple[str, str, int]) -> None:
        """Remove a wire."""
        if key in self._wire_items:
            wire = self._wire_items.pop(key)
            self._scene.removeItem(wire)
            self.graph.disconnect(key[0], key[1], key[2])
    
    def _on_node_moved(self, node_id: str) -> None:
        """Handle node position change - update connected wires."""
        # Update all wires connected to this node
        for key in self._wire_items:
            if key[0] == node_id or key[1] == node_id:
                self._update_wire(key)
    
    def _on_connection_started(self, node_id: str, socket_index: int, scene_pos: QPointF) -> None:
        """Start drawing a temporary wire."""
        self._connecting_from = (node_id, socket_index)
        
        # Create temporary wire
        self._temp_wire = WireItem()
        self._temp_wire.set_positions(scene_pos, scene_pos)
        self._scene.addItem(self._temp_wire)
    
    def _on_selection_changed(self) -> None:
        """Handle scene selection changes."""
        selected = self._scene.selectedItems()
        if selected and isinstance(selected[0], NodeItem):
            self.node_selected.emit(selected[0].node_data)
        else:
            self.node_selected.emit(None)
    
    def wheelEvent(self, event: QWheelEvent) -> None:
        """Handle zoom with scroll wheel."""
        factor = 1.15
        if event.angleDelta().y() < 0:
            factor = 1 / factor
        
        self.scale(factor, factor)
    
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press for panning."""
        if event.button() == Qt.MouseButton.RightButton:
            self._panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        else:
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse move for panning and wire drawing."""
        if self._panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(
                int(self.horizontalScrollBar().value() - delta.x())
            )
            self.verticalScrollBar().setValue(
                int(self.verticalScrollBar().value() - delta.y())
            )
        elif self._temp_wire and self._connecting_from:
            # Update temp wire endpoint
            scene_pos = self.mapToScene(event.pos())
            source_id, _ = self._connecting_from
            source_item = self._node_items.get(source_id)
            if source_item:
                self._temp_wire.set_positions(
                    source_item.get_output_socket_scene_pos(),
                    scene_pos
                )
        else:
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release."""
        if event.button() == Qt.MouseButton.RightButton and self._panning:
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
        elif self._temp_wire and self._connecting_from:
            # Try to complete connection
            scene_pos = self.mapToScene(event.pos())
            self._try_complete_connection(scene_pos)
            
            # Remove temp wire
            self._scene.removeItem(self._temp_wire)
            self._temp_wire = None
            self._connecting_from = None
        else:
            super().mouseReleaseEvent(event)
    
    def _try_complete_connection(self, scene_pos: QPointF) -> None:
        """Try to complete a wire connection at the given position."""
        if not self._connecting_from:
            return
        
        source_id, _ = self._connecting_from
        
        # Find if we're over an input socket
        for node_id, node_item in self._node_items.items():
            if node_id == source_id:
                continue  # Can't connect to self
            
            socket_index = node_item.get_clicked_input_socket(scene_pos)
            if socket_index >= 0:
                # Try to make connection
                self.connect_nodes(source_id, node_id, socket_index)
                return
