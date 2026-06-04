"""
PlotWidget: High-resolution interactive 2D geometric coordinate space for visualizing linear algebra.
"""
from typing import Optional, Tuple
import numpy as np

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPointF, Signal, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath

from model.node_data import NodeData, NodeType, OperationType


def draw_arrow(painter: QPainter, start: QPointF, end: QPointF, color: QColor, width: int = 3, arrow_size: float = 12.0):
    """Draw a vector arrow with a colored head."""
    painter.setPen(QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.MiterJoin))
    painter.drawLine(start, end)
    
    # Calculate direction vector
    dx = end.x() - start.x()
    dy = end.y() - start.y()
    length = np.hypot(dx, dy)
    if length < 1e-5:
        return
    
    ux = dx / length
    uy = dy / length
    
    # Arrowhead points
    px = -uy
    py = ux
    
    p1 = end - QPointF(ux * arrow_size, uy * arrow_size) + QPointF(px * arrow_size * 0.5, py * arrow_size * 0.5)
    p2 = end - QPointF(ux * arrow_size, uy * arrow_size) - QPointF(px * arrow_size * 0.5, py * arrow_size * 0.5)
    
    painter.setBrush(QBrush(color))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawPolygon([end, p1, p2])


class GeometricPlotWidget(QWidget):
    """
    High-resolution 2D coordinate space widget.
    Supports zooming, panning, vector dragging, basis vectors dragging, and matrix deformations.
    """
    
    # Signals to notify changes back to MainWindow/Controller
    # (node_id, new_vector_matrix_data)
    dataDragged = Signal(str, object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.node: Optional[NodeData] = None
        self.scale = 50.0  # Pixels per mathematical unit
        self.center_offset = QPointF(0, 0)  # Panning offset in pixels
        
        # Panning state
        self.is_panning = False
        self.pan_start = QPointF()
        
        # Dragging state
        self.dragged_item: Optional[str] = None  # 'vector' or 'basis'
        self.dragged_node_id: Optional[str] = None
        self.dragged_col = -1  # Column index if dragging a matrix basis vector
        
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._initialized_center = False
        
        # Gram-Schmidt Animation setup
        self.gs_timer = QTimer(self)
        self.gs_timer.setInterval(30)  # ~33 FPS
        self.gs_timer.timeout.connect(self._animate_gs)
        self.gs_t = 0.0
    
    def set_node(self, node: Optional[NodeData]) -> None:
        """Set the active node for plotting and refresh rendering."""
        self.node = node
        # Ensure metadata is initialized
        if self.node and not hasattr(self.node, 'metadata'):
            self.node.metadata = {}
        if self.node and 'show_eigen' not in self.node.metadata:
            self.node.metadata['show_eigen'] = True
        if self.node and 'show_det' not in self.node.metadata:
            self.node.metadata['show_det'] = True
            
        # Animation management
        if self.node and self.node.operation == OperationType.GRAM_SCHMIDT:
            if not self.gs_timer.isActive():
                self.gs_t = 0.0
                self.gs_timer.start()
        else:
            if self.gs_timer.isActive():
                self.gs_timer.stop()
            
        self.update()
        
    def _animate_gs(self) -> None:
        """Timer callback to step the Gram-Schmidt animation."""
        self.gs_t += 0.015
        if self.gs_t > 1.0:
            self.gs_t = 0.0  # Loop animation
        self.update()
    
    def to_screen(self, math_pos: QPointF) -> QPointF:
        """Convert mathematical coordinates to screen pixels."""
        x = self.width() / 2.0 + math_pos.x() * self.scale + self.center_offset.x()
        y = self.height() / 2.0 - math_pos.y() * self.scale + self.center_offset.y()
        return QPointF(x, y)
    
    def to_math(self, screen_pos: QPointF) -> QPointF:
        """Convert screen pixels to mathematical coordinates."""
        mx = (screen_pos.x() - self.width() / 2.0 - self.center_offset.x()) / self.scale
        my = (self.height() / 2.0 - screen_pos.y() + self.center_offset.y()) / self.scale
        return QPointF(mx, my)
    
    def paintEvent(self, event) -> None:
        """Draw the grid, axes, and active math vectors/shapes."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background fill
        painter.fillRect(self.rect(), QColor("#F8F9FA"))
        
        # Set up coordinates center_offset on first render
        if not self._initialized_center:
            self.center_offset = QPointF(0, 0)
            self._initialized_center = True
            
        # Draw Cartesian axes and regular grid lines
        self._draw_main_grid(painter)
        
        if self.node is None:
            self._draw_welcome_message(painter)
            return
            
        # Render visual linear algebra geometry
        self._draw_visualization(painter)
    
    def _draw_main_grid(self, painter: QPainter) -> None:
        """Draw a responsive 2D coordinate grid with adaptive tick sizing."""
        grid_color = QColor("#E9ECEF")
        axis_color = QColor("#6C757D")
        
        # Adaptive step based on zoom scale
        if self.scale < 15:
            step = 5.0
        elif self.scale < 35:
            step = 2.0
        elif self.scale > 140:
            step = 0.5
        else:
            step = 1.0
            
        # Find boundaries in math space
        top_left = self.to_math(QPointF(0, 0))
        bottom_right = self.to_math(QPointF(self.width(), self.height()))
        
        x_min = min(top_left.x(), bottom_right.x())
        x_max = max(top_left.x(), bottom_right.x())
        y_min = min(top_left.y(), bottom_right.y())
        y_max = max(top_left.y(), bottom_right.y())
        
        painter.setPen(QPen(grid_color, 1, Qt.PenStyle.SolidLine))
        
        # Draw vertical grid lines
        start_x = np.floor(x_min / step) * step
        end_x = np.ceil(x_max / step) * step
        curr_x = start_x
        while curr_x <= end_x:
            if abs(curr_x) > 1e-5:
                p1 = self.to_screen(QPointF(curr_x, y_min))
                p2 = self.to_screen(QPointF(curr_x, y_max))
                painter.drawLine(p1, p2)
            curr_x += step
            
        # Draw horizontal grid lines
        start_y = np.floor(y_min / step) * step
        end_y = np.ceil(y_max / step) * step
        curr_y = start_y
        while curr_y <= end_y:
            if abs(curr_y) > 1e-5:
                p1 = self.to_screen(QPointF(x_min, curr_y))
                p2 = self.to_screen(QPointF(x_max, curr_y))
                painter.drawLine(p1, p2)
            curr_y += step
            
        # Draw Cartesian axes
        painter.setPen(QPen(axis_color, 2, Qt.PenStyle.SolidLine))
        # Y axis (x = 0)
        py1 = self.to_screen(QPointF(0, y_min))
        py2 = self.to_screen(QPointF(0, y_max))
        painter.drawLine(py1, py2)
        # X axis (y = 0)
        px1 = self.to_screen(QPointF(x_min, 0))
        px2 = self.to_screen(QPointF(x_max, 0))
        painter.drawLine(px1, px2)
        
        # Draw tick labels
        painter.setPen(axis_color)
        painter.setFont(QFont("Segoe UI", 8))
        
        # X axis text values
        curr_x = start_x
        while curr_x <= end_x:
            if abs(curr_x) > 1e-5:
                p = self.to_screen(QPointF(curr_x, 0))
                painter.drawLine(int(p.x()), int(p.y() - 3), int(p.x()), int(p.y() + 3))
                painter.drawText(int(p.x() - 20), int(p.y() + 6), 40, 15, Qt.AlignmentFlag.AlignCenter, f"{curr_x:.3g}")
            curr_x += step
            
        # Y axis text values
        curr_y = start_y
        while curr_y <= end_y:
            if abs(curr_y) > 1e-5:
                p = self.to_screen(QPointF(0, curr_y))
                painter.drawLine(int(p.x() - 3), int(p.y()), int(p.x() + 3), int(p.y()))
                painter.drawText(int(p.x() - 42), int(p.y() - 7), 36, 14, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"{curr_y:.3g}")
            curr_y += step
            
        # Origin marker
        p0 = self.to_screen(QPointF(0, 0))
        painter.drawText(int(p0.x() - 15), int(p0.y() + 4), 10, 12, Qt.AlignmentFlag.AlignRight, "0")
    
    def _draw_welcome_message(self, painter: QPainter) -> None:
        """Render a helpful empty state screen."""
        painter.setPen(QColor("#7F8C8D"))
        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, 
                         "Select a 2D Vector or Matrix node\nto start interactive geometric plotting.")
    
    def _draw_visualization(self, painter: QPainter) -> None:
        """Determine what components to paint based on node state and operations."""
        show_eigen = self.node.metadata.get("show_eigen", True) if self.node else True
        show_det = self.node.metadata.get("show_det", True) if self.node else True
        
        matrix = self.node.matrix
        
        # 1. Directly Visualizable Data (Input Nodes)
        if self.node.is_visualizable and matrix is not None:
            if matrix.shape == (2, 1):
                self._draw_single_vector(painter, matrix, QColor("#1976D2"), self.node.name)
            elif matrix.shape == (2, 2):
                # Render transformation grid
                self._draw_deformed_grid(painter, matrix)
                if show_det:
                    self._draw_determinant_parallelogram(painter, matrix)
                if show_eigen:
                    self._draw_eigenvectors(painter, matrix)
                # Render basis vectors on top
                self._draw_basis_vectors(painter, matrix)
                
        # 2. Selected Operations / Result Node Visualizations
        elif self.node.node_type in (NodeType.OPERATION, NodeType.RESULT):
            op = self.node.operation
            inputs = [self.node.get_input(i) for i in range(self.node.input_count)]
            
            # Vector Addition / Subtraction
            if op in (OperationType.ADD, OperationType.SUBTRACT):
                if len(inputs) >= 2 and inputs[0] is not None and inputs[1] is not None:
                    v1 = inputs[0].matrix
                    v2 = inputs[1].matrix
                    out = self.node.matrix
                    
                    if v1 is not None and v2 is not None and out is not None:
                        if v1.shape == (2, 1) and v2.shape == (2, 1):
                            # Draw inputs
                            self._draw_single_vector(painter, v1, QColor("#1976D2"), inputs[0].name)
                            self._draw_single_vector(painter, v2, QColor("#388E3C"), inputs[1].name)
                            
                            p_v1 = QPointF(float(v1[0, 0]), float(v1[1, 0]))
                            p_v2 = QPointF(float(v2[0, 0]), float(v2[1, 0]))
                            p_out = QPointF(float(out[0, 0]), float(out[1, 0]))
                            
                            # Show parallelogram addition dashes
                            painter.setPen(QPen(QColor("#7F8C8D"), 1.5, Qt.PenStyle.DashLine))
                            if op == OperationType.ADD:
                                painter.drawLine(self.to_screen(p_v1), self.to_screen(p_out))
                                painter.drawLine(self.to_screen(p_v2), self.to_screen(p_out))
                            else:
                                # Subtraction: draws vector pointing from v2 to v1
                                painter.drawLine(self.to_screen(p_v2), self.to_screen(p_v1))
                                
                            # Draw final result
                            self._draw_single_vector(painter, out, QColor("#E67E22"), self.node.name)
                            
            # Scalar multiplication
            elif op == OperationType.MULTIPLY_SCALAR:
                if len(inputs) >= 2 and inputs[0] is not None and inputs[1] is not None:
                    vec = inputs[0].matrix
                    scalar = inputs[1].matrix
                    out = self.node.matrix
                    if vec is not None and scalar is not None and out is not None:
                        if vec.shape == (2, 1) and scalar.size == 1:
                            self._draw_single_vector(painter, vec, QColor("#1976D2"), inputs[0].name)
                            self._draw_single_vector(painter, out, QColor("#E67E22"), self.node.name)
                            
            # Dot Product Projection
            elif op == OperationType.DOT:
                if len(inputs) >= 2 and inputs[0] is not None and inputs[1] is not None:
                    u = inputs[0].matrix
                    v = inputs[1].matrix
                    if u is not None and v is not None and u.shape == (2, 1) and v.shape == (2, 1):
                        self._draw_single_vector(painter, u, QColor("#1976D2"), inputs[0].name)  # u (Blue)
                        self._draw_single_vector(painter, v, QColor("#7F8C8D"), inputs[1].name)  # v (Grey)
                        
                        u_flat = u.flatten()
                        v_flat = v.flatten()
                        v_len_sq = np.dot(v_flat, v_flat)
                        if v_len_sq > 1e-5:
                            proj_f = np.dot(u_flat, v_flat) / v_len_sq
                            proj_vec = proj_f * v_flat
                            
                            p_proj = QPointF(proj_vec[0], proj_vec[1])
                            p_u = QPointF(u_flat[0], u_flat[1])
                            
                            # Draw projection vector
                            self._draw_single_vector(painter, proj_vec.reshape(-1, 1), QColor("#FFD700"), "proj")
                            # Dashed projection drop line
                            painter.setPen(QPen(QColor("#E74C3C"), 1.5, Qt.PenStyle.DashLine))
                            painter.drawLine(self.to_screen(p_u), self.to_screen(p_proj))
                            
            # System Solver Ax = B
            elif op == OperationType.SOLVE:
                if len(inputs) >= 2 and inputs[0] is not None and inputs[1] is not None:
                    A = inputs[0].matrix
                    B = inputs[1].matrix
                    x = self.node.matrix
                    if A is not None and B is not None and x is not None:
                        if A.shape == (2, 2) and B.shape == (2, 1) and x.shape == (2, 1):
                            # Draw deformed grid of mapping A
                            self._draw_deformed_grid(painter, A)
                            self._draw_single_vector(painter, x, QColor("#1976D2"), "x (Sol)")
                            self._draw_single_vector(painter, B, QColor("#FF9800"), "B")
                            
            # Gram-Schmidt orthogonalization animation
            elif op == OperationType.GRAM_SCHMIDT:
                if len(inputs) >= 2 and inputs[0] is not None and inputs[1] is not None:
                    v1 = inputs[0].matrix
                    v2 = inputs[1].matrix
                    if v1 is not None and v2 is not None and v1.shape == (2, 1) and v2.shape == (2, 1):
                        v1_coords = v1.flatten()
                        v2_coords = v2.flatten()
                        
                        u1 = v1_coords.copy()
                        u1_len_sq = np.dot(u1, u1)
                        
                        if u1_len_sq > 1e-5:
                            proj_vec = (np.dot(v2_coords, u1) / u1_len_sq) * u1
                            u2 = v2_coords - proj_vec
                        else:
                            proj_vec = np.zeros(2)
                            u2 = v2_coords.copy()
                            
                        # Animate steps based on self.gs_t (0.0 to 1.0)
                        t = self.gs_t
                        
                        # Draw v1 base vector
                        self._draw_single_vector(painter, v1, QColor("#1976D2"), inputs[0].name)
                        
                        p_v2 = QPointF(v2_coords[0], v2_coords[1])
                        
                        if t < 0.5:
                            # Step 1: Show projection vector fading in
                            alpha = int((t / 0.5) * 180)
                            proj_current = (t / 0.5) * proj_vec
                            
                            self._draw_single_vector(painter, proj_current.reshape(-1, 1), QColor(231, 76, 60, alpha), "proj")
                            
                            # Draw dashed orthogonal drop line
                            painter.setPen(QPen(QColor(127, 140, 141, alpha), 1.5, Qt.PenStyle.DashLine))
                            painter.drawLine(self.to_screen(p_v2), self.to_screen(QPointF(proj_current[0], proj_current[1])))
                            
                            # Draw v2 unchanged
                            self._draw_single_vector(painter, v2, QColor("#388E3C"), inputs[1].name)
                        else:
                            # Step 2: projection vector subtracts, pulling v2 down to orthogonal target u2
                            factor = (t - 0.5) / 0.5
                            v2_current = v2_coords - factor * proj_vec
                            
                            # Draw remaining projection vector fading out
                            alpha = int((1.0 - factor) * 180)
                            self._draw_single_vector(painter, ((1.0 - factor) * proj_vec).reshape(-1, 1), QColor(231, 76, 60, alpha), "proj")
                            
                            # Draw sliding projection line
                            proj_start = v2_coords
                            proj_end = v2_current
                            painter.setPen(QPen(QColor(231, 76, 60, 200), 2, Qt.PenStyle.SolidLine))
                            draw_arrow(painter, self.to_screen(QPointF(proj_start[0], proj_start[1])),
                                       self.to_screen(QPointF(proj_end[0], proj_end[1])), QColor("#E74C3C"), 2)
                            
                            # Draw moving vector v2(t)
                            self._draw_single_vector(painter, v2_current.reshape(-1, 1), QColor("#388E3C"), f"{inputs[1].name}'")
                            
                            # Draw final orthogonal target indicator circle
                            painter.setPen(QPen(QColor("#FFD700"), 1.5, Qt.PenStyle.DashLine))
                            painter.setBrush(Qt.BrushStyle.NoBrush)
                            u2_screen = self.to_screen(QPointF(u2[0], u2[1]))
                            painter.drawEllipse(u2_screen, 6.0, 6.0)
                                
            # Matrix Inverse / Transpose deforms
            elif op in (OperationType.INVERSE, OperationType.TRANSPOSE):
                if len(inputs) >= 1 and inputs[0] is not None:
                    A = inputs[0].matrix
                    out = self.node.matrix
                    if A is not None and out is not None and A.shape == (2, 2) and out.shape == (2, 2):
                        # Draw original grid faint, output grid thick
                        self._draw_deformed_grid(painter, A, alpha=40)
                        self._draw_deformed_grid(painter, out)
                        self._draw_basis_vectors(painter, out)
                        
            # Output result node (simply renders output data if visualizable)
            elif op == OperationType.RESULT:
                if matrix is not None:
                    if matrix.shape == (2, 1):
                        self._draw_single_vector(painter, matrix, QColor("#FFD700"), "Result")
                    elif matrix.shape == (2, 2):
                        self._draw_deformed_grid(painter, matrix)
                        if show_det:
                            self._draw_determinant_parallelogram(painter, matrix)
                        if show_eigen:
                            self._draw_eigenvectors(painter, matrix)
                        self._draw_basis_vectors(painter, matrix)
    
    def _draw_single_vector(self, painter: QPainter, vec: np.ndarray, color: QColor, label: str) -> None:
        """Render a single vector arrow with coordinate tip dragging handle."""
        vx = float(vec[0, 0])
        vy = float(vec[1, 0] if vec.size > 1 else 0)
        
        origin_screen = self.to_screen(QPointF(0, 0))
        tip_screen = self.to_screen(QPointF(vx, vy))
        
        draw_arrow(painter, origin_screen, tip_screen, color, 3)
        
        # Dragging handle overlay
        painter.setPen(QPen(color.darker(125), 1.5))
        painter.setBrush(QBrush(QColor(255, 255, 255, 220)))
        painter.drawEllipse(tip_screen, 5.0, 5.0)
        
        # Label rendering
        painter.setPen(color.darker(140))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.drawText(int(tip_screen.x() + 8), int(tip_screen.y() - 6), label)
        
    def _draw_basis_vectors(self, painter: QPainter, matrix: np.ndarray) -> None:
        """Render the columns of a transformation matrix as coordinate basis vectors."""
        i_hat = np.array([[matrix[0, 0]], [matrix[1, 0]]])
        j_hat = np.array([[matrix[0, 1]], [matrix[1, 1]]])
        
        # Green for i_hat, Red for j_hat
        self._draw_single_vector(painter, i_hat, QColor("#2ECC71"), "i_hat")
        self._draw_single_vector(painter, j_hat, QColor("#E74C3C"), "j_hat")
        
    def _draw_deformed_grid(self, painter: QPainter, matrix: np.ndarray, alpha: int = 90) -> None:
        """Deform coordinate space by painting grid lines mapped under a linear transformation."""
        grid_color = QColor(120, 144, 156, alpha)
        painter.setPen(QPen(grid_color, 1, Qt.PenStyle.SolidLine))
        
        bounds = 10
        step = 1.0
        
        # Draw vertical lines transformed
        for x in np.arange(-bounds, bounds + step, step):
            p1 = QPointF(x, -bounds)
            p2 = QPointF(x, bounds)
            
            p1_trans = QPointF(
                matrix[0, 0] * p1.x() + matrix[0, 1] * p1.y(),
                matrix[1, 0] * p1.x() + matrix[1, 1] * p1.y()
            )
            p2_trans = QPointF(
                matrix[0, 0] * p2.x() + matrix[0, 1] * p2.y(),
                matrix[1, 0] * p2.x() + matrix[1, 1] * p2.y()
            )
            painter.drawLine(self.to_screen(p1_trans), self.to_screen(p2_trans))
            
        # Draw horizontal lines transformed
        for y in np.arange(-bounds, bounds + step, step):
            p1 = QPointF(-bounds, y)
            p2 = QPointF(bounds, y)
            
            p1_trans = QPointF(
                matrix[0, 0] * p1.x() + matrix[0, 1] * p1.y(),
                matrix[1, 0] * p1.x() + matrix[1, 1] * p1.y()
            )
            p2_trans = QPointF(
                matrix[0, 0] * p2.x() + matrix[0, 1] * p2.y(),
                matrix[1, 0] * p2.x() + matrix[1, 1] * p2.y()
            )
            painter.drawLine(self.to_screen(p1_trans), self.to_screen(p2_trans))
            
    def _draw_determinant_parallelogram(self, painter: QPainter, matrix: np.ndarray) -> None:
        """Plot the transformed unit square area shaded as a parallelogram."""
        p0 = QPointF(0, 0)
        p1 = QPointF(float(matrix[0, 0]), float(matrix[1, 0]))
        p2 = QPointF(float(matrix[0, 0] + matrix[0, 1]), float(matrix[1, 0] + matrix[1, 1]))
        p3 = QPointF(float(matrix[0, 1]), float(matrix[1, 1]))
        
        s0, s1, s2, s3 = self.to_screen(p0), self.to_screen(p1), self.to_screen(p2), self.to_screen(p3)
        
        # Transparent Gold fill
        painter.setBrush(QBrush(QColor(241, 196, 15, 35)))
        painter.setPen(QPen(QColor(243, 156, 18, 90), 1.5, Qt.PenStyle.DashLine))
        painter.drawPolygon([s0, s1, s2, s3])
        
        # Draw Area label text
        det_val = np.linalg.det(matrix)
        center = (s0 + s2) / 2.0
        painter.setPen(QColor("#D68910"))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.drawText(int(center.x() - 60), int(center.y() - 10), 120, 20, 
                         Qt.AlignmentFlag.AlignCenter, f"Area = {abs(det_val):.3g}")
        
    def _draw_eigenvectors(self, painter: QPainter, matrix: np.ndarray) -> None:
        """Calculate and paint real eigenvector span lines and the deformed unit circle."""
        try:
            if not np.all(np.isfinite(matrix)):
                return
                
            # Draw deformed unit circle (deformed to an ellipse)
            painter.setPen(QPen(QColor(155, 89, 182, 110), 2, Qt.PenStyle.SolidLine))
            path = QPainterPath()
            steps = 72
            for i in range(steps + 1):
                theta = i * 2 * np.pi / steps
                pt = QPointF(np.cos(theta), np.sin(theta))
                # Transform by matrix
                t_pt = QPointF(
                    matrix[0, 0] * pt.x() + matrix[0, 1] * pt.y(),
                    matrix[1, 0] * pt.x() + matrix[1, 1] * pt.y()
                )
                scr_pt = self.to_screen(t_pt)
                if i == 0:
                    path.moveTo(scr_pt)
                else:
                    path.lineTo(scr_pt)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)
            
            # Draw real eigenvectors span lines
            vals, vecs = np.linalg.eig(matrix)
            for i in range(len(vals)):
                if np.isreal(vals[i]) and np.all(np.isreal(vecs[:, i])):
                    val = float(vals[i].real)
                    vec = vecs[:, i].real
                    
                    vx, vy = vec[0], vec[1]
                    if np.hypot(vx, vy) < 1e-4:
                        continue
                        
                    # Calculate infinite endpoints
                    p1 = self.to_screen(QPointF(vx * -50, vy * -50))
                    p2 = self.to_screen(QPointF(vx * 50, vy * 50))
                    
                    # Purple span lines
                    painter.setPen(QPen(QColor(142, 68, 173, 140), 1.5, Qt.PenStyle.DashDotLine))
                    painter.drawLine(p1, p2)
                    
                    # Span label
                    p_lbl = self.to_screen(QPointF(vx * 3.5, vy * 3.5))
                    painter.setPen(QColor(125, 60, 152))
                    painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                    painter.drawText(int(p_lbl.x() + 4), int(p_lbl.y() - 4), f"λ={val:.3g}")
        except Exception:
            pass

    def mousePressEvent(self, event) -> None:
        """Handle clicking coordinates for dragging handles or initiating canvas panning."""
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            if self.node is None:
                return
                
            # Check selected node handles
            if self.node.is_visualizable and self.node.matrix is not None:
                matrix = self.node.matrix
                if matrix.shape == (2, 1):
                    tip = self.to_screen(QPointF(float(matrix[0, 0]), float(matrix[1, 0])))
                    if (pos - tip).manhattanLength() < 12:
                        self.dragged_item = 'vector'
                        self.dragged_node_id = self.node.id
                        self.setCursor(Qt.CursorShape.ClosedHandCursor)
                        return
                elif matrix.shape == (2, 2):
                    i_tip = self.to_screen(QPointF(float(matrix[0, 0]), float(matrix[1, 0])))
                    j_tip = self.to_screen(QPointF(float(matrix[0, 1]), float(matrix[1, 1])))
                    if (pos - i_tip).manhattanLength() < 12:
                        self.dragged_item = 'basis'
                        self.dragged_node_id = self.node.id
                        self.dragged_col = 0
                        self.setCursor(Qt.CursorShape.ClosedHandCursor)
                        return
                    if (pos - j_tip).manhattanLength() < 12:
                        self.dragged_item = 'basis'
                        self.dragged_node_id = self.node.id
                        self.dragged_col = 1
                        self.setCursor(Qt.CursorShape.ClosedHandCursor)
                        return
                        
            # Check operation input handles (allows dragging parent variables when operation is selected)
            if self.node.node_type in (NodeType.OPERATION, NodeType.RESULT):
                inputs = [self.node.get_input(i) for i in range(self.node.input_count)]
                for idx, inp in enumerate(inputs):
                    if inp and inp.is_visualizable and inp.matrix is not None and inp.matrix.shape == (2, 1):
                        tip = self.to_screen(QPointF(float(inp.matrix[0, 0]), float(inp.matrix[1, 0])))
                        if (pos - tip).manhattanLength() < 12:
                            self.dragged_item = 'vector'
                            self.dragged_node_id = inp.id
                            self.setCursor(Qt.CursorShape.ClosedHandCursor)
                            return
            
            # Fall back to panning
            self.is_panning = True
            self.pan_start = pos
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            
        elif event.button() == Qt.MouseButton.RightButton:
            self.is_panning = True
            self.pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event) -> None:
        """Track mouse movement to update pan offsets or mathematical coordinates."""
        pos = event.position()
        
        # Panning logic
        if self.is_panning:
            delta = pos - self.pan_start
            self.center_offset += delta
            self.pan_start = pos
            self.update()
            return
            
        # Dragging vector logic
        if self.dragged_item:
            math_pos = self.to_math(pos)
            
            # Smart coordinate rounding/snapping
            val_x = round(math_pos.x(), 1)
            val_y = round(math_pos.y(), 1)
            
            # Snap to integer if closer than 0.05
            if abs(val_x - round(val_x)) < 0.05:
                val_x = float(round(val_x))
            if abs(val_y - round(val_y)) < 0.05:
                val_y = float(round(val_y))
                
            new_data = np.array([[val_x], [val_y]])
            
            if self.dragged_item == 'vector':
                self.dataDragged.emit(self.dragged_node_id, new_data)
            elif self.dragged_item == 'basis':
                # Reconstruct matrix column by column
                current_matrix = self.node.matrix.copy() if self.node.matrix is not None else np.eye(2)
                current_matrix[:, self.dragged_col] = new_data.flatten()
                self.dataDragged.emit(self.dragged_node_id, current_matrix)
                
            self.update()
            return
            
        # Cursor styling on hover over handles
        if self.node:
            hovering = False
            if self.node.is_visualizable and self.node.matrix is not None:
                matrix = self.node.matrix
                if matrix.shape == (2, 1):
                    tip = self.to_screen(QPointF(float(matrix[0, 0]), float(matrix[1, 0])))
                    if (pos - tip).manhattanLength() < 12:
                        hovering = True
                elif matrix.shape == (2, 2):
                    i_tip = self.to_screen(QPointF(float(matrix[0, 0]), float(matrix[1, 0])))
                    j_tip = self.to_screen(QPointF(float(matrix[0, 1]), float(matrix[1, 1])))
                    if (pos - i_tip).manhattanLength() < 12 or (pos - j_tip).manhattanLength() < 12:
                        hovering = True
                        
            if self.node.node_type in (NodeType.OPERATION, NodeType.RESULT):
                inputs = [self.node.get_input(i) for i in range(self.node.input_count)]
                for inp in inputs:
                    if inp and inp.is_visualizable and inp.matrix is not None and inp.matrix.shape == (2, 1):
                        tip = self.to_screen(QPointF(float(inp.matrix[0, 0]), float(inp.matrix[1, 0])))
                        if (pos - tip).manhattanLength() < 12:
                            hovering = True
                            
            if hovering:
                self.setCursor(Qt.CursorShape.PointingHandCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event) -> None:
        """Reset panning and dragging indicators."""
        self.dragged_item = None
        self.dragged_node_id = None
        self.dragged_col = -1
        self.is_panning = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    def wheelEvent(self, event) -> None:
        """Zoom scene relative to scroll position."""
        factor = 1.15
        if event.angleDelta().y() < 0:
            factor = 1.0 / factor
            
        mouse_screen = event.position()
        mouse_math = self.to_math(mouse_screen)
        
        self.scale = max(5.0, min(self.scale * factor, 600.0))
        
        mouse_screen_after = self.to_screen(mouse_math)
        delta = mouse_screen - mouse_screen_after
        self.center_offset += delta
        
        self.update()
