"""
miniplumber.utils — plain functions that plug into pipelines with / or @

All utilities are dependency-free and work with any pipeline step.

    from miniplumber import pipe, flatten, sort, field, debug

    result = records > (
        pipe
        @ having(status="active")
        // field("name")
        / sort()
        / debug("sorted names")
    )
"""

# ── Flatten ───────────────────────────────────────────────────────────────────

def flatten(value):
    """Flatten one level of nesting.
        [[1,2],[3,4]] → [1,2,3,4]
        pipe // str.split / flatten
    """
    return [item for sublist in value for item in sublist]

def flatten_deep(value):
    """Flatten arbitrarily nested lists.
        [1,[2,[3,4]]] → [1,2,3,4]
        pipe / flatten_deep
    """
    def _flat(v):
        for x in v:
            if isinstance(x, (list, tuple)):
                yield from _flat(x)
            else:
                yield x
    return list(_flat(value))


# ── Sequence operations ───────────────────────────────────────────────────────

def sort(key=None, reverse=False):
    """Return a sorted list.
        pipe / sort()
        pipe / sort(key=len, reverse=True)
    """
    return lambda v: sorted(v, key=key, reverse=reverse)

def unique(value):
    """Deduplicate preserving order.
        pipe / unique
    """
    seen = set()
    return [x for x in value if not (x in seen or seen.add(x))]

def take(n):
    """Keep first n elements.
        pipe / take(3)
    """
    return lambda v: v[:n]

def drop(n):
    """Skip first n elements.
        pipe / drop(3)
    """
    return lambda v: v[n:]

def chunk(n):
    """Split into n-sized groups.
        [1,2,3,4,5] / chunk(2) → [[1,2],[3,4],[5]]
        pipe / chunk(2) // process_batch
    """
    return lambda v: [v[i:i+n] for i in range(0, len(v), n)]

def window(n):
    """Sliding windows of size n.
        [1,2,3,4] / window(2) → [(1,2),(2,3),(3,4)]
        pipe / window(2) // compute_delta
    """
    return lambda v: [tuple(v[i:i+n]) for i in range(len(v) - n + 1)]

def compact(value):
    """Remove falsy values (None, 0, "", [], False).
        pipe / compact
    """
    return [x for x in value if x]

def group(key):
    """Group elements into a dict by key function.
        words > pipe / group(len)   → {3: ["foo","bar"], 5: ["hello"]}
        pipe / group(lambda x: x["role"])
    """
    def _group(value):
        result = {}
        for x in value:
            result.setdefault(key(x), []).append(x)
        return result
    return _group


# ── Dict and object access ────────────────────────────────────────────────────

def field(key, default=None):
    """Extract a key from each dict. Use with //
        users > pipe // field("name")
        users > pipe // field("age", default=0)
    """
    return lambda x: x.get(key, default)

def attr(name, default=None):
    """Extract an attribute from each object. Use with //
        objects > pipe // attr("created_at")
        objects > pipe // attr("name", default="unknown")
    """
    return lambda x: getattr(x, name, default)


# ── Predicates for @ ──────────────────────────────────────────────────────────

def equals(value):
    """Keep elements equal to value.
        pipe @ equals("cat")
        pipe @ equals(42)
    """
    return lambda x: x == value

def instance(type_):
    """Keep elements of a given type.
        pipe @ instance(str)
        pipe @ instance(int)
    """
    return lambda x: isinstance(x, type_)

def between(lo, hi):
    """Keep elements between lo and hi inclusive.
        pipe @ between(18, 65)
    """
    return lambda x: lo <= x <= hi

def nonzero(x):
    """Keep truthy values.
        pipe @ nonzero
    """
    return bool(x)

def matching(pattern):
    """Keep elements containing a substring or matching a regex.
        pipe @ matching("ing")
        pipe @ matching(r"^\\d+$")
    """
    import re  # pylint: disable=import-outside-toplevel
    if isinstance(pattern, str):
        return lambda x: pattern in x
    return lambda x: bool(re.search(pattern, x))

def having(**kwargs):
    """Keep dicts containing all given key/value pairs.
        pipe @ having(status="active", role="admin")
    """
    return lambda x: all(x.get(k) == v for k, v in kwargs.items())


# ── Debugging ─────────────────────────────────────────────────────────────────

def debug(label=""):
    """Print value mid-pipeline and pass through unchanged.
        pipe / debug("after flatten") // str.upper
    """
    def _debug(value):
        print(f"[{label}]  {value}" if label else str(value))
        return value
    return _debug

def tap(func):
    """Call func as side effect, pass value through unchanged.
        pipe / tap(log_to_file) / tap(send_metric)
    """
    def _tap(value):
        func(value)
        return value
    return _tap

def capture(store, key):
    """Snapshot a mid-pipeline value into a dict, pass through unchanged.
        captured = {}
        result = data > pipe // str.split / capture(captured, "words") / flatten
        print(captured["words"])
    """
    def _capture(value):
        store[key] = value
        return value
    return _capture


# ── Error handling ────────────────────────────────────────────────────────────

def safe(fallback):
    """Wrap a function — return fallback on any exception.
        pipe // safe(0)(int)          replace failed int() with 0
        pipe / safe([])(parse_json)   return [] if parse fails
    """
    def wrap(func):
        def guarded(value):
            try:
                return func(value)
            except Exception:  # pylint: disable=broad-exception-caught
                return fallback
        guarded.__name__ = getattr(func, '__name__', repr(func))
        return guarded
    return wrap
