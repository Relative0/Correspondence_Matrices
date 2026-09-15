from pathlib import Path
import json

from scripts import cm_overnight_local_portfolio_audit as audit


def test_junit_cases_preserve_failure_error_skip_and_pass(tmp_path: Path) -> None:
    path = tmp_path / "junit.xml"
    path.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<testsuites><testsuite tests="4" failures="1" errors="1" skipped="1">
  <testcase classname="suite" name="pass" time="0.1" />
  <testcase classname="suite" name="fail" time="0.2"><failure message="no" /></testcase>
  <testcase classname="suite" name="error" time="0.3"><error>trace</error></testcase>
  <testcase classname="suite" name="skip" time="0"><skipped message="optional" /></testcase>
</testsuite></testsuites>
""",
        encoding="utf-8",
    )

    cases = audit.junit_cases(path)

    assert [case["outcome"] for case in cases] == [
        "passed",
        "failure",
        "error",
        "skipped",
    ]
    assert cases[1]["detail"] == "no"
    assert cases[2]["detail"] == "trace"
    assert sum(case["seconds"] for case in cases) == 0.6


def test_expected_refusals_match_the_supported_baseline_exclusions() -> None:
    assert len(audit.EXPECTED_COLLECTION_REFUSALS) == 8
    assert set(audit.EXPECTED_ALL_SKIPPED) == {
        "tests/test_bucket_cudd_reference.py"
    }
    assert sum("PyTorch" in reason for reason in audit.EXPECTED_COLLECTION_REFUSALS.values()) == 7
    assert audit.EXPECTED_COLLECTION_REFUSALS["tests/test_packed_io_campaign.py"] == (
        "the Unix resource module is unavailable on Windows"
    )


def test_manifest_verifier_detects_tampering(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence.txt"
    evidence.write_text("bound\n", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "files": [
                    {
                        "path": "evidence.txt",
                        "bytes": evidence.stat().st_size,
                        "sha256": audit.sha256(evidence),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    assert audit.verify_manifest(manifest, tmp_path)["status"] == "passed"
    evidence.write_text("tampered\n", encoding="utf-8")
    result = audit.verify_manifest(manifest, tmp_path)
    assert result["status"] == "failed"
    assert result["failures"] == [{"path": "evidence.txt", "reason": "size"}]
