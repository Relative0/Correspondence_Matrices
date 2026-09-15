import pytest

from cm_ir import (
    evaluation_defaults_scope,
    get_evaluation_defaults,
    preserve_evaluation_defaults,
    set_flat_eval_default,
    set_words_eval_default,
)


def test_evaluation_defaults_scope_alternates_and_restores():
    set_flat_eval_default(False)
    set_words_eval_default(False)
    with evaluation_defaults_scope(flat_eval=True, words_eval=False):
        assert get_evaluation_defaults() == (True, False)
        with evaluation_defaults_scope(flat_eval=False, words_eval=True):
            assert get_evaluation_defaults() == (False, True)
        assert get_evaluation_defaults() == (True, False)
    assert get_evaluation_defaults() == (False, False)


def test_evaluation_defaults_scope_restores_after_exception():
    set_flat_eval_default(False)
    set_words_eval_default(True)
    with pytest.raises(RuntimeError):
        with evaluation_defaults_scope(flat_eval=True, words_eval=False):
            raise RuntimeError("boom")
    assert get_evaluation_defaults() == (False, True)
    set_words_eval_default(False)


def test_preserve_defaults_makes_reentrant_entry_point_isolated():
    set_flat_eval_default(False)
    set_words_eval_default(False)

    @preserve_evaluation_defaults
    def simulated_cli(flat, words, fail=False):
        set_flat_eval_default(flat)
        set_words_eval_default(words)
        assert get_evaluation_defaults() == (flat, words)
        if fail:
            raise ValueError("cli failure")

    simulated_cli(True, False)
    assert get_evaluation_defaults() == (False, False)
    simulated_cli(False, True)
    assert get_evaluation_defaults() == (False, False)
    with pytest.raises(ValueError):
        simulated_cli(True, True, fail=True)
    assert get_evaluation_defaults() == (False, False)
