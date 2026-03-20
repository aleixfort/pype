# pylint: disable=pointless-statement
# pylint: disable=missing-function-docstring


"""Tests for pype/core.py — Pipeline class and pipe sentinel."""
import pytest
from pype import pipe

# ── / pass ────────────────────────────────────────────────────────────────────

def test_pass_applies_function():
    result = [1, 2, 3] > pipe / len
    assert result == 3

def test_pass_chains_functions():
    result = ["hello", "world"] > pipe / sorted / list
    assert result == ["hello", "world"]

def test_pass_with_builtin():
    result = ["hello", "world"] > pipe / " ".join
    assert result == "hello world"


# ── / compose ─────────────────────────────────────────────────────────────────

def test_compose_two_pipelines():
    clean = pipe // str.strip
    upper = pipe // str.upper
    result = ["  hello  "] > clean / upper
    assert result == ["HELLO"]

def test_compose_three_pipelines():
    a = pipe // str.strip
    b = pipe // str.lower
    c = pipe // str.upper
    result = ["  Hello  "] > a / b / c
    assert result == ["HELLO"]

def test_compose_preserves_order():
    first  = pipe / (lambda v: v + [1])
    second = pipe / (lambda v: v + [2])
    result = [] > first / second #pylint: disable=use-implicit-booleaness-not-comparison
    assert result == [1, 2]


# ── // map ────────────────────────────────────────────────────────────────────

def test_map_applies_to_each():
    result = ["hello", "world"] > pipe // str.upper
    assert result == ["HELLO", "WORLD"]

def test_map_preserves_length():
    result = [1, 2, 3, 4] > pipe // str
    assert len(result) == 4

def test_map_with_def_function():
    def double(x):
        return x * 2
    result = [1, 2, 3] > pipe // double
    assert result == [2, 4, 6]

def test_map_chained():
    result = ["  hello  ", "  world  "] > pipe // str.strip // str.upper
    assert result == ["HELLO", "WORLD"]


# ── @ filter ──────────────────────────────────────────────────────────────────

def test_filter_by_predicate():
    def is_long(w):
        return len(w) > 3
    result = ["hi", "hello", "world", "ok"] > pipe @ is_long
    assert result == ["hello", "world"]

def test_filter_with_builtin():
    result = ["HELLO", "world", "FOO"] > pipe @ str.isupper
    assert result == ["HELLO", "FOO"]

def test_filter_returns_empty_when_none_match():
    result = [1, 2, 3] > pipe @ (lambda x: x > 10)
    assert result == []

def test_filter_returns_all_when_all_match():
    result = [1, 2, 3] > pipe @ (lambda x: x > 0)
    assert result == [1, 2, 3]


# ── + fork ────────────────────────────────────────────────────────────────────

def test_fork_two_branches():
    result = [1, 2, 3] > pipe / (pipe / len + pipe / sum)
    assert result == [3, 6]

def test_fork_three_branches():
    result = [1, 2, 3] > pipe / (pipe / len + pipe / sum + pipe / list)
    assert result == [3, 6, [1, 2, 3]]

def test_fork_branches_are_independent():
    upper = pipe // str.upper
    lower = pipe // str.lower
    result = ["Hello"] > pipe / (upper + lower)
    assert result == [["HELLO"], ["hello"]]

def test_fork_then_merge():
    def merge(pair):
        return pair[0] + pair[1]
    result = [1, 2, 3] > pipe / (pipe / list + pipe / list) / merge
    assert result == [1, 2, 3, 1, 2, 3]


# ── identity ─────────────────────────────────────────────────────────────────

def test_identity_in_fork():
    def double(x):
        return x * 2
    result = 5 > pipe / (pipe/double + pipe)
    assert result == [10, 5]

def test_identity_preserves_fork_point():
    def add_one(x):
        return x + 1
    branch = pipe / add_one / add_one
    result = 0 > pipe / add_one / (branch + pipe)
    assert result == [3, 1]   # branch: 1+1+1=3, identity: 1


# ── > fire ────────────────────────────────────────────────────────────────────

def test_fire_returns_raw_value():
    result = "hello" > pipe / str.upper
    assert result == "HELLO"
    assert isinstance(result, str)

def test_fire_empty_pipeline_returns_input():
    result = 42 > pipe
    assert result == 42

def test_pipeline_is_lazy():
    calls = []
    def track(v):
        calls.append(v)
        return v
    p = pipe / track
    assert not calls     # not called yet
    "x" > p
    assert calls == ["x"]   # called only on fire


# ── Error messages ────────────────────────────────────────────────────────────

def test_error_includes_step_number():
    with pytest.raises(RuntimeError, match="step 1/1"):
        "hello" > pipe / int

def test_error_includes_op():
    with pytest.raises(RuntimeError, match="op"):
        "hello" > pipe / int

def test_error_includes_input():
    with pytest.raises(RuntimeError, match="hello"):
        "hello" > pipe / int

def test_error_chains_original_exception():
    with pytest.raises(RuntimeError) as exc_info:
        "hello" > pipe / int
    assert exc_info.value.__cause__ is not None

def test_error_correct_step_number_in_chain():
    with pytest.raises(RuntimeError, match="step 2/3"):
        ["1", "oops", "3"] > pipe / list / int / str


# ── Type errors ───────────────────────────────────────────────────────────────

def test_pass_rejects_non_callable():
    with pytest.raises(TypeError):
        pipe / 42

def test_map_rejects_non_callable():
    with pytest.raises(TypeError):
        pipe // 42

def test_filter_rejects_non_callable():
    with pytest.raises(TypeError):
        pipe @ 42

def test_fork_rejects_non_pipeline():
    with pytest.raises(TypeError):
        pipe + 42
