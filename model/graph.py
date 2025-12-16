"""
Graph: Directed Acyclic Graph for managing node dependencies and propagation.
"""
from typing import Dict, List, Set, Optional
from collections import deque
import numpy as np

from .node_data import NodeData, NodeType, OperationType


class Graph:
    """
    Manages the computation graph as a DAG.
    Handles node registration, connection validation, and update propagation.
    """
    
    def __init__(self):
        self.nodes: Dict[str, NodeData] = {}  # id -> NodeData
        self.edges: Dict[str, List[str]] = {}  # source_id -> [target_ids]
        self.reverse_edges: Dict[str, List[str]] = {}  # target_id -> [source_ids]
    
    def add_node(self, node: NodeData) -> None:
        """Add a node to the graph."""
        self.nodes[node.id] = node
        self.edges[node.id] = []
        self.reverse_edges[node.id] = []
    
    def remove_node(self, node_id: str) -> None:
        """Remove a node and all its connections."""
        if node_id not in self.nodes:
            return
        
        # Remove all edges to/from this node
        for target_id in self.edges.get(node_id, []):
            if target_id in self.reverse_edges:
                self.reverse_edges[target_id] = [
                    src for src in self.reverse_edges[target_id] if src != node_id
                ]
        
        for source_id in self.reverse_edges.get(node_id, []):
            if source_id in self.edges:
                self.edges[source_id] = [
                    tgt for tgt in self.edges[source_id] if tgt != node_id
                ]
        
        del self.nodes[node_id]
        del self.edges[node_id]
        del self.reverse_edges[node_id]
    
    def connect(self, source_id: str, target_id: str, input_index: int) -> bool:
        """
        Connect source node's output to target node's input at given index.
        Returns False if connection would create a cycle.
        """
        if source_id not in self.nodes or target_id not in self.nodes:
            return False
        
        # Check for cycle
        if self._would_create_cycle(source_id, target_id):
            return False
        
        # Add edge
        if target_id not in self.edges[source_id]:
            self.edges[source_id].append(target_id)
        if source_id not in self.reverse_edges[target_id]:
            self.reverse_edges[target_id].append(source_id)
        
        # Update node input
        target_node = self.nodes[target_id]
        source_node = self.nodes[source_id]
        target_node.set_input(input_index, source_node)
        
        return True
    
    def disconnect(self, source_id: str, target_id: str, input_index: int) -> None:
        """Disconnect source from target's input."""
        if source_id in self.edges and target_id in self.edges[source_id]:
            self.edges[source_id].remove(target_id)
        if target_id in self.reverse_edges and source_id in self.reverse_edges[target_id]:
            self.reverse_edges[target_id].remove(source_id)
        
        if target_id in self.nodes:
            self.nodes[target_id].set_input(input_index, None)
    
    def _would_create_cycle(self, source_id: str, target_id: str) -> bool:
        """Check if adding source->target edge would create a cycle."""
        # If target can reach source, adding source->target creates a cycle
        visited: Set[str] = set()
        queue = deque([target_id])
        
        while queue:
            current = queue.popleft()
            if current == source_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            queue.extend(self.edges.get(current, []))
        
        return False
    
    def get_downstream_nodes(self, node_id: str) -> List[str]:
        """Get all nodes downstream of the given node in topological order."""
        if node_id not in self.nodes:
            return []
        
        downstream: List[str] = []
        visited: Set[str] = set()
        queue = deque(self.edges.get(node_id, []))
        
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            downstream.append(current)
            queue.extend(self.edges.get(current, []))
        
        return downstream
    
    def propagate_from(self, node_id: str) -> None:
        """Recompute all nodes downstream of the given node."""
        downstream = self.get_downstream_nodes(node_id)
        
        for nid in downstream:
            node = self.nodes[nid]
            self._compute_node(node)
    
    def _compute_node(self, node: NodeData) -> None:
        """Compute the result for an operation node."""
        if node.node_type == NodeType.DATA:
            # Data nodes don't compute, they just hold input
            return
        
        # Gather inputs
        inputs = [node.get_input(i) for i in range(node.input_count)]
        
        # Check if all required inputs are connected and have data
        matrices = []
        for inp in inputs:
            if inp is None:
                node.error_state = "Missing input"
                node.matrix = None
                node.notify_change()
                return
            if inp.matrix is None:
                node.error_state = "Input has no data"
                node.matrix = None
                node.notify_change()
                return
            if inp.error_state:
                node.error_state = "Input has error"
                node.matrix = None
                node.notify_change()
                return
            matrices.append(inp.matrix)
        
        # Perform the operation
        try:
            result = self._execute_operation(node.operation, matrices)
            node.matrix = result
            node.error_state = None
        except np.linalg.LinAlgError as e:
            node.error_state = f"LinAlg Error: {e}"
            node.matrix = None
        except ValueError as e:
            node.error_state = f"Value Error: {e}"
            node.matrix = None
        except Exception as e:
            node.error_state = f"Error: {e}"
            node.matrix = None
        
        node.notify_change()
    
    def _execute_operation(self, op: OperationType, matrices: List[np.ndarray]) -> np.ndarray:
        """Execute a matrix operation."""
        if op == OperationType.RESULT:
            return matrices[0].copy()
        
        # Binary operations
        if op == OperationType.ADD:
            return np.add(matrices[0], matrices[1])
        elif op == OperationType.SUBTRACT:
            return np.subtract(matrices[0], matrices[1])
        elif op == OperationType.MULTIPLY_SCALAR:
            return np.multiply(matrices[0], matrices[1])
        elif op == OperationType.MULTIPLY_ELEMENTWISE:
            return np.multiply(matrices[0], matrices[1])
        elif op == OperationType.DIVIDE_ELEMENTWISE:
            return np.divide(matrices[0], matrices[1])
        elif op == OperationType.DOT:
            return np.dot(matrices[0], matrices[1])
        elif op == OperationType.CROSS:
            return np.cross(matrices[0], matrices[1])
        elif op == OperationType.SOLVE:
            return np.linalg.solve(matrices[0], matrices[1])
        
        # Unary operations
        elif op == OperationType.TRANSPOSE:
            return matrices[0].T
        elif op == OperationType.DETERMINANT:
            return np.array([[np.linalg.det(matrices[0])]])
        elif op == OperationType.TRACE:
            return np.array([[np.trace(matrices[0])]])
        elif op == OperationType.RANK:
            return np.array([[np.linalg.matrix_rank(matrices[0])]])
        elif op == OperationType.INVERSE:
            return np.linalg.inv(matrices[0])
        elif op == OperationType.PSEUDO_INVERSE:
            return np.linalg.pinv(matrices[0])
        elif op == OperationType.EIGENVALUES:
            eigenvalues, _ = np.linalg.eig(matrices[0])
            return eigenvalues.reshape(-1, 1)
        elif op == OperationType.EIGENVECTORS:
            _, eigenvectors = np.linalg.eig(matrices[0])
            return eigenvectors
        elif op == OperationType.SVD:
            # Return singular values as column vector
            _, s, _ = np.linalg.svd(matrices[0])
            return s.reshape(-1, 1)
        
        raise ValueError(f"Unknown operation: {op}")
