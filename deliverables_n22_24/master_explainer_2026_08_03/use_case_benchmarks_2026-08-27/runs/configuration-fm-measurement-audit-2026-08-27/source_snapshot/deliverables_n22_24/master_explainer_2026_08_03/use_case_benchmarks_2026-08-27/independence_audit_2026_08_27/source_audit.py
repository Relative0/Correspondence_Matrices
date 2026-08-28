"""Independent source-to-residual reconstruction and refusal corroboration.

No benchmark producer, compiler, or earlier auditor is imported.  Historical
joint witnesses were not retained: this auditor regenerates them with the
CaDiCaL195 backend and saves them as retrospective evidence.  The installed
wrapper version is recorded even when it differs from the historical run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from artifact_audit import (
    CORE, DELTA, PILOT, csv_rows, digest_packed, finalize, read_json,
    require, scalar_cnf_vector, sha, snapshot, verify_run, write_csv, write_json,
)


@dataclass
class Formula:
    variables: int
    clauses: list[tuple[int, ...]]
    names: dict[int, str]


def parse_dimacs(path: Path) -> Formula:
    variables = declared = None
    clauses = []
    names = {}
    pending = []
    with path.open("rb") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            if line.startswith(b"c"):
                fields = line.split(maxsplit=2)
                if len(fields) == 3 and fields[0] == b"c" and fields[1].isdigit():
                    number, name = int(fields[1]), fields[2].decode("utf-8", errors="strict").strip()
                    require(number not in names or names[number] == name, "conflicting source feature mapping")
                    if name:
                        names[number] = name
                continue
            if line.startswith(b"p"):
                fields = line.split()
                require(variables is None and not clauses and not pending, "misplaced DIMACS header")
                require(len(fields) == 4 and fields[:2] == [b"p", b"cnf"], "unsupported DIMACS header")
                variables, declared = int(fields[2]), int(fields[3])
                require(variables >= 0 and declared >= 0, "negative DIMACS size")
                continue
            require(variables is not None, "DIMACS clauses before header")
            for field in line.split():
                literal = int(field)
                if literal == 0:
                    clauses.append(tuple(pending))
                    pending = []
                else:
                    require(1 <= abs(literal) <= variables, "source literal outside header range")
                    pending.append(literal)
    require(variables is not None and not pending and len(clauses) == declared, "incomplete DIMACS")
    names = {variable: name for variable, name in names.items() if 1 <= variable <= variables}
    require(len(set(names.values())) == len(names), "duplicate source feature names")
    return Formula(variables, clauses, names)


def valid(formula: Formula, product: dict[int, bool]) -> bool:
    return all(any(product[abs(literal)] == (literal > 0) for literal in clause) for clause in formula.clauses)


def decode_product(row: dict) -> dict[int, bool]:
    width = int(row["n_vars"])
    raw = bytes.fromhex(row["product_little_endian_hex"])
    require(len(raw) == (width + 7) // 8, "witness byte length")
    require(hashlib.sha256(raw).hexdigest() == row["product_sha256"], "witness hash mismatch")
    return {variable: bool(raw[(variable - 1) >> 3] & (1 << ((variable - 1) & 7))) for variable in range(1, width + 1)}


def encode_product(product: dict[int, bool], n: int) -> dict:
    raw = bytearray((n + 7) // 8)
    for variable, selected in product.items():
        if selected:
            raw[(variable - 1) >> 3] |= 1 << ((variable - 1) & 7)
    return {"n_vars": n, "product_little_endian_hex": raw.hex(),
            "product_sha256": hashlib.sha256(raw).hexdigest()}


def condition(formula: Formula, product: dict[int, bool], variables: tuple[int, ...]) -> tuple[tuple[int, ...], ...]:
    numbering = {variable: index + 1 for index, variable in enumerate(variables)}
    residual = []
    for clause in formula.clauses:
        if any(abs(literal) not in numbering and product[abs(literal)] == (literal > 0) for literal in clause):
            continue
        free = tuple(numbering[abs(literal)] * (1 if literal > 0 else -1)
                     for literal in clause if abs(literal) in numbering)
        require(bool(free), "conditioning a checked satisfying product yielded an empty clause")
        residual.append(free)
    return tuple(residual)


def joint_formula(earlier: Formula, later: Formula) -> tuple[list[tuple[int, ...]], list[int]]:
    """Keep earlier IDs, then map shared names; allocate unique later IDs last."""
    earlier_by_name = {name: variable for variable, name in earlier.names.items()}
    next_id = earlier.variables
    later_ids = [0] * (later.variables + 1)
    for variable in range(1, later.variables + 1):
        name = later.names.get(variable)
        shared = earlier_by_name.get(name) if name is not None else None
        if shared is not None:
            later_ids[variable] = shared
        else:
            next_id += 1
            later_ids[variable] = next_id
    clauses = list(earlier.clauses)
    clauses.extend(tuple(later_ids[abs(literal)] * (1 if literal > 0 else -1) for literal in clause)
                   for clause in later.clauses)
    return clauses, later_ids


def opposing_named_units(earlier: Formula, later: Formula) -> list[dict]:
    units = []
    for formula in (earlier, later):
        current = {}
        for clause_index, clause in enumerate(formula.clauses, start=1):
            if len(clause) == 1 and abs(clause[0]) in formula.names:
                literal = clause[0]
                current.setdefault(formula.names[abs(literal)], []).append((literal, clause_index))
        units.append(current)
    proofs = []
    for name in sorted(set(units[0]) & set(units[1])):
        for left, left_index in units[0][name]:
            for right, right_index in units[1][name]:
                if (left > 0) != (right > 0):
                    proofs.append({"feature_name": name,
                                   "earlier_clause_index_1based": left_index, "earlier_unit_literal": left,
                                   "later_clause_index_1based": right_index, "later_unit_literal": right,
                                   "certificate": "equal feature name forces both true and false in the joint CNF"})
    return proofs


def audit(source: Path, output: Path) -> dict:
    import pysat
    from pysat.solvers import Solver

    require(not output.exists(), f"refusing to overwrite {output}")
    output.mkdir(parents=True)
    observed = snapshot(output)
    runs = [verify_run(run) for run in (PILOT, CORE, DELTA)]
    write_json(output / "historical-run-identities.json", runs)
    provenance = read_json(PILOT / "SOURCE-PROVENANCE.json")
    witnesses = {row["model_id"]: row for row in
                 (json.loads(line) for line in (PILOT / "witnesses.jsonl").read_text(encoding="utf-8").splitlines())}
    corpus = [json.loads(line) for line in (CORE / "corpus.jsonl").read_text(encoding="utf-8").splitlines()]
    delta_cases = {row["case_id"]: row for row in
                   (json.loads(line) for line in (DELTA / "cases.jsonl").read_text(encoding="utf-8").splitlines())}
    saved_delta_rows = {row["case_id"]: row for row in csv_rows(DELTA / "version-delta.csv")}
    admissions = {row["transition_id"]: row for row in csv_rows(DELTA / "admissions.csv")}
    formulas, inputs = {}, []
    endpoint_rows = []
    for index, payload in enumerate(provenance["selected_payloads"], start=1):
        filename = payload["cache_filename"]
        require(Path(filename).name == filename, "unsafe source cache filename")
        path = source / "selected_payloads" / filename
        require(sha(path) == payload["dimacs_sha256"], f"source digest mismatch: {path}")
        formula = parse_dimacs(path)
        model_id = payload["model_id"]
        formulas[model_id] = formula
        inputs.append({"model_id": model_id, "path": str(path), "sha256": payload["dimacs_sha256"],
                       "variables": formula.variables, "clauses": len(formula.clauses), "named_features": len(formula.names)})
        product = decode_product(witnesses[model_id])
        require(formula.variables == int(witnesses[model_id]["n_vars"]) and valid(formula, product), f"invalid original witness: {model_id}")
        incidence = Counter(abs(literal) for clause in formula.clauses for literal in clause)
        for case in (row for row in corpus if row["model_id"] == model_id):
            k = int(case["k"])
            if case["slice_kind"] == "incidence":
                variables = tuple(sorted(formula.names, key=lambda variable: (-incidence[variable], variable))[:k])
            else:
                require(case["slice_kind"] == "hash", "unknown endpoint slice")
                variables = tuple(sorted(formula.names, key=lambda variable: hashlib.sha256(f"{model_id}|{variable}".encode()).digest())[:k])
            residual = condition(formula, product, variables)
            require(residual == tuple(map(tuple, case["residual"])), f"endpoint residual reconstruction mismatch: {case['case_id']}")
            require(list(variables) == case["metadata"]["slice_variables"], "endpoint variable ordering mismatch")
            require([formula.names[variable] for variable in variables] == case["metadata"]["slice_feature_names"], "endpoint feature-name mismatch")
            endpoint_rows.append({"case_id": case["case_id"], "source_sha256": payload["dimacs_sha256"],
                                  "original_witness_valid": True, "exact_residual_reconstructed": True,
                                  "residual_clauses": len(residual), "k": k})
        if index % 10 == 0:
            print(f"source endpoint reconstruction {index}/40", flush=True)
    write_csv(output / "endpoint-source-reconstruction.csv", endpoint_rows)
    write_csv(output / "source-inputs.csv", inputs)

    transition_rows, reconstructed_rows, joint_witnesses = [], [], []
    for history_group in provenance["transitions"]:
        history = history_group["history"]
        for transition in history_group["transitions"]:
            earlier_id = f"{history}@{transition['earlier_version']}"
            later_id = f"{history}@{transition['later_version']}"
            transition_id = f"{earlier_id}->{transition['later_version']}"
            earlier, later = formulas[earlier_id], formulas[later_id]
            print(f"joint reconstruction {len(transition_rows) + 1}/21: {transition_id}", flush=True)
            clauses, later_ids = joint_formula(earlier, later)
            with Solver(name="cadical195", bootstrap_with=clauses) as solver:
                sat = solver.solve()
                model = {abs(literal): literal > 0 for literal in (solver.get_model() or [])} if sat else {}
            expected_admission = admissions[transition_id]["admitted"] == "True"
            require(sat == expected_admission, f"transition admission changed: {transition_id}")
            if not sat:
                with Solver(name="minisat22", bootstrap_with=clauses) as independent_solver:
                    second_sat = independent_solver.solve()
                require(not second_sat, f"independent solver disagrees with refusal: {transition_id}")
                unit_certificates = opposing_named_units(earlier, later)
                write_json(output / "refusal-certificate.json", {
                    "transition_id": transition_id, "caDiCaL195_result": "UNSAT", "MiniSat22_result": "UNSAT",
                    "source_payloads": [item for item in inputs if item["model_id"] in (earlier_id, later_id)],
                    "opposing_unit_certificates": unit_certificates,
                    "scope": "joint formula under exact-name identification; not either original model alone",
                })
                transition_rows.append({"transition_id": transition_id, "admitted": False,
                                        "source_witness_verified": False, "second_solver_refusal_confirmed": True,
                                        "direct_unit_certificates": len(unit_certificates), "exact_residuals_reconstructed": 0})
                continue
            earlier_product = {variable: model.get(variable, False) for variable in range(1, earlier.variables + 1)}
            later_product = {variable: model.get(later_ids[variable], False) for variable in range(1, later.variables + 1)}
            require(valid(earlier, earlier_product) and valid(later, later_product), "regenerated joint witness invalid at source")
            earlier_names = {name: variable for variable, name in earlier.names.items()}
            later_names = {name: variable for variable, name in later.names.items()}
            common = set(earlier_names) & set(later_names)
            require(all(earlier_product[earlier_names[name]] == later_product[later_names[name]] for name in common), "shared context disagrees")
            left_incidence = Counter(abs(literal) for clause in earlier.clauses for literal in clause)
            right_incidence = Counter(abs(literal) for clause in later.clauses for literal in clause)
            joint_witnesses.append({"transition_id": transition_id, "retrospective_reconstruction": True,
                                    "earlier": encode_product(earlier_product, earlier.variables),
                                    "later": encode_product(later_product, later.variables)})
            for k in (8, 12, 16):
                for kind in ("incidence", "hash"):
                    if kind == "incidence":
                        names = sorted(common, key=lambda name: (-(left_incidence[earlier_names[name]] + right_incidence[later_names[name]]), name))[:k]
                    else:
                        names = sorted(common, key=lambda name: hashlib.sha256(f"{transition_id}|{name}".encode()).digest())[:k]
                    case_id = f"{transition_id}|{kind}|k{k}"
                    saved = delta_cases[case_id]
                    require(names == saved["feature_names"], f"transition slice feature ordering mismatch: {case_id}")
                    earlier_residual = condition(earlier, earlier_product, tuple(earlier_names[name] for name in names))
                    later_residual = condition(later, later_product, tuple(later_names[name] for name in names))
                    require(earlier_residual == tuple(map(tuple, saved["earlier_residual"])), f"earlier residual mismatch: {case_id}")
                    require(later_residual == tuple(map(tuple, saved["later_residual"])), f"later residual mismatch: {case_id}")
                    left = scalar_cnf_vector(earlier_residual, k)
                    right = scalar_cnf_vector(later_residual, k)
                    require(digest_packed(left, k) == saved["earlier_packed_sha256"], "earlier reconstructed digest")
                    require(digest_packed(right, k) == saved["later_packed_sha256"], "later reconstructed digest")
                    require(digest_packed(left ^ right, k) == saved["changed_packed_sha256"], "reconstructed delta digest")
                    changed = (left ^ right).bit_count()
                    require(changed == int(saved_delta_rows[case_id]["changed_assignments"]), "reconstructed delta count")
                    reconstructed_rows.append({"case_id": case_id, "k": k,
                                               "earlier_exact_source_reconstruction": True,
                                               "later_exact_source_reconstruction": True,
                                               "changed_assignments": changed})
            transition_rows.append({"transition_id": transition_id, "admitted": True,
                                    "source_witness_verified": True, "second_solver_refusal_confirmed": False,
                                    "direct_unit_certificates": 0, "exact_residuals_reconstructed": 6})
    require(len(endpoint_rows) == 240 and len(reconstructed_rows) == 120 and len(transition_rows) == 21, "source audit coverage mismatch")
    write_csv(output / "transition-source-reconstruction.csv", transition_rows)
    write_csv(output / "delta-source-reconstruction.csv", reconstructed_rows)
    with (output / "retrospective-joint-witnesses.jsonl").open("w", encoding="utf-8") as handle:
        for witness in joint_witnesses:
            handle.write(json.dumps(witness, sort_keys=True, separators=(",", ":")) + "\n")
    for item in inputs:
        require(sha(Path(item["path"])) == item["sha256"], "source payload changed during audit")
    summary = {"schema": "cm-fm-deep-source-audit/v1", "status": "passed", "official_payloads_rehashed_and_reparsed": 40,
               "endpoint_residuals_reconstructed_from_original_witnesses": len(endpoint_rows),
               "admitted_transition_witnesses_regenerated_and_saved": len(joint_witnesses),
               "delta_case_pairs_reconstructed_from_source": len(reconstructed_rows),
               "refusal_independently_confirmed_by_MiniSat22": 1,
               "direct_unit_contradiction_certificates": sum(row["direct_unit_certificates"] for row in transition_rows),
               "pysat_version": pysat.__version__, "python": sys.version,
               "historical_pysat_version": "1.8.dev24",
               "pysat_wrapper_version_matches_historical": pysat.__version__ == "1.8.dev24",
               "historical_joint_witnesses_were_missing": True,
               "independence_limit": "retrospective joint-witness regeneration uses CaDiCaL195 and original clause order, with wrapper version separately recorded; source parsing, mapping, conditioning and scalar checks are separate code; refusal also uses MiniSat22",
               "performance_claims_certified": False}
    write_json(output / "summary.json", summary)
    finalize(output, observed, runs)
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    audit(arguments.source.resolve(), arguments.output.resolve())
