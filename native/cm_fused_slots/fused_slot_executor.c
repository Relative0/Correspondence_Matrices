#include <stddef.h>
#include <stdint.h>
#include <string.h>

#if defined(_WIN32)
#define CM_EXPORT __declspec(dllexport)
#else
#define CM_EXPORT __attribute__((visibility("default")))
#endif

enum {
    CM_VAR = 0,
    CM_NOT = 1,
    CM_AND = 2,
    CM_OR = 3,
    CM_XOR = 4,
    CM_IMP = 5,
    CM_EQV = 6
};

static uint64_t low_mask(unsigned bits) {
    if (bits >= 64U) {
        return UINT64_MAX;
    }
    return (UINT64_C(1) << bits) - UINT64_C(1);
}

static uint64_t live_variable_word(
    size_t live_count,
    size_t live_position,
    size_t word_index
) {
    const size_t block = (size_t)1U << (live_count - 1U - live_position);
    if (block >= 64U) {
        return (((word_index * 64U) / block) & 1U) ? UINT64_MAX : UINT64_C(0);
    }
    uint64_t value = UINT64_C(0);
    const uint64_t run = low_mask((unsigned)block);
    for (size_t start = block; start < 64U; start += block * 2U) {
        value |= run << start;
    }
    return value;
}

/*
 * bindings use -1 for fixed zero, -2 for fixed one, and a non-negative
 * residual-variable position for a live variable.  Workspace contains
 * node_count * word_count uint64_t cells and is owned by the caller.
 */
CM_EXPORT int cm_fused_slots_eval(
    const uint8_t *opcodes,
    const int32_t *child_a,
    const int32_t *child_b,
    const int16_t *variable_indices,
    size_t node_count,
    size_t root,
    const int16_t *bindings,
    size_t variable_count,
    size_t live_count,
    size_t word_count,
    uint64_t *workspace,
    uint64_t *output
) {
    if (opcodes == NULL || child_a == NULL || child_b == NULL
            || variable_indices == NULL || bindings == NULL
            || workspace == NULL || output == NULL || node_count == 0U
            || root >= node_count || live_count == 0U || live_count >= 31U) {
        return 1;
    }
    const size_t row_count = (size_t)1U << live_count;
    const size_t expected_words = (row_count + 63U) / 64U;
    if (word_count != expected_words) {
        return 2;
    }
    const unsigned tail_bits = (unsigned)(row_count & 63U);
    const uint64_t tail_mask = tail_bits == 0U ? UINT64_MAX : low_mask(tail_bits);

    for (size_t slot = 0U; slot < node_count; ++slot) {
        uint64_t *destination = workspace + slot * word_count;
        const uint8_t opcode = opcodes[slot];
        if (opcode == CM_VAR) {
            const int16_t variable = variable_indices[slot];
            if (variable < 0 || (size_t)variable >= variable_count) {
                return 3;
            }
            const int16_t binding = bindings[variable];
            if (binding == -1) {
                memset(destination, 0, word_count * sizeof(uint64_t));
            } else if (binding == -2) {
                for (size_t word = 0U; word < word_count; ++word) {
                    destination[word] = UINT64_MAX;
                }
                destination[word_count - 1U] &= tail_mask;
            } else if (binding >= 0 && (size_t)binding < live_count) {
                for (size_t word = 0U; word < word_count; ++word) {
                    destination[word] = live_variable_word(
                        live_count, (size_t)binding, word);
                }
                destination[word_count - 1U] &= tail_mask;
            } else {
                return 4;
            }
            continue;
        }

        const int32_t a_slot = child_a[slot];
        if (a_slot < 0 || (size_t)a_slot >= slot) {
            return 5;
        }
        const uint64_t *left = workspace + (size_t)a_slot * word_count;
        const uint64_t *right = NULL;
        if (opcode != CM_NOT) {
            const int32_t b_slot = child_b[slot];
            if (b_slot < 0 || (size_t)b_slot >= slot) {
                return 6;
            }
            right = workspace + (size_t)b_slot * word_count;
        }
        for (size_t word = 0U; word < word_count; ++word) {
            switch (opcode) {
                case CM_NOT:
                    destination[word] = ~left[word];
                    break;
                case CM_AND:
                    destination[word] = left[word] & right[word];
                    break;
                case CM_OR:
                    destination[word] = left[word] | right[word];
                    break;
                case CM_XOR:
                    destination[word] = left[word] ^ right[word];
                    break;
                case CM_IMP:
                    destination[word] = (~left[word]) | right[word];
                    break;
                case CM_EQV:
                    destination[word] = ~(left[word] ^ right[word]);
                    break;
                default:
                    return 7;
            }
        }
        destination[word_count - 1U] &= tail_mask;
    }
    memcpy(output, workspace + root * word_count, word_count * sizeof(uint64_t));
    return 0;
}

CM_EXPORT int cm_fused_slots_eval_multi(
    const uint8_t *opcodes,
    const int32_t *child_a,
    const int32_t *child_b,
    const int16_t *variable_indices,
    size_t node_count,
    const int32_t *roots,
    size_t root_count,
    const int16_t *bindings,
    size_t variable_count,
    size_t live_count,
    size_t word_count,
    uint64_t *workspace,
    uint64_t *outputs
) {
    if (roots == NULL || outputs == NULL || root_count == 0U) {
        return 8;
    }
    for (size_t index = 0U; index < root_count; ++index) {
        if (roots[index] < 0 || (size_t)roots[index] >= node_count) {
            return 9;
        }
    }
    int status = cm_fused_slots_eval(
        opcodes, child_a, child_b, variable_indices, node_count,
        (size_t)roots[0], bindings, variable_count, live_count, word_count,
        workspace, outputs);
    if (status != 0) {
        return status;
    }
    for (size_t index = 0U; index < root_count; ++index) {
        memcpy(
            outputs + index * word_count,
            workspace + (size_t)roots[index] * word_count,
            word_count * sizeof(uint64_t));
    }
    return 0;
}

CM_EXPORT uint32_t cm_fused_slots_abi_version(void) {
    return UINT32_C(1);
}
