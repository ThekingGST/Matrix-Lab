# Matrix Lab - Node Documentation

This document explains how to use each node type in Matrix Lab.

---

## Data Nodes

### Matrix (Data Node)
**Purpose:** Holds matrix data that can be used as input to operations.

**Creating a Matrix:**
1. Click `+ New Matrix` in the sidebar
2. Set the name, rows, and columns
3. Enter values in the grid or use Quick Fill (Identity, Zeros, Random)
4. Click Save

**Editing:** Double-click the matrix in the Variables panel.

**Using:** Drag the matrix from the sidebar onto the canvas, then connect its output socket to operation inputs.

---

## Arithmetic Operations

### Add (+)
**Purpose:** Adds two matrices element-wise.

**Inputs:**
- Input 1: Matrix A (any shape)
- Input 2: Matrix B (must match shape of A)

**Output:** Matrix with same shape as inputs, where each element is A[i,j] + B[i,j]

**Connection:**
```
[Matrix A] ──► [Add (+)] ──► [Result]
[Matrix B] ──►
```

---

### Subtract (-)
**Purpose:** Subtracts second matrix from first, element-wise.

**Inputs:**
- Input 1: Matrix A
- Input 2: Matrix B (must match shape of A)

**Output:** Matrix where each element is A[i,j] - B[i,j]

---

### Scalar Multiply
**Purpose:** Multiplies all elements of a matrix by a scalar value.

**Inputs:**
- Input 1: Matrix
- Input 2: Scalar (1x1 matrix)

**Output:** Matrix with all elements multiplied by the scalar.

---

### Element Multiply
**Purpose:** Multiplies two matrices element-wise (Hadamard product).

**Inputs:**
- Input 1: Matrix A
- Input 2: Matrix B (must match shape of A)

**Output:** Matrix where each element is A[i,j] × B[i,j]

---

### Element Divide
**Purpose:** Divides first matrix by second, element-wise.

**Inputs:**
- Input 1: Matrix A
- Input 2: Matrix B (must match shape of A)

**Output:** Matrix where each element is A[i,j] ÷ B[i,j]

**Note:** Division by zero will cause an error.

---

## Linear Algebra Operations

### Dot Product (@)
**Purpose:** Performs matrix multiplication.

**Inputs:**
- Input 1: Matrix A (m × n)
- Input 2: Matrix B (n × p)

**Output:** Matrix (m × p), the matrix product A @ B

**Requirement:** Number of columns in A must equal number of rows in B.

---

### Cross Product
**Purpose:** Computes cross product of two 3-element vectors.

**Inputs:**
- Input 1: Vector A (3 elements)
- Input 2: Vector B (3 elements)

**Output:** Vector (3 elements) perpendicular to both inputs.

---

### Transpose
**Purpose:** Swaps rows and columns of a matrix.

**Inputs:**
- Input 1: Matrix (m × n)

**Output:** Matrix (n × m)

---

### Inverse
**Purpose:** Computes the multiplicative inverse of a square matrix.

**Inputs:**
- Input 1: Square matrix (n × n)

**Output:** Inverse matrix where A @ A⁻¹ = Identity

**Note:** Matrix must be invertible (non-singular). Otherwise, an error occurs.

---

### Pseudo-Inverse
**Purpose:** Computes the Moore-Penrose pseudo-inverse.

**Inputs:**
- Input 1: Any matrix (m × n)

**Output:** Pseudo-inverse matrix

**Use:** Works for any matrix, even non-square or singular matrices.

---

## Properties

### Determinant
**Purpose:** Computes the determinant of a square matrix.

**Inputs:**
- Input 1: Square matrix (n × n)

**Output:** Scalar value (1×1 matrix)

---

### Trace
**Purpose:** Computes the sum of diagonal elements.

**Inputs:**
- Input 1: Square matrix (n × n)

**Output:** Scalar value (1×1 matrix)

---

### Rank
**Purpose:** Computes the rank (number of linearly independent rows/columns).

**Inputs:**
- Input 1: Any matrix

**Output:** Scalar value (1×1 matrix)

---

## Decompositions

### Eigenvalues
**Purpose:** Computes the eigenvalues of a square matrix.

**Inputs:**
- Input 1: Square matrix (n × n)

**Output:** Array of eigenvalues

---

### Eigenvectors
**Purpose:** Computes the eigenvectors of a square matrix.

**Inputs:**
- Input 1: Square matrix (n × n)

**Output:** Matrix where each column is an eigenvector

---

### SVD (Singular Values)
**Purpose:** Performs Singular Value Decomposition, returning singular values.

**Inputs:**
- Input 1: Any matrix

**Output:** Array of singular values (sorted descending)

---

## Solvers

### Solve (Ax=B)
**Purpose:** Solves the linear system Ax = B for x.

**Inputs:**
- Input 1: Coefficient matrix A (n × n)
- Input 2: Right-hand side vector/matrix B

**Output:** Solution x such that Ax = B

**Example Use Case:**
To solve the system:
```
2x + y = 5
x + 3y = 7
```

1. Create matrix A: `[[2, 1], [1, 3]]`
2. Create matrix B: `[[5], [7]]`
3. Connect both to Solve node
4. Result is x: `[[1.6], [1.8]]`

---

## Output

### Result Display
**Purpose:** Displays the final computed result with the option to save as a variable.

**Inputs:**
- Input 1: Any matrix from a computation

**Output:** Shows the matrix in the Inspector panel.

**Special Feature:** When a Result node is selected, click `Add as Variable` in the Inspector to save the result as a new matrix variable.

---

## General Tips

1. **Connect nodes** by dragging from an output socket (right side) to an input socket (left side)
2. **View results** by clicking on any node - the Inspector panel shows the matrix values
3. **Delete nodes** by selecting them and pressing the Delete key
4. **Pan the canvas** by right-click dragging
5. **Zoom** with the scroll wheel
6. **Error states** are shown in red - hover over the node or check the Inspector for details
