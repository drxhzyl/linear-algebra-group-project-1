"""Small, exact matrix calculator and GameTrix objective checks.

All operations return new matrices and use Fraction arithmetic. In vector_op,
A is the target matrix and B supplies the source row or column.
"""

from fractions import Fraction


def _scalar(value):
    if isinstance(value, bool) or not isinstance(value, (int, str, Fraction)):
        raise ValueError("Entries must be integers or rational strings")
    try:
        return Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError("Invalid rational number") from exc


def matrix(value):
    """Parse a nonempty rectangular nested list of integers/rational strings."""
    if not isinstance(value, list) or not value:
        raise ValueError("A matrix must be a nonempty nested list")
    if any(not isinstance(row, list) or not row for row in value):
        raise ValueError("A matrix must have nonempty list rows")
    n = len(value[0])
    if any(len(row) != n for row in value):
        raise ValueError("Matrix rows must have the same length")
    if any(isinstance(x, Fraction) for row in value for x in row):
        raise ValueError("Input entries must be integers or rational strings")
    return [[_scalar(x) for x in row] for row in value]


def shape(A):
    return len(A), len(A[0])


def dump(A):
    return [[x.numerator if x.denominator == 1 else str(x) for x in row]
            for row in A]


def _copy(A):
    return [row[:] for row in A]


def _same_shape(A, B):
    if shape(A) != shape(B):
        raise ValueError("Matrices must have the same shape")


def add(A, B):
    _same_shape(A, B)
    return [[a + b for a, b in zip(ar, br)] for ar, br in zip(A, B)]


def sub(A, B):
    _same_shape(A, B)
    return [[a - b for a, b in zip(ar, br)] for ar, br in zip(A, B)]


def mul(A, B):
    m, n = shape(A)
    p, q = shape(B)
    if n != p:
        raise ValueError("Inner matrix dimensions must match")
    return [[sum((A[i][k] * B[k][j] for k in range(n)), Fraction(0))
             for j in range(q)] for i in range(m)]


def transpose(A):
    return [list(column) for column in zip(*A)]


def scale(A, c):
    c = _scalar(c)
    return [[x * c for x in row] for row in A]


def shift(A, c):
    """Add c to every entry, including off-diagonal entries."""
    c = _scalar(c)
    return [[x + c for x in row] for row in A]


def identity(n):
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError("Identity size must be a positive integer")
    return [[Fraction(i == j) for j in range(n)] for i in range(n)]


def _square(A):
    m, n = shape(A)
    if m != n:
        raise ValueError("Operation requires a square matrix")
    return n


def det(A):
    n = _square(A)
    U = _copy(A)
    result = Fraction(1)
    for j in range(n):
        pivot_row = next((i for i in range(j, n) if U[i][j]), None)
        if pivot_row is None:
            return Fraction(0)
        if pivot_row != j:
            U[j], U[pivot_row] = U[pivot_row], U[j]
            result = -result
        pivot = U[j][j]
        result *= pivot
        for i in range(j + 1, n):
            factor = U[i][j] / pivot
            for k in range(j + 1, n):
                U[i][k] -= factor * U[j][k]
    return result


def rank(A):
    m, n = shape(A)
    U = _copy(A)
    r = 0
    for j in range(n):
        pivot_row = next((i for i in range(r, m) if U[i][j]), None)
        if pivot_row is None:
            continue
        U[r], U[pivot_row] = U[pivot_row], U[r]
        for i in range(r + 1, m):
            factor = U[i][j] / U[r][j]
            for k in range(j, n):
                U[i][k] -= factor * U[r][k]
        r += 1
        if r == m:
            break
    return r


def inverse(A):
    n = _square(A)
    U, V = _copy(A), identity(n)
    for j in range(n):
        pivot_row = next((i for i in range(j, n) if U[i][j]), None)
        if pivot_row is None:
            raise ValueError("Singular matrix has no inverse")
        U[j], U[pivot_row] = U[pivot_row], U[j]
        V[j], V[pivot_row] = V[pivot_row], V[j]
        pivot = U[j][j]
        U[j] = [x / pivot for x in U[j]]
        V[j] = [x / pivot for x in V[j]]
        for i in range(n):
            if i == j:
                continue
            factor = U[i][j]
            U[i] = [a - factor * b for a, b in zip(U[i], U[j])]
            V[i] = [a - factor * b for a, b in zip(V[i], V[j])]
    return V


def lu(A):
    """Doolittle LU without pivoting; only the final pivot may be zero."""
    n = _square(A)
    L, U = identity(n), _copy(A)
    for j in range(n - 1):
        if not U[j][j]:
            raise ValueError("LU without row swaps requires nonzero earlier pivots")
        for i in range(j + 1, n):
            L[i][j] = U[i][j] / U[j][j]
            for k in range(j, n):
                U[i][k] -= L[i][j] * U[j][k]
    return L, U


def _index(i, size):
    if isinstance(i, bool) or not isinstance(i, int) or not 0 <= i < size:
        raise ValueError("Vector index is out of range")


def _axis(axis):
    if axis not in ("row", "column"):
        raise ValueError("Axis must be 'row' or 'column'")


def _unit_delta(delta):
    if isinstance(delta, bool) or not isinstance(delta, int) or delta not in (-1, 1):
        raise ValueError("Delta must be the integer -1 or 1")


def entry_tweak(A, i, j, delta=1):
    """Add exactly +1 or -1 to one entry, using zero-based row/column indices."""
    m, n = shape(A)
    _index(i, m)
    _index(j, n)
    _unit_delta(delta)
    result = _copy(A)
    result[i][j] += delta
    return result


def entry_zero(A, i, j):
    """Set one entry to exact zero, using zero-based row/column indices."""
    m, n = shape(A)
    _index(i, m)
    _index(j, n)
    result = _copy(A)
    result[i][j] = Fraction(0)
    return result


def combine_vectors(A, axis, source_index, target_index, delta=1):
    """Add +/- an existing row or column to a distinct vector in the same A."""
    _axis(axis)
    _unit_delta(delta)
    vectors = _copy(A) if axis == "row" else transpose(A)
    _index(source_index, len(vectors))
    _index(target_index, len(vectors))
    if source_index == target_index:
        raise ValueError("Combining requires distinct source and target rows or columns")
    vectors[target_index] = [a + delta * b for a, b in
                             zip(vectors[target_index], vectors[source_index])]
    return vectors if axis == "row" else transpose(vectors)


def swap(A, axis, i, j):
    _axis(axis)
    vectors = _copy(A) if axis == "row" else transpose(A)
    _index(i, len(vectors))
    _index(j, len(vectors))
    if i == j:
        raise ValueError("Interchange requires two distinct rows or columns")
    vectors[i], vectors[j] = vectors[j], vectors[i]
    return vectors if axis == "row" else transpose(vectors)


def vector_op(A, B, axis, source_index, target_index, mode):
    """Add/replace a target vector in A, or append a source vector from B."""
    _axis(axis)
    if mode not in ("add", "replace", "append"):
        raise ValueError("Mode must be 'add', 'replace', or 'append'")
    target = _copy(A) if axis == "row" else transpose(A)
    source = B if axis == "row" else transpose(B)
    _index(source_index, len(source))
    vector = source[source_index][:]
    if len(vector) != len(target[0]):
        raise ValueError("Source and target vectors must have the same length")
    if mode == "append":
        if target_index is not None:
            raise ValueError("Append does not take a target index")
        if max(len(target) + 1, len(target[0])) > 4:
            raise ValueError("Appending cannot exceed dimension 4")
        target.append(vector)
    else:
        _index(target_index, len(target))
        target[target_index] = (vector if mode == "replace" else
                                [a + b for a, b in zip(target[target_index], vector)])
    return target if axis == "row" else transpose(target)


def check(objective_id, A):
    """Return exact, named predicates for a GameTrix objective."""
    m, n = shape(A)
    square = m == n and 2 <= n <= 4
    square3 = square and n >= 3
    bounded = 2 <= m <= 4 and 2 <= n <= 4
    checks = {}

    def put(name, value):
        checks[name] = bool(value)

    def nonzero():
        return any(x for row in A for x in row)

    def diagonal():
        return m == n and all(not A[i][j] for i in range(m)
                              for j in range(n) if i != j)

    def negative():
        return any(x < 0 for row in A for x in row)

    def signed_permutation():
        return (all(sum(x != 0 for x in row) == 1 for row in A)
                and all(sum(x != 0 for x in col) == 1 for col in zip(*A))
                and all(x in (-1, 0, 1) for row in A for x in row))

    objective_id = objective_id.upper()
    if objective_id == "C01":
        put("shape", square)
        put("symmetric", square and A == transpose(A))
        put("invertible", square and det(A) != 0)
        put("non_diagonal", square and not diagonal())
    elif objective_id in ("C02", "C02+", "C02-"):
        put("shape", square)
        put("identity", square and A == scale(identity(n), -1 if objective_id == "C02-" else 1))
    elif objective_id == "C03":
        put("shape", square3)
        put("diagonal", square3 and diagonal())
        put("nonzero_diagonal", square3 and all(A[i][i] for i in range(n)))
        put("three_distinct_diagonal_values", square3 and len({A[i][i] for i in range(n)}) >= 3)
    elif objective_id == "C04":
        put("shape", square3)
        put("row_sums_one", square3 and all(sum(row) == 1 for row in A))
        put("column_sums_one", square3 and all(sum(col) == 1 for col in zip(*A)))
        put("negative_entry", negative())
    elif objective_id == "C05":
        put("shape", square)
        put("skew_symmetric", square and A == scale(transpose(A), -1))
        put("nonzero", nonzero())
    elif objective_id == "C06":
        put("shape", square)
        put("involution", square and mul(A, A) == identity(n))
        put("non_diagonal", square and not diagonal())
    elif objective_id == "C07":
        put("shape", square)
        put("determinant_one", square and det(A) == 1)
        put("two_nonzeros_per_row", all(sum(x != 0 for x in row) >= 2 for row in A))
        put("two_nonzeros_per_column", all(sum(x != 0 for x in col) >= 2 for col in zip(*A)))
    elif objective_id == "C08":
        put("shape", square3)
        put("non_diagonal", square3 and not diagonal())
        put("rank_two", square3 and rank(A) == 2)
        put("idempotent", square3 and mul(A, A) == A)
    elif objective_id == "C09":
        put("shape", square3)
        A2 = mul(A, A) if square3 else None
        put("cube_zero", square3 and not any(x for row in mul(A2, A) for x in row))
        put("square_nonzero", square3 and any(x for row in A2 for x in row))
    elif objective_id == "C10":
        put("shape", square)
        put("cube_identity", square and mul(mul(A, A), A) == identity(n))
        put("not_signed_permutation", square and not signed_permutation())
    elif objective_id in ("C11", "C12", "C14"):
        tall = (m, n) in ((3, 2), (4, 2), (4, 3))
        wide = (m, n) in ((2, 3), (2, 4), (3, 4))
        valid = tall if objective_id == "C11" else wide
        put("shape", valid)
        vectors = transpose(A) if objective_id == "C11" else A
        put("nonzero_vectors", all(any(v) for v in vectors))
        put("orthogonal_vectors", all(sum(a * b for a, b in zip(vectors[i], vectors[j])) == 0
                                       for i in range(len(vectors)) for j in range(i)))
        put("no_zero_rows" if objective_id == "C11" else "no_zero_columns",
            all(any(v) for v in (A if objective_id == "C11" else transpose(A))))
        if objective_id == "C14":
            put("row_sums_zero", all(sum(row) == 0 for row in A))
    elif objective_id == "C13":
        put("shape", bounded and m != n)
        put("row_sums_n", all(sum(row) == n for row in A))
        put("column_sums_m", all(sum(col) == m for col in zip(*A)))
        put("negative_entry", negative())
    elif objective_id == "W01":
        put("shape", square)
        put("nonzero", nonzero())
        put("singular", square and det(A) == 0)
    elif objective_id == "W02":
        put("shape", bounded)
        put("zero_row", any(not any(row) for row in A))
        put("nonzero", nonzero())
    elif objective_id in ("W03", "W04"):
        put("shape", square)
        upper = objective_id == "W03"
        put("triangular", square and all(not A[i][j] for i in range(n) for j in range(n)
                                         if (i > j if upper else i < j)))
        put("nonzero_off_diagonal", square and any(A[i][j] for i in range(n) for j in range(n)
                                                  if (i < j if upper else i > j)))
    elif objective_id == "W05":
        put("shape", square)
        put("nonzero", nonzero())
        put("trace_zero", square and sum(A[i][i] for i in range(n)) == 0)
    elif objective_id == "W06":
        put("shape", square)
        put("determinant_one", square and det(A) == 1)
    else:
        raise ValueError("Unknown objective ID")
    return {"won": all(checks.values()), "checks": checks, "shape": [m, n]}
