"""
NodeData: Core data structure for nodes in the computation graph.
"""
import uuid
from enum import Enum
from typing import Optional, List, Callable
import numpy as np


class NodeType(Enum):
    """Types of nodes in the graph."""
    DATA = "data"           # Matrix input node
    OPERATION = "operation" # Math operation node
    RESULT = "result"       # Terminal result display node


class OperationType(Enum):
    """All supported matrix operations."""
    # Special types
    NONE = "none"           # For DATA nodes
    RESULT = "result"       # For RESULT nodes
    
    # Basic Arithmetic (2 inputs)
    ADD = "add"
    SUBTRACT = "subtract"
    MULTIPLY_SCALAR = "scalar_multiply"
    MULTIPLY_ELEMENTWISE = "elementwise_multiply"
    DIVIDE_ELEMENTWISE = "elementwise_divide"
    
    # Linear Algebra (2 inputs)
    DOT = "dot"
    CROSS = "cross"
    SOLVE = "solve"  # Ax = B solver
    
    # Single Input Operations
    TRANSPOSE = "transpose"
    DETERMINANT = "determinant"
    TRACE = "trace"
    RANK = "rank"
    INVERSE = "inverse"
    PSEUDO_INVERSE = "pseudo_inverse"
    EIGENVALUES = "eigenvalues"
    EIGENVECTORS = "eigenvectors"
    SVD = "svd"


# Define input counts for each operation
OPERATION_INPUTS = {
    OperationType.NONE: 0,
    OperationType.RESULT: 1,
    OperationType.ADD: 2,
    OperationType.SUBTRACT: 2,
    OperationType.MULTIPLY_SCALAR: 2,
    OperationType.MULTIPLY_ELEMENTWISE: 2,
    OperationType.DIVIDE_ELEMENTWISE: 2,
    OperationType.DOT: 2,
    OperationType.CROSS: 2,
    OperationType.SOLVE: 2,
    OperationType.TRANSPOSE: 1,
    OperationType.DETERMINANT: 1,
    OperationType.TRACE: 1,
    OperationType.RANK: 1,
    OperationType.INVERSE: 1,
    OperationType.PSEUDO_INVERSE: 1,
    OperationType.EIGENVALUES: 1,
    OperationType.EIGENVECTORS: 1,
    OperationType.SVD: 1,
}


class NodeData:
    """
    Represents data for a single node in the computation graph.
    Stores matrix data, operation type, and error state.
    """
    
    def __init__(
        self,
        name: str,
        node_type: NodeType,
        operation: OperationType = OperationType.NONE,
        matrix: Optional[np.ndarray] = None
    ):
        self.id = str(uuid.uuid4())
        self.name = name
        self.node_type = node_type
        self.operation = operation
        self.matrix = matrix  # The actual data or computed result
        self.error_state: Optional[str] = None
        self._inputs: List[Optional['NodeData']] = [None] * OPERATION_INPUTS.get(operation, 0)
        self._on_change_callbacks: List[Callable] = []
    
    @property
    def input_count(self) -> int:
        """Number of inputs this node expects."""
        return OPERATION_INPUTS.get(self.operation, 0)
    
    @property
    def shape_str(self) -> str:
        """Human-readable shape string."""
        if self.matrix is None:
            return "No Data"
        if self.matrix.ndim == 0:
            return "Scalar"
        return f"{self.matrix.shape[0]}x{self.matrix.shape[1] if self.matrix.ndim > 1 else 1}"
    
    def set_input(self, index: int, source: Optional['NodeData']) -> None:
        """Set an input connection."""
        if 0 <= index < len(self._inputs):
            self._inputs[index] = source
    
    def get_input(self, index: int) -> Optional['NodeData']:
        """Get input at index."""
        if 0 <= index < len(self._inputs):
            return self._inputs[index]
        return None
    
    def clear_inputs(self) -> None:
        """Clear all input connections."""
        self._inputs = [None] * self.input_count
    
    def add_change_callback(self, callback: Callable) -> None:
        """Register a callback for when data changes."""
        if callback not in self._on_change_callbacks:
            self._on_change_callbacks.append(callback)
    
    def remove_change_callback(self, callback: Callable) -> None:
        """Remove a change callback."""
        if callback in self._on_change_callbacks:
            self._on_change_callbacks.remove(callback)
    
    def notify_change(self) -> None:
        """Notify all listeners that data has changed."""
        for callback in self._on_change_callbacks:
            callback(self)
    
    def __repr__(self) -> str:
        return f"NodeData(name='{self.name}', type={self.node_type.value}, op={self.operation.value})"
