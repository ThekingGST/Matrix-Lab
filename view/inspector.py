"""
Inspector: The right panel (Zone C) for detailed data viewing.
"""
from typing import Optional
import numpy as np

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from model.node_data import NodeData


class Inspector(QWidget):
    """
    Right panel that shows detailed matrix data for selected nodes.
    Context-sensitive: shows tips when nothing selected, data when node selected.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(280)
        
        self._current_node: Optional[NodeData] = None
        
        self._setup_ui()
        self._show_empty_state()
    
    def _setup_ui(self) -> None:
        """Setup the inspector UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Header
        self.header_label = QLabel("Inspector")
        self.header_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.header_label.setStyleSheet("color: #1976D2; padding: 4px;")
        layout.addWidget(self.header_label)
        
        # Node info section (card-style)
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("""
            QLabel {
                background: white;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                padding: 12px;
                color: #333;
            }
        """)
        layout.addWidget(self.info_label)
        
        # Data table (hidden initially)
        self.table = QTableWidget()
        self.table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                background: white;
                gridline-color: #F0F0F0;
            }
            QTableWidget::item {
                padding: 4px;
                color: #333;
            }
            QHeaderView::section {
                background-color: #666666;
                color: white;
                padding: 6px;
                border: none;
                font-weight: bold;
            }
        """)
        self.table.hide()
        layout.addWidget(self.table, 1)
        
        # Copy button
        self.copy_btn = QPushButton("Copy to Clipboard")
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 16px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        """)
        self.copy_btn.clicked.connect(self._copy_to_clipboard)
        self.copy_btn.hide()
        layout.addWidget(self.copy_btn)
        
        # Stretch at bottom
        layout.addStretch()
    
    def _show_empty_state(self) -> None:
        """Show the empty/tips state."""
        self.info_label.setText(
            "<div style='line-height: 1.6;'>"
            "<b style='color: #1976D2; font-size: 11pt;'>Quick Tips</b><br><br>"
            "• <b>Right-click + drag</b> → Pan canvas<br>"
            "• <b>Scroll wheel</b> → Zoom in/out<br>"
            "• <b>Drag from socket</b> → Create wire<br>"
            "• <b>Click node</b> → View details here<br><br>"
            "<i style='color: #666;'>Drag matrices from the sidebar onto the canvas to begin.</i>"
            "</div>"
        )
        self.table.hide()
        self.copy_btn.hide()
    
    def set_node(self, node: Optional[NodeData]) -> None:
        """Update inspector to show data for the given node."""
        self._current_node = node
        
        if node is None:
            self._show_empty_state()
            return
        
        # Update info label
        info_text = f"<b>{node.name}</b><br>"
        info_text += f"Type: {node.node_type.value.title()}<br>"
        info_text += f"Shape: {node.shape_str}<br>"
        
        if node.error_state:
            info_text += f"<span style='color: red;'>Error: {node.error_state}</span>"
        
        self.info_label.setText(info_text)
        
        # Update table
        if node.matrix is not None:
            self._display_matrix(node.matrix)
            self.table.show()
            self.copy_btn.show()
        else:
            self.table.hide()
            self.copy_btn.hide()
    
    def _display_matrix(self, matrix: np.ndarray) -> None:
        """Display a numpy array in the table."""
        if matrix.ndim == 0:
            # Scalar
            self.table.setRowCount(1)
            self.table.setColumnCount(1)
            item = QTableWidgetItem(f"{float(matrix):.6g}")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(0, 0, item)
            return
        
        if matrix.ndim == 1:
            matrix = matrix.reshape(-1, 1)
        
        rows, cols = matrix.shape
        self.table.setRowCount(rows)
        self.table.setColumnCount(cols)
        
        for r in range(rows):
            for c in range(cols):
                val = matrix[r, c]
                # Format complex numbers if needed
                if np.iscomplex(val):
                    text = f"{val:.4g}"
                else:
                    text = f"{float(val.real):.6g}"
                
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Read-only
                self.table.setItem(r, c, item)
        
        # Resize columns to content
        self.table.resizeColumnsToContents()
    
    def _copy_to_clipboard(self) -> None:
        """Copy matrix data to clipboard."""
        if self._current_node is None or self._current_node.matrix is None:
            return
        
        matrix = self._current_node.matrix
        if matrix.ndim == 1:
            matrix = matrix.reshape(-1, 1)
        
        # Format as tab-separated values
        lines = []
        for r in range(matrix.shape[0]):
            row_vals = []
            for c in range(matrix.shape[1] if matrix.ndim > 1 else 1):
                val = matrix[r, c] if matrix.ndim > 1 else matrix[r]
                row_vals.append(f"{val:.6g}")
            lines.append("\t".join(row_vals))
        
        text = "\n".join(lines)
        QApplication.clipboard().setText(text)
    
    def refresh(self) -> None:
        """Refresh display for current node."""
        if self._current_node:
            self.set_node(self._current_node)
