#include "../cm_fused_slots/fused_slot_executor.c"

/*
 * Successor ABI for repeated one-root restrictions of the same residual width.
 *
 * The frozen v1 implementation remains unchanged and supplies the exact scalar
 * kernel above.  This entry point moves the repeated-call loop across the FFI
 * boundary while retaining the same caller-owned workspace and output layout.
 */
CM_EXPORT int cm_fused_slots_eval_batch(
    const uint8_t *opcodes,
    const int32_t *child_a,
    const int32_t *child_b,
    const int16_t *variable_indices,
    size_t node_count,
    size_t root,
    const int16_t *bindings,
    size_t query_count,
    size_t variable_count,
    size_t live_count,
    size_t word_count,
    uint64_t *workspace,
    uint64_t *outputs
) {
    if (bindings == NULL || outputs == NULL || query_count == 0U) {
        return 10;
    }
    for (size_t query = 0U; query < query_count; ++query) {
        const int status = cm_fused_slots_eval(
            opcodes,
            child_a,
            child_b,
            variable_indices,
            node_count,
            root,
            bindings + query * variable_count,
            variable_count,
            live_count,
            word_count,
            workspace,
            outputs + query * word_count
        );
        if (status != 0) {
            return status;
        }
    }
    return 0;
}

CM_EXPORT uint32_t cm_fused_slots_batch_abi_version(void) {
    return UINT32_C(1);
}
