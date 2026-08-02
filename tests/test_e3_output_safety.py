"""Output-overwrite safety of the corrected E3 driver (2026-08-02, F5).

The superseded driver wrote fixed archived filenames, so re-running it
destroyed the evidence it was meant to reproduce. The corrected driver must
refuse to touch existing outputs unless ``--overwrite`` is passed.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_DRIVER = (Path(__file__).resolve().parents[1] / "deliverables_n22_24"
           / "cm_gap_e3_corrected_2026_08_02.py")


def _load_driver():
    spec = importlib.util.spec_from_file_location("e3_corrected_driver", _DRIVER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def driver():
    return _load_driver()


def test_default_refuses_existing_corpus(tmp_path, driver):
    (tmp_path / driver.CORPUS_NAME).write_text("archived evidence", encoding="utf-8")
    with pytest.raises(SystemExit, match="refusing to overwrite"):
        driver.resolve_outputs(tmp_path, overwrite=False)
    # the archived file is untouched
    assert (tmp_path / driver.CORPUS_NAME).read_text(encoding="utf-8") == "archived evidence"


def test_default_refuses_existing_results_and_summary(tmp_path, driver):
    (tmp_path / driver.RESULTS_NAME).write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit, match=driver.RESULTS_NAME):
        driver.resolve_outputs(tmp_path, overwrite=False)
    (tmp_path / driver.RESULTS_NAME).unlink()
    (tmp_path / driver.SUMMARY_NAME).write_text("x", encoding="utf-8")
    with pytest.raises(SystemExit, match=driver.SUMMARY_NAME):
        driver.resolve_outputs(tmp_path, overwrite=False)


def test_fresh_directory_is_created_and_accepted(tmp_path, driver):
    out = tmp_path / "new" / "nested"
    targets = driver.resolve_outputs(out, overwrite=False)
    assert out.is_dir()
    assert set(targets) == {"corpus", "results", "summary"}
    assert all(not p.exists() for p in targets.values())


def test_overwrite_flag_permits_replacement(tmp_path, driver):
    (tmp_path / driver.CORPUS_NAME).write_text("old", encoding="utf-8")
    targets = driver.resolve_outputs(tmp_path, overwrite=True)
    assert targets["corpus"] == tmp_path / driver.CORPUS_NAME


def test_loading_corpus_skips_corpus_target(tmp_path, driver):
    """When measuring from an existing corpus, only results/summary are
    outputs; a corpus file already in out-dir must not block the run."""
    (tmp_path / driver.CORPUS_NAME).write_text("input corpus", encoding="utf-8")
    targets = driver.resolve_outputs(tmp_path, overwrite=False, writing_corpus=False)
    assert "corpus" not in targets
