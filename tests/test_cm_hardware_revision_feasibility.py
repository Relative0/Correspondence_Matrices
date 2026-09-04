from __future__ import annotations

import json
from pathlib import Path
import subprocess

from cmbench.comparative import hardware_revision_feasibility as audit


def test_candidate_roles_and_selection_contract_are_frozen():
    assert [row["slug"] for row in audit.CANDIDATES] == [
        "alexforencich/verilog-axi", "lowRISC/ibex", "olofk/serv", "YosysHQ/picorv32"
    ]
    assert [row["role"] for row in audit.CANDIDATES] == [
        "development", "development", "confirmation", "confirmation"
    ]
    assert audit.CUTOFF == "2026-09-04T00:00:00Z"
    assert audit.MAX_TRANSITIONS == 12


def test_comment_stripping_preserves_strings_and_driver_semantics():
    source = b'''module demo(input a, b, output y, z);\n
      assign y = a /* ignored */ & b; // ignored\n
      always_comb begin\n
        if (a <= b) z <= y;\n
        else z <= 1'b0;\n
      end\n
    endmodule\n'''
    parsed = audit.parse_driver_regions(source)
    assert parsed["status"] == "parsed"
    assert parsed["discovered"] == 2
    assert parsed["admitted"] == 2
    assert set(parsed["drivers"]) == {"demo::y", "demo::z"}
    changed = source.replace(b"z <= y", b"z <= a")
    comparison = audit.compare_driver_regions(parsed, audit.parse_driver_regions(changed))
    assert comparison == {
        "comparable": 2, "changed": 1, "unchanged": 1, "added": 0, "removed": 0,
        "changed_identities": ["demo::z"],
    }


def test_ambiguous_macro_and_generated_drivers_fail_closed():
    source = b'''module demo(input a, output y, z);\n
      assign y = a;\n
      assign y = ~a;\n
      assign z = `SELECT(a);\n
      generate assign extra = a; endgenerate\n
    endmodule\n'''
    parsed = audit.parse_driver_regions(source)
    assert parsed["drivers"] == {}
    assert parsed["ambiguous_identities"] == ["demo::y"]
    assert parsed["discovered"] == 4
    assert parsed["refused"] == 4


def _git(repository: Path, *arguments: str, env: dict[str, str] | None = None) -> str:
    return subprocess.check_output(["git", "-C", str(repository), *arguments], text=True, env=env).strip()


def test_first_parent_transition_selection_is_mechanical(tmp_path: Path):
    repository = tmp_path / "repo"
    repository.mkdir()
    subprocess.run(["git", "init", "-b", "main", str(repository)], check=True, capture_output=True)
    _git(repository, "config", "user.email", "fixture@example.invalid")
    _git(repository, "config", "user.name", "Fixture")
    environment = {**__import__("os").environ, "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z",
                   "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z"}
    (repository / "LICENSE").write_text("fixture", encoding="utf-8")
    (repository / "design.v").write_text("module a; assign y = 0; endmodule\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repository), "add", "LICENSE", "design.v"], check=True, env=environment)
    subprocess.run(["git", "-C", str(repository), "commit", "-m", "initial"], check=True,
                   capture_output=True, env=environment)
    (repository / "README.md").write_text("docs", encoding="utf-8")
    subprocess.run(["git", "-C", str(repository), "add", "README.md"], check=True, env=environment)
    subprocess.run(["git", "-C", str(repository), "commit", "-m", "docs only"], check=True,
                   capture_output=True, env=environment)
    (repository / "design.v").write_text("module a; assign y = 1; endmodule\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repository), "add", "design.v"], check=True, env=environment)
    subprocess.run(["git", "-C", str(repository), "commit", "-m", "hardware edit"], check=True,
                   capture_output=True, env=environment)
    rows = audit.select_transitions(repository, _git(repository, "rev-parse", "HEAD"), maximum=4)
    assert [row["subject"] for row in rows] == ["hardware edit"]
    assert rows[0]["hdl_changes"][0]["new_path"] == "design.v"


def test_summary_requires_both_confirmation_histories_and_replay():
    def repository(slug: str, role: str, changed: int, transitions: int = 6):
        rows = []
        for index in range(transitions):
            count = changed // transitions + int(index < changed % transitions)
            rows.append({"has_changed_stable_seeds": count > 0,
                         "seed_counts": {"changed": count, "comparable": 20,
                                         "unchanged": 20 - count, "added": 0, "removed": 0},
                         "paths": [{"before": {"parse": {"discovered": 10, "admitted": 9}},
                                    "after": {"parse": {"discovered": 10, "admitted": 9}}}]})
        return {"slug": slug, "role": role, "status": "admitted", "refusal": None,
                "selected_transition_count": transitions, "transitions": rows}
    evidence = {"repositories": [repository("d1", "development", 6),
                                  repository("d2", "development", 6),
                                  repository("c1", "confirmation", 30),
                                  repository("c2", "confirmation", 30)]}
    summary = audit.summarize(evidence)
    assert all(summary["conditions"].values())
    assert summary["status_without_replay"] == "admissible_pending_replay"
    evidence["repositories"][-1]["transitions"] = evidence["repositories"][-1]["transitions"][:3]
    evidence["repositories"][-1]["selected_transition_count"] = 3
    assert audit.summarize(evidence)["status_without_replay"] == "insufficient_activation_or_provenance"
