"""
MainWindow: The main application window with 3-zone layout.
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QSplitter, QApplication
)
from PySide6.QtCore import Qt, QPointF, QMimeData
from PySide6.QtGui import QDragEnterEvent, QDropEvent

from model.node_data import NodeData, NodeType, OperationType
from model.graph import Graph
from view.canvas import CanvasView
from view.sidebar import Sidebar
from view.inspector import Inspector
from dialogs.matrix_editor import MatrixEditor


class MainWindow(QMainWindow):
    """
    Main application window with three zones:
    - Zone A: Sidebar (Variable Shelf)
    - Zone B: Canvas (Workbench)
    - Zone C: Inspector
    """
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Matrix Lab")
        self.setMinimumSize(1200, 700)
        
        # Core model
        self.graph = Graph()
        self._matrix_nodes: dict[str, NodeData] = {}  # Track matrix source nodes
        
        self._setup_ui()
        self._connect_signals()
        
        # Apply stylesheet
        self._apply_styles()
    
    def _setup_ui(self) -> None:
        """Setup the main window layout."""
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Zone A: Sidebar
        self.sidebar = Sidebar()
        splitter.addWidget(self.sidebar)
        
        # Zone B: Canvas
        self.canvas = CanvasView(self.graph)
        self.canvas.setAcceptDrops(True)
        splitter.addWidget(self.canvas)
        
        # Zone C: Inspector
        self.inspector = Inspector()
        splitter.addWidget(self.inspector)
        
        # Set initial sizes (250 | flex | 300)
        splitter.setSizes([250, 650, 300])
        splitter.setStretchFactor(0, 0)  # Sidebar fixed
        splitter.setStretchFactor(1, 1)  # Canvas stretches
        splitter.setStretchFactor(2, 0)  # Inspector fixed
        
        layout.addWidget(splitter)
        
        # Enable drops on canvas
        self.canvas.viewport().setAcceptDrops(True)
        self.canvas.viewport().installEventFilter(self)
    
    def _connect_signals(self) -> None:
        """Connect all signals."""
        # Sidebar signals
        self.sidebar.new_matrix_requested.connect(self._on_new_matrix)
        
        # Canvas signals
        self.canvas.node_selected.connect(self._on_node_selected)
    
    def _apply_styles(self) -> None:
        """Apply global stylesheet."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F5F7FA;
            }
            QSplitter::handle {
                background-color: #CFD8DC;
                width: 1px;
            }
            QSplitter::handle:hover {
                background-color: #90A4AE;
            }
            QWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
    
    def _on_new_matrix(self) -> None:
        """Handle new matrix button click."""
        dialog = MatrixEditor(self)
        if dialog.exec():
            name, matrix = dialog.get_result()
            if matrix is not None:
                # Create node data
                node = NodeData(name, NodeType.DATA, OperationType.NONE, matrix)
                self._matrix_nodes[node.id] = node
                
                # Add to sidebar
                self.sidebar.add_matrix(node.id, name, node.shape_str)
    
    def _on_node_selected(self, node: NodeData) -> None:
        """Handle node selection on canvas."""
        self.inspector.set_node(node)
    
    def eventFilter(self, obj, event):
        """Filter events for canvas viewport to handle drops."""
        if obj == self.canvas.viewport():
            if event.type() == event.Type.DragEnter:
                self._handle_drag_enter(event)
                return True
            elif event.type() == event.Type.DragMove:
                # Must accept DragMove for Drop to work
                if event.mimeData().hasText():
                    text = event.mimeData().text()
                    if text.startswith("MATRIX:") or text.startswith("OPERATION:"):
                        event.acceptProposedAction()
                return True
            elif event.type() == event.Type.Drop:
                self._handle_drop(event)
                return True
        return super().eventFilter(obj, event)
    
    def _handle_drag_enter(self, event: QDragEnterEvent) -> None:
        """Accept drag if valid MIME data."""
        if event.mimeData().hasText():
            text = event.mimeData().text()
            if text.startswith("MATRIX:") or text.startswith("OPERATION:"):
                event.acceptProposedAction()
    
    def _handle_drop(self, event: QDropEvent) -> None:
        """Handle drop on canvas."""
        text = event.mimeData().text()
        pos = self.canvas.mapToScene(event.position().toPoint())
        
        if text.startswith("MATRIX:"):
            # Drop a matrix node
            matrix_id = text.split(":", 1)[1]
            self._add_matrix_node_to_canvas(matrix_id, pos)
        
        elif text.startswith("OPERATION:"):
            # Drop an operation node
            parts = text.split(":")
            if len(parts) >= 3:
                op_value = parts[1]
                display_name = parts[2]
                self._add_operation_node_to_canvas(op_value, display_name, pos)
        
        event.acceptProposedAction()
    
    def _add_matrix_node_to_canvas(self, matrix_id: str, pos: QPointF) -> None:
        """Add a matrix node instance to the canvas."""
        source_node = self._matrix_nodes.get(matrix_id)
        if not source_node:
            return
        
        # Create a new node that references the source matrix
        node = NodeData(
            source_node.name,
            NodeType.DATA,
            OperationType.NONE,
            source_node.matrix.copy() if source_node.matrix is not None else None
        )
        
        self.canvas.add_node(node, pos)
    
    def _add_operation_node_to_canvas(self, op_value: str, display_name: str, pos: QPointF) -> None:
        """Add an operation node to the canvas."""
        # Find the operation type
        op_type = None
        for op in OperationType:
            if op.value == op_value:
                op_type = op
                break
        
        if op_type is None:
            return
        
        # Determine node type
        if op_type == OperationType.RESULT:
            node_type = NodeType.RESULT
        else:
            node_type = NodeType.OPERATION
        
        node = NodeData(display_name, node_type, op_type)
        self.canvas.add_node(node, pos)
