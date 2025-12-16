"""
Sidebar: The Variable Shelf (Zone A) - inventory of matrices and operations.
"""
from typing import Dict, Callable, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFrame, QScrollArea, QSizePolicy,
    QTreeWidget, QTreeWidgetItem
)
from PySide6.QtCore import Qt, Signal, QMimeData
from PySide6.QtGui import QDrag, QFont

from model.node_data import NodeData, NodeType, OperationType


# Operation display names and categories
OPERATIONS = {
    "Arithmetic": [
        (OperationType.ADD, "Add (+)"),
        (OperationType.SUBTRACT, "Subtract (-)"),
        (OperationType.MULTIPLY_SCALAR, "Scalar Multiply"),
        (OperationType.MULTIPLY_ELEMENTWISE, "Element Multiply"),
        (OperationType.DIVIDE_ELEMENTWISE, "Element Divide"),
    ],
    "Linear Algebra": [
        (OperationType.DOT, "Dot Product (@)"),
        (OperationType.CROSS, "Cross Product"),
        (OperationType.TRANSPOSE, "Transpose"),
        (OperationType.INVERSE, "Inverse"),
        (OperationType.PSEUDO_INVERSE, "Pseudo-Inverse"),
    ],
    "Properties": [
        (OperationType.DETERMINANT, "Determinant"),
        (OperationType.TRACE, "Trace"),
        (OperationType.RANK, "Rank"),
    ],
    "Decompositions": [
        (OperationType.EIGENVALUES, "Eigenvalues"),
        (OperationType.EIGENVECTORS, "Eigenvectors"),
        (OperationType.SVD, "SVD (Singular Values)"),
    ],
    "Solvers": [
        (OperationType.SOLVE, "Solve (Ax=B)"),
    ],
    "Output": [
        (OperationType.RESULT, "Result Display"),
    ],
}


class DraggableListWidget(QListWidget):
    """List widget that supports drag operations."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setDragDropMode(QListWidget.DragDropMode.DragOnly)
    
    def startDrag(self, supportedActions):
        """Custom drag with MIME data."""
        item = self.currentItem()
        if item:
            drag = QDrag(self)
            mime_data = QMimeData()
            
            # Store item data in MIME
            data = item.data(Qt.ItemDataRole.UserRole)
            if data:
                if isinstance(data, tuple):
                    mime_data.setText(f"OPERATION:{data[0].value}:{data[1]}")
                else:
                    mime_data.setText(f"MATRIX:{data}")
            
            drag.setMimeData(mime_data)
            drag.exec(Qt.DropAction.CopyAction)


class DraggableTreeWidget(QTreeWidget):
    """Tree widget that supports drag operations for operation nodes."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setDragDropMode(QTreeWidget.DragDropMode.DragOnly)
        self.setHeaderHidden(True)
    
    def startDrag(self, supportedActions):
        """Custom drag with MIME data."""
        item = self.currentItem()
        if item and item.parent():  # Only allow dragging child items (operations), not categories
            drag = QDrag(self)
            mime_data = QMimeData()
            
            # Store item data in MIME
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and isinstance(data, tuple):
                mime_data.setText(f"OPERATION:{data[0].value}:{data[1]}")
            
            drag.setMimeData(mime_data)
            drag.exec(Qt.DropAction.CopyAction)


class Sidebar(QWidget):
    """
    Left sidebar containing:
    - Variable list (defined matrices)
    - New Matrix button
    - Operations library (collapsible tree)
    """
    
    new_matrix_requested = Signal()
    matrix_drag_started = Signal(str)  # matrix_id
    operation_drag_started = Signal(str, str)  # operation_type, display_name
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(250)
        self.setMaximumWidth(300)
        
        self._matrix_items: Dict[str, QListWidgetItem] = {}
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup the sidebar UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # ===== VARIABLES SECTION =====
        header = QLabel("Variables")
        header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        layout.addWidget(header)
        
        # New Matrix button
        new_matrix_btn = QPushButton("+ New Matrix")
        new_matrix_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        new_matrix_btn.clicked.connect(self.new_matrix_requested.emit)
        layout.addWidget(new_matrix_btn)
        
        # Matrix list
        self.matrix_list = DraggableListWidget()
        self.matrix_list.setMinimumHeight(100)
        self.matrix_list.setMaximumHeight(200)
        self.matrix_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                background: white;
                padding: 4px;
            }
            QListWidget::item {
                padding: 10px 12px;
                border-radius: 4px;
                margin: 2px 0;
                color: #333;
                background: #FAFAFA;
                border: 1px solid #F0F0F0;
            }
            QListWidget::item:selected {
                background-color: #E3F2FD;
                color: #1976D2;
                border: 1px solid #2196F3;
                font-weight: bold;
            }
            QListWidget::item:hover {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
            }
        """)
        layout.addWidget(self.matrix_list)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)
        
        # ===== OPERATIONS SECTION =====
        ops_header = QLabel("Operations")
        ops_header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        layout.addWidget(ops_header)
        
        # Operations tree (collapsible categories)
        self.operations_tree = DraggableTreeWidget()
        self.operations_tree.setIndentation(15)
        self.operations_tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                background: #FAFAFA;
                padding: 4px;
            }
            QTreeWidget::item {
                padding: 8px 6px;
                color: #333;
                border-radius: 4px;
                margin: 2px 0;
            }
            QTreeWidget::item:selected {
                background-color: #E3F2FD;
                color: #1976D2;
                font-weight: bold;
            }
            QTreeWidget::item:hover {
                background-color: #F5F5F5;
                color: #1976D2;
            }
            QTreeWidget::branch {
                background: transparent;
            }
            QTreeWidget::branch:has-children:closed {
                image: url(none);
                border: none;
            }
            QTreeWidget::branch:has-children:open {
                image: url(none);
                border: none;
            }
        """)
        
        # Populate tree with operation categories
        for category, operations in OPERATIONS.items():
            # Create category item (parent) with arrow only
            category_item = QTreeWidgetItem([f"▼ {category}"])  # Start with down arrow (expanded)
            category_item.setFont(0, QFont("Segoe UI", 10, QFont.Weight.Bold))
            category_item.setForeground(0, Qt.GlobalColor.darkBlue)
            category_item.setExpanded(True)  # Start expanded
            
            # Add operations as children with subtle indentation
            for op_type, display_name in operations:
                child_item = QTreeWidgetItem([f"  {display_name}"])
                child_item.setData(0, Qt.ItemDataRole.UserRole, (op_type, display_name))
                child_item.setFont(0, QFont("Segoe UI", 9))
                category_item.addChild(child_item)
            
            self.operations_tree.addTopLevelItem(category_item)
        
        # Connect expand/collapse signals to update arrows
        self.operations_tree.itemExpanded.connect(self._on_item_expanded)
        self.operations_tree.itemCollapsed.connect(self._on_item_collapsed)
        
        layout.addWidget(self.operations_tree, 1)
    
    def _on_item_expanded(self, item: QTreeWidgetItem) -> None:
        """Update arrow when item is expanded."""
        text = item.text(0)
        if text.startswith("▶"):
            # Replace right arrow with down arrow
            new_text = "▼" + text[1:]
            item.setText(0, new_text)
    
    def _on_item_collapsed(self, item: QTreeWidgetItem) -> None:
        """Update arrow when item is collapsed."""
        text = item.text(0)
        if text.startswith("▼"):
            # Replace down arrow with right arrow
            new_text = "▶" + text[1:]
            item.setText(0, new_text)
    
    def add_matrix(self, node_id: str, name: str, shape: str) -> None:
        """Add a matrix to the variable list."""
        item = QListWidgetItem(f"{name} [{shape}]")
        item.setData(Qt.ItemDataRole.UserRole, node_id)
        self.matrix_list.addItem(item)
        self._matrix_items[node_id] = item
    
    def remove_matrix(self, node_id: str) -> None:
        """Remove a matrix from the variable list."""
        if node_id in self._matrix_items:
            item = self._matrix_items.pop(node_id)
            row = self.matrix_list.row(item)
            self.matrix_list.takeItem(row)
    
    def update_matrix(self, node_id: str, name: str, shape: str) -> None:
        """Update matrix display in list."""
        if node_id in self._matrix_items:
            self._matrix_items[node_id].setText(f"{name} [{shape}]")
