"""
MatrixEditor: Modal dialog for creating and editing matrices.
"""
from typing import Optional
import numpy as np

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QSpinBox, QTableWidget, QTableWidgetItem,
    QPushButton, QWidget, QLabel, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator


class MatrixEditor(QDialog):
    """
    Modal dialog for editing matrix values.
    Includes name input, dimension spinboxes, grid editor, and quick-fill buttons.
    """
    
    def __init__(self, parent=None, name: str = "", matrix: Optional[np.ndarray] = None):
        super().__init__(parent)
        self.setWindowTitle("Matrix Editor")
        self.setMinimumSize(400, 450)
        
        self._result_matrix: Optional[np.ndarray] = None
        self._result_name: str = ""
        
        # Default values
        default_rows = matrix.shape[0] if matrix is not None else 3
        default_cols = matrix.shape[1] if matrix is not None and matrix.ndim > 1 else 3
        
        self._setup_ui(name, default_rows, default_cols)
        
        # Load existing matrix if provided
        if matrix is not None:
            self._load_matrix(matrix)
    
    def _setup_ui(self, name: str, rows: int, cols: int) -> None:
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Name input
        form_layout = QFormLayout()
        self.name_input = QLineEdit(name or "Matrix")
        form_layout.addRow("Name:", self.name_input)
        layout.addLayout(form_layout)
        
        # Dimension controls
        dim_layout = QHBoxLayout()
        dim_layout.addWidget(QLabel("Rows:"))
        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 100)
        self.rows_spin.setValue(rows)
        self.rows_spin.valueChanged.connect(self._on_dimensions_changed)
        dim_layout.addWidget(self.rows_spin)
        
        dim_layout.addWidget(QLabel("Cols:"))
        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(1, 100)
        self.cols_spin.setValue(cols)
        self.cols_spin.valueChanged.connect(self._on_dimensions_changed)
        dim_layout.addWidget(self.cols_spin)
        dim_layout.addStretch()
        layout.addLayout(dim_layout)
        
        # Quick fill buttons
        fill_layout = QHBoxLayout()
        fill_layout.addWidget(QLabel("Quick Fill:"))
        
        identity_btn = QPushButton("Identity")
        identity_btn.clicked.connect(self._fill_identity)
        fill_layout.addWidget(identity_btn)
        
        zeros_btn = QPushButton("Zeros")
        zeros_btn.clicked.connect(self._fill_zeros)
        fill_layout.addWidget(zeros_btn)
        
        random_btn = QPushButton("Random")
        random_btn.clicked.connect(self._fill_random)
        fill_layout.addWidget(random_btn)
        
        fill_layout.addStretch()
        layout.addLayout(fill_layout)
        
        # Matrix grid
        self.table = QTableWidget(rows, cols)
        
        # Style the headers with dark gray background
        self.table.setStyleSheet("""
            QTableWidget {
                gridline-color: #E0E0E0;
            }
            QHeaderView::section {
                background-color: #666666;
                color: white;
                padding: 4px;
                border: 1px solid #555555;
                font-weight: bold;
            }
        """)
        
        # Connect cell change to auto-resize columns
        self.table.itemChanged.connect(self._on_cell_changed)
        
        self._init_table()
        layout.addWidget(self.table, 1)  # Stretch factor 1 = expand to fill space
        
        # Dialog buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._on_save)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
        
        # Auto-resize dialog to fit content
        self._resize_to_fit_content()
    
    def _init_table(self) -> None:
        """Initialize table with zero values."""
        rows = self.rows_spin.value()
        cols = self.cols_spin.value()
        self.table.setRowCount(rows)
        self.table.setColumnCount(cols)
        
        for r in range(rows):
            for c in range(cols):
                item = QTableWidgetItem("0")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(r, c, item)
    
    def _on_cell_changed(self, item: QTableWidgetItem) -> None:
        """Auto-resize column when cell content changes."""
        if item:
            col = item.column()
            self.table.resizeColumnToContents(col)
            # Ensure minimum width
            if self.table.columnWidth(col) < 50:
                self.table.setColumnWidth(col, 50)
    
    def _resize_to_fit_content(self) -> None:
        """Resize dialog to fit table content with minimal dead space."""
        # Resize columns to content
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()
        
        # Calculate required size
        width = self.table.verticalHeader().width() + 4  # Row header width
        for i in range(self.table.columnCount()):
            width += self.table.columnWidth(i)
        width += self.table.verticalScrollBar().sizeHint().width() + 40  # Margins
        
        height = self.table.horizontalHeader().height() + 4  # Column header height
        for i in range(self.table.rowCount()):
            height += self.table.rowHeight(i)
        height += 250  # Space for other controls (name, dimensions, buttons)
        
        # Set dialog size
        self.resize(max(400, min(width, 800)), max(450, min(height, 700)))
    
    def _on_dimensions_changed(self) -> None:
        """Handle dimension changes."""
        rows = self.rows_spin.value()
        cols = self.cols_spin.value()
        
        old_rows = self.table.rowCount()
        old_cols = self.table.columnCount()
        
        self.table.setRowCount(rows)
        self.table.setColumnCount(cols)
        
        # Initialize new cells
        for r in range(rows):
            for c in range(cols):
                if r >= old_rows or c >= old_cols:
                    item = QTableWidgetItem("0")
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.table.setItem(r, c, item)
        
        # Resize dialog to fit new dimensions
        self._resize_to_fit_content()
    
    def _load_matrix(self, matrix: np.ndarray) -> None:
        """Load values from numpy array into table."""
        if matrix.ndim == 1:
            matrix = matrix.reshape(-1, 1)
        
        rows, cols = matrix.shape
        self.rows_spin.setValue(rows)
        self.cols_spin.setValue(cols)
        self.table.setRowCount(rows)
        self.table.setColumnCount(cols)
        
        for r in range(rows):
            for c in range(cols):
                item = QTableWidgetItem(f"{matrix[r, c]:.6g}")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(r, c, item)
    
    def _get_matrix_from_table(self) -> Optional[np.ndarray]:
        """Extract numpy array from table values."""
        rows = self.table.rowCount()
        cols = self.table.columnCount()
        matrix = np.zeros((rows, cols))
        
        for r in range(rows):
            for c in range(cols):
                item = self.table.item(r, c)
                text = item.text() if item else "0"
                try:
                    matrix[r, c] = float(text) if text else 0.0
                except ValueError:
                    QMessageBox.warning(
                        self, "Invalid Input",
                        f"Invalid number at row {r+1}, column {c+1}: '{text}'"
                    )
                    return None
        
        return matrix
    
    def _fill_identity(self) -> None:
        """Fill with identity matrix."""
        rows = self.rows_spin.value()
        cols = self.cols_spin.value()
        
        for r in range(rows):
            for c in range(cols):
                val = "1" if r == c else "0"
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(r, c, item)
    
    def _fill_zeros(self) -> None:
        """Fill with zeros."""
        rows = self.rows_spin.value()
        cols = self.cols_spin.value()
        
        for r in range(rows):
            for c in range(cols):
                item = QTableWidgetItem("0")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(r, c, item)
    
    def _fill_random(self) -> None:
        """Fill with random values."""
        rows = self.rows_spin.value()
        cols = self.cols_spin.value()
        random_matrix = np.random.randn(rows, cols)
        
        for r in range(rows):
            for c in range(cols):
                item = QTableWidgetItem(f"{random_matrix[r, c]:.4f}")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(r, c, item)
    
    def _on_save(self) -> None:
        """Validate and save the matrix."""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Invalid Name", "Please enter a matrix name.")
            return
        
        matrix = self._get_matrix_from_table()
        if matrix is None:
            return
        
        self._result_name = name
        self._result_matrix = matrix
        self.accept()
    
    def get_result(self) -> tuple[str, Optional[np.ndarray]]:
        """Get the resulting name and matrix."""
        return self._result_name, self._result_matrix
