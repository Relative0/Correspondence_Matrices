/* Research-only serial rank control. Input rows are little-endian packed bytes. */
#include <stddef.h>
#include <stdint.h>
#include <m4ri/m4ri.h>

int cm_m4ri_rank(const uint8_t *data, size_t length, int rows, int columns) {
    if (rows < 0 || rows > 16384 || columns < 0 || columns > 8193) return -1;
    size_t stride = ((size_t)columns + 7) / 8;
    if (length != (size_t)rows * stride || (length && !data)) return -1;
    if (!rows || !columns) return 0;
    mzd_t *matrix = mzd_init(rows, columns);
    if (!matrix) return -2;
    for (int i = 0; i < rows; ++i) {
        for (size_t j = 0; j < stride; ++j) {
            unsigned value = data[(size_t)i * stride + j];
            while (value) {
                unsigned bit = (unsigned)__builtin_ctz(value);
                size_t column = 8 * j + bit;
                if (column >= (size_t)columns) { mzd_free(matrix); return -1; }
                mzd_write_bit(matrix, i, (rci_t)column, 1);
                value &= value - 1;
            }
        }
    }
    int rank = mzd_echelonize(matrix, 0);
    mzd_free(matrix);
    return rank;
}
