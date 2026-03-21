# pylint: disable=pointless-statement
# pylint: disable=expression-not-assigned
# pylint: disable=missing-function-docstring
# pylint: disable=missing-class-docstring



"""Tests for pype/utils.py — all utility functions."""

from miniplumber import pipe
from miniplumber.utils import (
    flatten, flatten_deep,
    sort, unique, compact, take, drop, chunk, window, group,
    field, attr,
    equals, instance, between, nonzero, matching, having,
    debug, tap, capture,
    safe,
)


# ── Flatten ───────────────────────────────────────────────────────────────────

def test_flatten_one_level():
    assert flatten([[1, 2], [3, 4]]) == [1, 2, 3, 4]

def test_flatten_does_not_go_deep():
    assert flatten([[1, [2]], [3]]) == [1, [2], 3]

def test_flatten_empty():
    assert flatten([]) == [] #pylint: disable=use-implicit-booleaness-not-comparison

def test_flatten_deep_arbitrary_nesting():
    assert flatten_deep([1, [2, [3, [4]]]]) == [1, 2, 3, 4]

def test_flatten_deep_mixed():
    assert flatten_deep([[1, 2], [3, [4, 5]]]) == [1, 2, 3, 4, 5]

def test_flatten_in_pipeline():
    result = ["hello world", "foo bar"] > pipe // str.split / flatten
    assert result == ["hello", "world", "foo", "bar"]


# ── Sort ─────────────────────────────────────────────────────────────────────

def test_sort_default():
    assert sort()([3, 1, 2]) == [1, 2, 3]

def test_sort_by_key():
    assert sort(key=len)(["bb", "a", "ccc"]) == ["a", "bb", "ccc"]

def test_sort_reverse():
    assert sort(reverse=True)([1, 2, 3]) == [3, 2, 1]

def test_sort_does_not_mutate():
    original = [3, 1, 2]
    sort()(original)
    assert original == [3, 1, 2]


# ── Unique ────────────────────────────────────────────────────────────────────

def test_unique_removes_duplicates():
    assert unique([1, 2, 1, 3, 2]) == [1, 2, 3]

def test_unique_preserves_order():
    assert unique(["b", "a", "b", "c"]) == ["b", "a", "c"]

def test_unique_empty():
    assert unique([]) == []


# ── Compact ───────────────────────────────────────────────────────────────────

def test_compact_removes_falsy():
    assert compact([1, None, 0, "hello", "", False, []]) == [1, "hello"]

def test_compact_all_truthy():
    assert compact([1, 2, 3]) == [1, 2, 3]

def test_compact_all_falsy():
    assert compact([None, 0, False]) == []


# ── Take / Drop ───────────────────────────────────────────────────────────────

def test_take_first_n():
    assert take(3)([1, 2, 3, 4, 5]) == [1, 2, 3]

def test_take_more_than_length():
    assert take(10)([1, 2, 3]) == [1, 2, 3]

def test_take_zero():
    assert take(0)([1, 2, 3]) == []

def test_drop_first_n():
    assert drop(2)([1, 2, 3, 4, 5]) == [3, 4, 5]

def test_drop_more_than_length():
    assert drop(10)([1, 2, 3]) == []

def test_drop_zero():
    assert drop(0)([1, 2, 3]) == [1, 2, 3]


# ── Chunk / Window ────────────────────────────────────────────────────────────

def test_chunk_even():
    assert chunk(2)([1, 2, 3, 4]) == [[1, 2], [3, 4]]

def test_chunk_with_remainder():
    assert chunk(2)([1, 2, 3, 4, 5]) == [[1, 2], [3, 4], [5]]

def test_window_size_two():
    assert window(2)([1, 2, 3, 4]) == [(1, 2), (2, 3), (3, 4)]

def test_window_size_three():
    assert window(3)([1, 2, 3, 4]) == [(1, 2, 3), (2, 3, 4)]

def test_window_exact_size():
    assert window(3)([1, 2, 3]) == [(1, 2, 3)]


# ── Group ─────────────────────────────────────────────────────────────────────

def test_group_by_len():
    result = group(len)(["a", "bb", "cc", "ddd"])
    assert result == {1: ["a"], 2: ["bb", "cc"], 3: ["ddd"]}

def test_group_preserves_order():
    result = group(lambda x: x % 2)([1, 2, 3, 4, 5])
    assert result == {1: [1, 3, 5], 0: [2, 4]}


# ── Field / Attr ──────────────────────────────────────────────────────────────

def test_field_extracts_key():
    users = [{"name": "Alice"}, {"name": "Bob"}]
    assert list(map(field("name"), users)) == ["Alice", "Bob"]

def test_field_missing_key_returns_default():
    users = [{"name": "Alice"}, {}]
    assert list(map(field("name", default="unknown"), users)) == ["Alice", "unknown"]

def test_field_default_is_none():
    assert field("x")({"y": 1}) is None

def test_field_in_pipeline():
    users = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
    result = users > pipe // field("name")
    assert result == ["Alice", "Bob"]

def test_attr_extracts_attribute():
    class Obj:
        def __init__(self, x):
            self.x = x
    objs = [Obj(1), Obj(2)]
    assert list(map(attr("x"), objs)) == [1, 2]

def test_attr_missing_returns_default():
    class Obj:
        pass
    assert attr("x", default=0)(Obj()) == 0


# ── Predicates ────────────────────────────────────────────────────────────────

def test_equals_match():
    assert equals("cat")("cat") is True

def test_equals_no_match():
    assert equals("cat")("dog") is False

def test_equals_in_pipeline():
    result = ["cat", "dog", "cat"] > pipe @ equals("cat")
    assert result == ["cat", "cat"]

def test_instance_match():
    assert instance(str)("hello") is True

def test_instance_no_match():
    assert instance(str)(42) is False

def test_instance_in_pipeline():
    result = [1, "hello", 2, "world"] > pipe @ instance(str)
    assert result == ["hello", "world"]

def test_between_inclusive():
    assert between(1, 5)(1) is True
    assert between(1, 5)(5) is True
    assert between(1, 5)(3) is True

def test_between_out_of_range():
    assert between(1, 5)(0) is False
    assert between(1, 5)(6) is False

def test_nonzero_truthy():
    assert nonzero(1) is True
    assert nonzero("hello") is True

def test_nonzero_falsy():
    assert nonzero(0) is False
    assert nonzero("") is False
    assert nonzero(None) is False

def test_matching_substring():
    pred = matching("ing")
    assert pred("running") is True
    assert pred("walked") is False

def test_matching_regex():
    import re # pylint: disable=import-outside-toplevel
    pred = matching(re.compile(r"^\d+$"))
    assert pred("123") is True
    assert pred("abc") is False

def test_having_single_kwarg():
    pred = having(status="active")
    assert pred({"status": "active", "name": "Alice"}) is True
    assert pred({"status": "inactive"}) is False

def test_having_multiple_kwargs():
    pred = having(status="active", role="admin")
    assert pred({"status": "active", "role": "admin"}) is True
    assert pred({"status": "active", "role": "user"}) is False


# ── Debugging ─────────────────────────────────────────────────────────────────

def test_debug_passes_value_through():
    result = [1, 2, 3] > pipe / debug("test")
    assert result == [1, 2, 3]

def test_debug_prints_label(capsys):
    [1, 2, 3] > pipe / debug("mylist")
    captured = capsys.readouterr()
    assert "mylist" in captured.out
    assert "[1, 2, 3]" in captured.out

def test_debug_no_label(capsys):
    [1, 2, 3] > pipe / debug()
    captured = capsys.readouterr()
    assert "[1, 2, 3]" in captured.out

def test_tap_calls_func_as_side_effect():
    calls = []
    result = [1, 2, 3] > pipe / tap(calls.append)
    assert calls == [[1, 2, 3]]
    assert result == [1, 2, 3]

def test_tap_passes_value_unchanged():
    result = "hello" > pipe / tap(lambda x: None)
    assert result == "hello"

def test_capture_snapshots_value():
    store = {}
    result = [1, 2, 3] > pipe / capture(store, "nums") / len
    assert store["nums"] == [1, 2, 3]
    assert result == 3

def test_capture_does_not_alter_value():
    store = {}
    result = "hello" > pipe / capture(store, "word")
    assert result == "hello"


# ── Safe ──────────────────────────────────────────────────────────────────────

def test_safe_returns_fallback_on_exception():
    guarded = safe(0)(int)
    assert guarded("oops") == 0

def test_safe_passes_through_on_success():
    guarded = safe(0)(int)
    assert guarded("42") == 42

def test_safe_in_pipeline():
    result = ["1", "2", "oops", "4"] > pipe // safe(0)(int)
    assert result == [1, 2, 0, 4]

def test_safe_preserves_function_name():
    guarded = safe(0)(int)
    assert guarded.__name__ == "int"
