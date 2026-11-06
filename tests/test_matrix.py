import unittest
from fractions import Fraction

import matrix as mx


class ArithmeticTests(unittest.TestCase):
    def test_parse_and_dump_exact(self):
        A = mx.matrix([[1, "2/6"], ["-4/2", "0"]])
        self.assertEqual(A[0][1], Fraction(1, 3))
        self.assertTrue(all(isinstance(x, Fraction) for row in A for x in row))
        self.assertEqual(mx.dump(A), [[1, "1/3"], [-2, 0]])
        self.assertEqual(mx.shape(A), (2, 2))

    def test_invalid_input(self):
        for value in ([], [[]], [[1], []], [[1], [2, 3]], [1],
                      [[True]], [[0.5]], [["1/0"]], [["bad"]],
                      ((1,),), [[Fraction(1, 2)]]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                mx.matrix(value)

    def test_arithmetic_and_no_mutation(self):
        A = mx.matrix([["1/3", 2], [3, 4]])
        B = mx.matrix([["2/3", 1], [2, 1]])
        before = mx.dump(A)
        self.assertEqual(mx.dump(mx.add(A, B)), [[1, 3], [5, 5]])
        self.assertEqual(mx.dump(mx.sub(A, B)), [["-1/3", 1], [1, 3]])
        self.assertEqual(mx.dump(mx.scale(A, Fraction(3, 2))), [["1/2", 3], ["9/2", 6]])
        self.assertEqual(mx.dump(mx.shift(A, "2/3")), [[1, "8/3"], ["11/3", "14/3"]])
        self.assertEqual(mx.dump(mx.transpose(A)), [["1/3", 3], [2, 4]])
        self.assertEqual(mx.dump(A), before)

    def test_rectangular_multiplication(self):
        A = mx.matrix([[1, 2, 3], [4, 5, 6]])
        B = mx.matrix([["1/2"], [2], [-1]])
        self.assertEqual(mx.dump(mx.mul(A, B)), [["3/2"], [6]])
        with self.assertRaises(ValueError):
            mx.mul(B, A)
        for op in (mx.add, mx.sub):
            with self.assertRaises(ValueError):
                op(A, B)

    def test_det_rank_inverse_with_pivoting(self):
        A = mx.matrix([[0, "1/3"], [2, 1]])
        self.assertEqual(mx.det(A), Fraction(-2, 3))
        self.assertEqual(mx.rank(A), 2)
        self.assertEqual(mx.mul(A, mx.inverse(A)), mx.identity(2))
        self.assertEqual(mx.dump(mx.inverse(A)), [["-3/2", "1/2"], [3, 0]])
        R = mx.matrix([["1/3", "2/3", 1], [1, 2, 3]])
        self.assertEqual(mx.rank(R), 1)
        self.assertEqual(mx.rank(mx.matrix([[0, 0], [0, 0], [0, 0]])), 0)
        with self.assertRaises(ValueError):
            mx.inverse(mx.matrix([[1, 2], [2, 4]]))
        for op in (mx.det, mx.inverse, mx.lu):
            with self.assertRaises(ValueError):
                op(R)
        self.assertEqual(mx.det(mx.matrix([["2/3"]])), Fraction(2, 3))
        for n in (0, -1, 2.5, True):
            with self.assertRaises(ValueError):
                mx.identity(n)

    def test_lu_exact_and_final_zero_pivot(self):
        for values in ([[2, 3, 1], [4, 7, 2], [6, 18, 8]],
                       [[1, 2], [2, 4]], [[0]]):
            A = mx.matrix(values)
            before = mx.dump(A)
            L, U = mx.lu(A)
            self.assertEqual(mx.mul(L, U), A)
            self.assertTrue(all(L[i][i] == 1 for i in range(len(L))))
            self.assertTrue(all(U[i][j] == 0 for i in range(len(U)) for j in range(i)))
            self.assertEqual(mx.dump(A), before)
        for values in ([[0, 1], [1, 0]], [[1, 1, 0], [1, 1, 1], [0, 0, 0]]):
            with self.assertRaises(ValueError):
                mx.lu(mx.matrix(values))


class VectorTests(unittest.TestCase):
    def setUp(self):
        self.A = mx.matrix([[1, 2], [3, 4]])
        self.B = mx.matrix([[10, 20], [30, 40]])

    def test_row_add_replace_append(self):
        self.assertEqual(mx.dump(mx.vector_op(self.A, self.B, "row", 1, 0, "add")),
                         [[31, 42], [3, 4]])
        self.assertEqual(mx.dump(mx.vector_op(self.A, self.B, "row", 1, 0, "replace")),
                         [[30, 40], [3, 4]])
        self.assertEqual(mx.dump(mx.vector_op(self.A, self.B, "row", 1, None, "append")),
                         [[1, 2], [3, 4], [30, 40]])
        self.assertEqual(mx.dump(self.A), [[1, 2], [3, 4]])
        self.assertEqual(mx.dump(self.B), [[10, 20], [30, 40]])

    def test_columns_and_swap(self):
        self.assertEqual(mx.dump(mx.vector_op(self.A, self.B, "column", 0, 1, "add")),
                         [[1, 12], [3, 34]])
        self.assertEqual(mx.dump(mx.vector_op(self.A, self.B, "column", 0, 1, "replace")),
                         [[1, 10], [3, 30]])
        self.assertEqual(mx.dump(mx.vector_op(self.A, self.B, "column", 1, None, "append")),
                         [[1, 2, 20], [3, 4, 40]])
        self.assertEqual(mx.dump(mx.swap(self.A, "row", 0, 1)), [[3, 4], [1, 2]])
        self.assertEqual(mx.dump(mx.swap(self.A, "column", 0, 1)), [[2, 1], [4, 3]])
        with self.assertRaises(ValueError):
            mx.swap(self.A, "row", 0, 0)
        equal_rows = mx.matrix([[1, 2], [1, 2]])
        self.assertEqual(mx.swap(equal_rows, "row", 0, 1), equal_rows)

    def test_vector_validation(self):
        cases = [("diagonal", 0, 0, "add"), ("row", -1, 0, "add"),
                 ("row", 0, 2, "replace"), ("row", 0, True, "add"),
                 ("row", 0, None, "add"), ("row", 0, None, "bad"),
                 ("row", 0, 0, "append")]
        for args in cases:
            with self.subTest(args=args), self.assertRaises(ValueError):
                mx.vector_op(self.A, self.B, *args)
        with self.assertRaises(ValueError):
            mx.vector_op(self.A, mx.matrix([[1, 2, 3]]), "row", 0, 0, "add")
        with self.assertRaises(ValueError):
            mx.vector_op(self.A, mx.matrix([[1], [2], [3]]), "column", 0, None, "append")
        with self.assertRaises(ValueError):
            mx.vector_op(mx.matrix([[1, 2]] * 4), self.B, "row", 0, None, "append")
        with self.assertRaises(ValueError):
            mx.vector_op(mx.matrix([[1] * 4] * 2), self.B, "column", 0, None, "append")
        with self.assertRaises(ValueError):
            mx.swap(self.A, "column", 0, -1)


class ObjectiveTests(unittest.TestCase):
    def won(self, goal, values):
        result = mx.check(goal, mx.matrix(values))
        self.assertEqual(result["shape"], [len(values), len(values[0])])
        self.assertTrue(all(isinstance(x, bool) for x in result["checks"].values()))
        return result["won"]

    def test_every_objective_has_a_winning_example(self):
        examples = {
            "C01": [[1, 1], [1, 2]],
            "C02": [[1, 0], [0, 1]],
            "C02+": [[1, 0], [0, 1]],
            "C02-": [[-1, 0], [0, -1]],
            "C03": [[1, 0, 0], [0, 2, 0], [0, 0, 3]],
            "C04": [[-1, 1, 1], [1, 0, 0], [1, 0, 0]],
            "C05": [[0, 2], [-2, 0]],
            "C06": [[1, 2], [0, -1]],
            "C07": [[1, 1], [1, 2]],
            "C08": [[1, 0, 1], [0, 1, 0], [0, 0, 0]],
            "C09": [[0, 1, 0], [0, 0, 1], [0, 0, 0]],
            "C10": [[0, -1], [1, -1]],
            "C11": [[1, 1], [1, -1], [1, 0]],
            "C12": [[1, 1, 1], [1, -1, 0]],
            "C13": [[-1, 1, 3], [3, 1, -1]],
            "C14": [[1, -1, 0], [1, 1, -2]],
            "W01": [[1, 2], [2, 4]],
            "W02": [[0, 0, 0], [1, 2, 3]],
            "W03": [[0, 1], [0, 0]],
            "W04": [[0, 0], [1, 0]],
            "W05": [[1, 2], [3, -1]],
            "W06": [[1, 1], [1, 2]],
        }
        for goal, values in examples.items():
            with self.subTest(goal=goal):
                self.assertTrue(self.won(goal, values))

    def test_square_goals_reject_rectangular_without_undefined_operations(self):
        goals = [f"C{i:02}" for i in range(1, 11)] + ["C02-", "W01", "W03", "W04", "W05", "W06"]
        for goal in goals:
            with self.subTest(goal=goal):
                self.assertFalse(self.won(goal, [[1, 0, 0], [0, 1, 0]]))
                self.assertFalse(self.won(goal, [[1]]))
                self.assertFalse(mx.check(goal, mx.identity(5))["won"])

    def test_nontriviality_and_shape_constraints(self):
        cases = {
            "C01": [[1, 0], [0, 2]],
            "C02-": [[1, 0], [0, 1]],
            "C03": [[1, 0, 0], [0, 2, 0], [0, 0, 2]],
            "C04": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
            "C05": [[0, 0], [0, 0]],
            "C06": [[1, 0], [0, -1]],
            "C07": [[1, 1], [0, 1]],
            "C08": [[1, 0, 0], [0, 1, 0], [0, 0, 0]],
            "C09": [[0, 1, 0], [0, 0, 0], [0, 0, 0]],
            "C10": [[0, 1, 0], [0, 0, 1], [1, 0, 0]],
            "C11": [[1, 0], [0, 1], [0, 0]],
            "C12": [[1, 0, 0], [0, 1, 0]],
            "C13": [[1, 1], [1, 1]],
            "C14": [[1, 1, 1], [1, -1, 0]],
            "W01": [[0, 0], [0, 0]],
            "W02": [[0, 0], [0, 0]],
            "W03": [[1, 0], [0, 1]],
            "W04": [[1, 0], [0, 1]],
            "W05": [[0, 0], [0, 0]],
            "W06": [[2, 0], [0, 1]],
        }
        for goal, values in cases.items():
            with self.subTest(goal=goal):
                self.assertFalse(self.won(goal, values))
        for goal in ("C11", "C12", "C14"):
            self.assertFalse(self.won(goal, [[1, 0], [0, 1]]))
        self.assertFalse(self.won("C13", [[-1, 5]]))
        self.assertFalse(self.won("W02", [[0, 0]]))

    def test_fractional_objectives_and_four_dimensional_examples(self):
        self.assertTrue(self.won("C08", [["1/2", "1/2", 0], ["1/2", "1/2", 0], [0, 0, 1]]))
        self.assertTrue(self.won("C11", [[1, 1, 1], [1, -1, 1], [1, 1, -1], [1, -1, -1]]))
        self.assertTrue(self.won("C14", [[1, -1, 0, 0], [1, 1, -2, 0], [1, 1, 1, -3]]))
        with self.assertRaises(ValueError):
            mx.check("C99", mx.identity(2))


if __name__ == "__main__":
    unittest.main()
