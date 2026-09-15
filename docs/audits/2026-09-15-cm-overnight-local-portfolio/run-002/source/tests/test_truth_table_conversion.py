import numpy as np

from cm_bench import cm_matrix_to_tt


def test_cm_matrix_to_tt_no_padding_ordered_vars():
    matrix = np.array([[0, 0], [0, 1]], dtype=np.uint8)

    tt = cm_matrix_to_tt(matrix, ["x0"], ["x1"], 2)

    assert np.array_equal(tt, np.array([0, 0, 0, 1], dtype=np.uint8))


def test_cm_matrix_to_tt_permuted_row_column_vars():
    matrix = np.array([[0, 1], [0, 0]], dtype=np.uint8)

    tt = cm_matrix_to_tt(matrix, ["x1"], ["x0"], 2)

    assert np.array_equal(tt, np.array([0, 0, 1, 0], dtype=np.uint8))


def test_cm_matrix_to_tt_removes_padding_axis():
    arr = np.zeros((2, 2, 2), dtype=np.uint8)
    arr[:, 0, :] = np.array([[0, 1], [1, 1]], dtype=np.uint8)
    arr[:, 1, :] = 1
    matrix = arr.reshape(4, 2)

    tt = cm_matrix_to_tt(matrix, ["x0", "__pad0"], ["x1"], 2)

    assert np.array_equal(tt, np.array([0, 1, 1, 1], dtype=np.uint8))

