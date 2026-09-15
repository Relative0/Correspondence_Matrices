from __future__ import annotations

from cmbench.comparative import hardware_behavior_corpus as audit


def test_frozen_candidates_split_paths_and_bounds():
    assert [row["slug"] for row in audit.CANDIDATES] == [
        "alexforencich/verilog-axi",
        "lowRISC/ibex",
        "black-parrot/black-parrot",
        "ultraembedded/riscv",
    ]
    assert [row["role"] for row in audit.CANDIDATES] == [
        "development", "development", "confirmation", "confirmation",
    ]
    assert audit.CUTOFF == "2026-09-04T00:00:00Z"
    assert audit.MAX_SCANNED_COMMITS == 160
    assert audit.MAX_SELECTED_TRANSITIONS == 12
    black_parrot = audit.CANDIDATES[2]
    assert audit._eligible_path("bp_be/src/v/core.sv", black_parrot)
    assert not audit._eligible_path("bp_be/test/core.sv", black_parrot)
    riscv = audit.CANDIDATES[3]
    assert audit._eligible_path("core/riscv/riscv_core.v", riscv)
    assert not audit._eligible_path("top_cache_axi/src_v/riscv_top.v", riscv)


def test_driver_parser_covers_sequential_and_combinational_blocks():
    source = b'''module demo(input clk, a, b, d, output y, q, z);
      assign y = a /* ignored */ & b; // ignored
      always_ff @(posedge clk) begin
        if (a <= b) q <= d;
        else q <= 1'b0;
      end
      always @(*) z = q | a;
    endmodule
'''
    parsed = audit.parse_driver_regions(source)
    assert parsed["status"] == "parsed"
    assert parsed["discovered"] == 3
    assert parsed["admitted"] == 3
    assert set(parsed["drivers"]) == {"demo::y", "demo::q", "demo::z"}
    changed = source.replace(b"q <= d", b"q <= y")
    comparison = audit.compare_driver_regions(parsed, audit.parse_driver_regions(changed))
    assert comparison["changed_identities"] == ["demo::q"]
    assert comparison["unchanged_identities"] == ["demo::y", "demo::z"]
    assert (comparison["changed"], comparison["unchanged"]) == (1, 2)


def test_ambiguous_macro_generated_and_incomplete_regions_fail_closed():
    source = b'''module demo(input a, output y, z);
      assign y = a;
      assign y = ~a;
      always_comb z = `SELECT(a);
      generate assign extra = a; endgenerate
    endmodule
'''
    parsed = audit.parse_driver_regions(source)
    assert parsed["drivers"] == {}
    assert parsed["ambiguous_identities"] == ["demo::y"]
    assert parsed["discovered"] == 4
    assert parsed["refused"] == 4
    incomplete = audit.parse_driver_regions(
        b"module bad(input clk, d, output q); always_ff @(posedge clk) begin q <= d; endmodule"
    )
    assert incomplete["drivers"] == {}
    assert incomplete["refused"] >= 1


def test_selection_reason_requires_change_reuse_and_non_rebuild():
    assert audit.selection_reason({"changed": 0, "unchanged": 8, "comparable": 8}) == (
        "no_changed_stable_driver"
    )
    assert audit.selection_reason({"changed": 2, "unchanged": 0, "comparable": 2}) == (
        "no_reusable_stable_driver"
    )
    assert audit.selection_reason({"changed": 10, "unchanged": 1, "comparable": 11}) == (
        "near_total_stable_driver_rebuild"
    )
    assert audit.selection_reason({"changed": 9, "unchanged": 1, "comparable": 10}) is None


def _repository(slug: str, role: str, transitions: int = 8) -> dict[str, object]:
    scans = []
    for index in range(transitions):
        path = f"rtl/unit_{index % 4}.sv"
        module = f"unit_{index}"
        scans.append({
            "selection": "selected",
            "reason": None,
            "driver_counts": {"comparable": 10, "changed": 1, "unchanged": 9,
                              "added": 0, "removed": 0},
            "changed_driver_keys": [f"{path}::{module}::changed_{index}"],
            "unchanged_driver_keys": [f"{path}::{module}::stable_{index}"],
            "paths": [{
                "before": {"parse": {"discovered": 10, "admitted": 8}},
                "after": {"parse": {"discovered": 10, "admitted": 8}},
            }],
        })
    return {
        "slug": slug,
        "role": role,
        "status": "admitted",
        "refusal": None,
        "scanned_commit_count": transitions,
        "selected_transition_count": transitions,
        "scans": scans,
    }


def test_summary_enforces_confirmation_diversity_activation_and_coverage():
    evidence = {"repositories": [
        _repository("d1", "development"),
        _repository("d2", "development"),
        _repository("c1", "confirmation"),
        _repository("c2", "confirmation"),
    ]}
    summary = audit.summarize(evidence)
    assert all(summary["conditions"].values())
    assert summary["status_without_replay"] == "admissible_pending_replay"
    evidence["repositories"][-1]["scans"] = evidence["repositories"][-1]["scans"][:7]
    evidence["repositories"][-1]["selected_transition_count"] = 7
    failed = audit.summarize(evidence)
    assert not failed["conditions"]["confirmation_each_has_eight_selected_transitions"]
    assert failed["status_without_replay"] == "insufficient_behavior_change_or_provenance"
