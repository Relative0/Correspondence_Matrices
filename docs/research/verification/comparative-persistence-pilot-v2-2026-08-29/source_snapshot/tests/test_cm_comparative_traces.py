"""Trace provenance refuses generated or reconstructed data as natural."""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import tempfile
import unittest

from cmbench.comparative.contracts import canonical_bytes
from cmbench.comparative import traces
from scripts.cm_comparative_task_pilot import traces as task_traces


def scenario() -> dict:
    return {
        "id": "trace-k6",
        "k": 6,
        "feature_names": [f"x{i}" for i in range(6)],
        "versions": [
            {"id": "base", "clauses": [[1, -6], [-1, 6]]},
            {"id": "duplicate", "clauses": [[1, -6], [-1, 6], [1, -6]]},
            {"id": "changed", "clauses": [[1, -6], [-1, 6], [-1]]},
        ],
        "source": {"kind": "synthetic", "purpose": "trace_schema_control"},
    }


SCENARIOS = {"case-1": scenario()}


def observed_corpus(kind="observed_natural") -> dict:
    return {
        "schema": traces.CORPUS_SCHEMA,
        "corpus_id": "observed-1",
        "source": {
            "kind": "observed_dataset" if kind == "observed_natural" else "public_event_log",
            "uri": "https://example.org/public-traces.jsonl",
            "content_sha256": hashlib.sha256(b"public-fixture").hexdigest(),
            "license": "CC-BY-4.0",
            "privacy": "public_nonpersonal",
            "captured_start": "2026-01-01T00:00:00Z",
            "captured_end": "2026-01-02T00:00:00Z",
        },
        "scenarios": [
            {
                "scenario_id": "case-1",
                "scenario_sha256": hashlib.sha256(canonical_bytes(scenario())).hexdigest(),
            }
        ],
        "traces": [
            {
                "trace_id": "trace-1",
                "scenario_id": "case-1",
                "task": "partial_context",
                "events": [{"version": 0, "assumptions": []}, {"version": 1, "assumptions": [-1]}],
                "provenance": {
                    "kind": kind,
                    "selection": "predeclared",
                    "source_record_ids": ["record-1", "record-2"],
                    "generator": None,
                },
            }
        ],
    }


class TraceProvenanceTests(unittest.TestCase):
    def test_generated_bridge_controls_cover_tasks_but_cannot_claim_natural(self):
        corpus = traces.generated_control_corpus(
            corpus_id="generated-bridge-1", scenarios=SCENARIOS, trace_map=task_traces()
        )
        audit = traces.validate_corpus(corpus, SCENARIOS)
        self.assertEqual(audit["trace_count"], 6)
        self.assertEqual(len(audit["tasks_covered"]), 6)
        self.assertEqual(audit["natural_trace_count"], 0)
        self.assertFalse(audit["natural_claim_permitted"])

    def test_observed_public_records_can_claim_natural(self):
        audit = traces.validate_corpus(observed_corpus(), SCENARIOS)
        self.assertEqual(audit["natural_trace_count"], 1)
        self.assertTrue(audit["natural_claim_permitted"])
        self.assertTrue(audit["publishable"])

    def test_reconstructed_public_events_remain_non_natural(self):
        audit = traces.validate_corpus(observed_corpus("reconstructed_public_events"), SCENARIOS)
        self.assertEqual(audit["provenance_counts"], {"reconstructed_public_events": 1})
        self.assertFalse(audit["natural_claim_permitted"])

    def test_natural_claim_refuses_missing_records_outcome_selection_and_wrong_source(self):
        base = observed_corpus()
        variants = []
        changed = copy.deepcopy(base)
        changed["traces"][0]["provenance"]["source_record_ids"] = []
        variants.append(changed)
        changed = copy.deepcopy(base)
        changed["traces"][0]["provenance"]["selection"] = "outcome_selected"
        variants.append(changed)
        changed = copy.deepcopy(base)
        changed["source"]["kind"] = "public_event_log"
        variants.append(changed)
        changed = copy.deepcopy(base)
        changed["source"]["uri"] = "file:///private/session.jsonl"
        variants.append(changed)
        changed = copy.deepcopy(base)
        changed["source"]["privacy"] = "synthetic_no_person_data"
        variants.append(changed)
        for item in variants:
            with self.subTest(item=item), self.assertRaises(ValueError):
                traces.validate_corpus(item, SCENARIOS)

    def test_trace_literals_scenario_hashes_and_duplicate_json_are_strict(self):
        base = observed_corpus()
        variants = []
        changed = copy.deepcopy(base)
        changed["traces"][0]["events"][0]["assumptions"] = [True]
        variants.append(changed)
        changed = copy.deepcopy(base)
        changed["scenarios"][0]["scenario_sha256"] = "0" * 64
        variants.append(changed)
        changed = copy.deepcopy(base)
        changed["traces"][0]["trace_id"] = base["traces"][0]["trace_id"]
        changed["traces"].append(copy.deepcopy(changed["traces"][0]))
        variants.append(changed)
        for item in variants:
            with self.subTest(item=item), self.assertRaises(ValueError):
                traces.validate_corpus(item, SCENARIOS)

        with tempfile.TemporaryDirectory(prefix="cm-traces-") as temporary:
            path = Path(temporary) / "corpus.json"
            path.write_bytes(canonical_bytes(base))
            loaded, audit = traces.load_corpus(path, SCENARIOS)
            self.assertEqual(loaded, base)
            self.assertTrue(audit["natural_claim_permitted"])
            path.write_bytes(canonical_bytes(base) + b"\n")
            with self.assertRaises(ValueError):
                traces.load_corpus(path, SCENARIOS)


if __name__ == "__main__":
    unittest.main()
