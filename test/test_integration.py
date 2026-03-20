# pylint: disable=pointless-statement
# pylint: disable=expression-not-assigned

"""Integration tests — full pipelines combining core and utils."""

import statistics
from pype import pipe
from pype.utils import (
    flatten,
    sort,
    having,
    field,
    instance,
    debug,
    capture,
    safe,
    group)

# ── Classic map / flatten / filter / reduce ───────────────────────────────────

def test_map_flatten_filter_reduce():
    sentences = ["hello world", "foo bar baz", "hi"]
    result = sentences > (
        pipe
        // str.split
        / flatten
        @ (lambda w: len(w) > 2)
        / sorted
        / " ".join
    )
    assert result == "bar baz foo hello world"

def test_word_processing_pipeline():
    def has_vowel(word): return any(v in word for v in "aeiou")

    tokenize = pipe // str.split / flatten
    clean    = pipe // str.strip // str.lower
    voiced   = pipe @ has_vowel
    join     = pipe / " ".join

    process  = tokenize / clean / voiced / join

    assert (["  Hello World  "] > process) == "hello world"
    assert (["  FOO  "] > process) == "foo"

def test_number_pipeline():
    def square(x): return x ** 2
    def is_even(x): return x % 2 == 0

    result = [1, 2, 3, 4, 5, 6] > (
        pipe
        @ is_even
        // square
        / sum
    )
    assert result == 56   # 4 + 16 + 36


# ── Named pipelines ───────────────────────────────────────────────────────────

def test_named_pipelines_compose():
    clean = pipe // str.strip // str.lower
    shout = pipe // str.upper

    process = clean / shout
    result = ["  hello  ", "  world  "] > process
    assert result == ["HELLO", "WORLD"]

def test_named_pipeline_reusable():
    normalize = pipe // str.strip // str.lower / sort()

    result_a = ["  banana  ", "  apple  "] > normalize
    result_b = ["  zebra  ", "  mango  "] > normalize

    assert result_a == ["apple", "banana"]
    assert result_b == ["mango", "zebra"]

def test_named_pipeline_testable_independently():
    tokenize = pipe // str.split / flatten
    clean    = pipe // str.strip // str.lower

    assert (["hello world"] > tokenize) == ["hello", "world"]
    assert (["  HELLO  "]   > clean)    == ["hello"]


# ── Fork and merge ────────────────────────────────────────────────────────────

def test_fork_two_branches():
    data = [2, 4, 4, 4, 5, 5, 7, 9]
    result = data > pipe / (
        pipe / statistics.mean +
        pipe / statistics.median
    )
    assert result == [5.0, 4.5]

def test_fork_three_branches():
    data = [1, 2, 3, 4, 5]
    result = data > pipe / (
        pipe / min  +
        pipe / max  +
        pipe / sum
    )
    assert result == [1, 5, 15]

def test_fork_then_merge():
    def as_dict(pair):
        return {"mean": pair[0], "stdev": pair[1]}

    data = [2, 4, 4, 4, 5, 5, 7, 9]
    result = data > pipe / (
        pipe / statistics.mean  +
        pipe / statistics.stdev
    ) / as_dict

    assert result["mean"] == 5.0
    assert round(result["stdev"], 1) == 2.1


# ── Identity in forks ─────────────────────────────────────────────────────────

def test_identity_preserves_value_in_fork():
    def double(x): return x * 2
    result = 5 > pipe / (pipe / double + pipe)
    assert result == [10, 5]

def test_identity_preserves_fork_point_not_start():
    def add_one(x): return x + 1
    branch = pipe / add_one / add_one

    result = 0 > pipe / add_one / (branch + pipe)
    assert result == [3, 1]   # branch: 1+1+1=3, identity gives 1 (after first add_one)

def test_identity_named_pattern():
    process  = pipe // str.upper
    preserve = pipe

    result = ["hello", "world"] > pipe / (process + preserve)
    assert result == [["HELLO", "WORLD"], ["hello", "world"]]


# ── Dict / record pipelines ───────────────────────────────────────────────────

def test_filter_and_extract_from_records():
    users = [
        {"name": "Alice", "role": "admin",  "active": True},
        {"name": "Bob",   "role": "user",   "active": False},
        {"name": "Carol", "role": "admin",  "active": True},
    ]
    result = users > (
        pipe
        @ having(role="admin", active=True)
        // field("name")
        / sort()
    )
    assert result == ["Alice", "Carol"]

def test_type_filter_on_mixed_list():
    mixed = [1, "hello", 2, None, "world", 3, True]
    strings = mixed > pipe @ instance(str)
    numbers = mixed > pipe @ instance(int)
    assert strings == ["hello", "world"]
    assert numbers == [1, 2, 3, True]


# ── Debugging mid-pipeline ────────────────────────────────────────────────────

def test_debug_does_not_affect_result():
    result = [1, 2, 3] > pipe / debug("nums") / sum
    assert result == 6

def test_capture_mid_pipeline():
    store = {}
    result = ["hello world", "foo bar"] > (
        pipe
        // str.split
        / capture(store, "split")
        / flatten
        // str.upper
    )
    assert store["split"] == [["hello", "world"], ["foo", "bar"]]
    assert result == ["HELLO", "WORLD", "FOO", "BAR"]


# ── Error handling ────────────────────────────────────────────────────────────

def test_safe_in_mixed_list_pipeline():
    result = ["1", "2", "oops", "4"] > pipe // safe(0)(int)
    assert result == [1, 2, 0, 4]

def test_error_propagates_with_context():
    import pytest
    with pytest.raises(RuntimeError) as exc_info:
        ["hello"] > pipe // int
    assert "step" in str(exc_info.value)
    assert exc_info.value.__cause__ is not None


# ── Real-world style pipelines ────────────────────────────────────────────────

def test_log_parsing_pipeline():
    logs = [
        "ERROR: disk full",
        "INFO: started",
        "ERROR: out of memory",
        "DEBUG: loop iteration",
        "ERROR: timeout",
    ]

    def parse(line):
        level, _, msg = line.partition(": ")
        return {"level": level, "msg": msg}

    def is_error(record): return record["level"] == "ERROR"

    result = logs > (
        pipe
        // parse
        @ is_error
        // field("msg")
        / sort()
    )
    assert result == ["disk full", "out of memory", "timeout"]

def test_text_frequency_pipeline():
    text = ["the cat sat on the mat", "the cat is fat"]

    result = text > (
        pipe
        // str.split
        / flatten
        / group(lambda w: w)
        / (lambda d: {k: len(v) for k, v in d.items()})
    )
    assert result["the"] == 3
    assert result["cat"] == 2
    assert result["mat"] == 1
