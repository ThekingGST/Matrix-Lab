"""
Inspector: The right panel (Zone C) upgraded to support numerical tables and geometric plots.
"""
from typing import Optional
import numpy as np

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QApplication, QTabWidget, QCheckBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from model.node_data import NodeData, NodeType, OperationType
from view.plot_widget import GeometricPlotWidget


class Inspector(QWidget):
    """
    Right panel that shows detailed matrix data for selected nodes.
    Supports a Numerical View (Table) and a Geometric View (Cartesian plot).
    """
    
    add_matrix_requested = Signal(object)  # Emits NodeData for adding as variable
    dataDragged = Signal(str, object)      # Emits updates from PlotWidget dragging
    
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
        
        # Create Tab Widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #E0E0E0;
                background: white;
                border-radius: 6px;
            }
            QTabBar::tab {
                background: #ECEFF1;
                border: 1px solid #CFD8DC;
                border-bottom-color: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
                color: #546E7A;
            }
            QTabBar::tab:selected {
                background: white;
                border-color: #E0E0E0;
                border-bottom-color: white;
                color: #1976D2;
            }
        """)
        layout.addWidget(self.tabs, 1)
        
        # --- Tab 1: Numerical View ---
        self.num_tab = QWidget()
        num_layout = QVBoxLayout(self.num_tab)
        num_layout.setContentsMargins(4, 4, 4, 4)
        
        self.table = QTableWidget()
        self.table.setStyleSheet("""
            QTableWidget {
                border: none;
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
        num_layout.addWidget(self.table, 1)
        
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
        num_layout.addWidget(self.copy_btn)
        
        self.tabs.addTab(self.num_tab, "Numerical")
        
        # --- Tab 2: Geometric View ---
        self.geo_tab = QWidget()
        geo_layout = QVBoxLayout(self.geo_tab)
        geo_layout.setContentsMargins(4, 4, 4, 4)
        
        # Plot widget
        self.plot_widget = GeometricPlotWidget()
        self.plot_widget.dataDragged.connect(self.dataDragged.emit)
        geo_layout.addWidget(self.plot_widget, 1)
        
        # Layer controls/toggles
        ctrl_layout = QHBoxLayout()
        self.eigen_chk = QCheckBox("Eigenvectors")
        self.eigen_chk.setChecked(True)
        self.eigen_chk.toggled.connect(self._on_toggles_changed)
        ctrl_layout.addWidget(self.eigen_chk)
        
        self.det_chk = QCheckBox("Det Area")
        self.det_chk.setChecked(True)
        self.det_chk.toggled.connect(self._on_toggles_changed)
        ctrl_layout.addWidget(self.det_chk)
        
        geo_layout.addLayout(ctrl_layout)
        
        self.tabs.addTab(self.geo_tab, "Geometric")
        
        # Add Matrix button (only for Result nodes)
        self.add_matrix_btn = QPushButton("Add as Variable")
        self.add_matrix_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px 16px;
                border-radius: 6px;
                font-weight: bold;
                margin-top: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.add_matrix_btn.clicked.connect(self._on_add_matrix_clicked)
        self.add_matrix_btn.hide()
        layout.addWidget(self.add_matrix_btn)
    
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
        self.tabs.hide()
        self.add_matrix_btn.hide()
    
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
        self.tabs.show()
        
        # Routing to Visual vs. Numerical View
        is_visual = node.is_visualizable
        inputs = []
        
        if not is_visual and node.node_type in (NodeType.OPERATION, NodeType.RESULT):
            inputs = [node.get_input(i) for i in range(node.input_count)]
            is_visual = any(inp and inp.is_visualizable for inp in inputs) or (node.matrix is not None and node.is_visualizable)
            
        if is_visual:
            self.tabs.setTabEnabled(1, True)
            self.plot_widget.set_node(node)
            
            # Sync toggles with node metadata
            if not hasattr(node, 'metadata'):
                node.metadata = {}
            self.eigen_chk.setChecked(node.metadata.get("show_eigen", True))
            self.det_chk.setChecked(node.metadata.get("show_det", True))
            
            # Show layers controls only if matrix is 2x2
            has_2x2 = False
            if node.matrix is not None and node.matrix.shape == (2, 2):
                has_2x2 = True
            elif node.node_type in (NodeType.OPERATION, NodeType.RESULT):
                inputs = [node.get_input(i) for i in range(node.input_count)]
                if len(inputs) > 0 and inputs[0] and inputs[0].matrix is not None and inputs[0].matrix.shape == (2, 2):
                    has_2x2 = True
                    
            self.eigen_chk.setVisible(has_2x2)
            self.det_chk.setVisible(has_2x2)
            
            self.tabs.setCurrentIndex(1)  # Focus Geometric View by default
        else:
            self.tabs.setTabEnabled(1, False)
            self.plot_widget.set_node(None)
            self.tabs.setCurrentIndex(0)  # Fall back to Numerical View
        
        # Update Numerical table
        if node.matrix is not None:
            self._display_matrix(node.matrix)
            self.table.show()
            self.copy_btn.show()
        else:
            self.table.hide()
            self.copy_btn.hide()
        
        # Show Add Matrix button only for Result nodes with valid matrix
        if node.operation == OperationType.RESULT and node.matrix is not None and not node.error_state:
            self.add_matrix_btn.show()
        else:
            self.add_matrix_btn.hide()
            
    def _on_toggles_changed(self) -> None:
        """Handle layer toggle changes."""
        if self._current_node:
            if not hasattr(self._current_node, 'metadata'):
                self._current_node.metadata = {}
            self._current_node.metadata["show_eigen"] = self.eigen_chk.isChecked()
            self._current_node.metadata["show_det"] = self.det_chk.isChecked()
            self.plot_widget.update()
    
    def _display_matrix(self, matrix: np.ndarray) -> None:
        """Display a numpy array in the table."""
        if matrix.ndim == 0:
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
                if np.iscomplex(val):
                    text = f"{val:.4g}"
                else:
                    text = f"{float(val.real):.6g}"
                
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Read-only
                self.table.setItem(r, c, item)
        
        self.table.resizeColumnsToContents()
    
    def _copy_to_clipboard(self) -> None:
        """Copy matrix data to clipboard."""
        if self._current_node is None or self._current_node.matrix is None:
            return
        
        matrix = self._current_node.matrix
        if matrix.ndim == 1:
            matrix = matrix.reshape(-1, 1)
        
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
    
    def _on_add_matrix_clicked(self) -> None:
        """Handle Add as Variable button click for Result nodes."""
        if self._current_node and self._current_node.matrix is not None:
            self.add_matrix_requested.emit(self._current_node)
