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

def keep(*args):
    """
    Slice a sequence using standard Python slice semantics.
    Wraps the built-in slice() to make it callable in a pipeline.

    Arguments mirror Python's slice(stop), slice(start, stop),
    and slice(start, stop, step) exactly.

    Examples:
        pipe / cut(3)              # [:3]        first 3 elements
        pipe / cut(3, None)        # [3:]        skip first 3
        pipe / cut(1, 5)           # [1:5]       elements 1 to 4
        pipe / cut(1, 5, 2)        # [1:5:2]     every other element
        pipe / cut(None, None, -1) # [::-1]      reverse

    Note:
        cut() is a thin callable wrapper over the built-in slice().
        pipe / cut(1, 5) is equivalent to seq[slice(1, 5)] or seq[1:5].
        Works on any object that supports __getitem__ with a slice:
        lists, tuples, strings, numpy arrays.
    """
    s = slice(*args)
    return lambda v: v[s]

def twist(lists):
    """Zip parallel fork outputs into per-position groups.
        [[a1,a2,a3],[b1,b2,b3]] → [[a1,b1],[a2,b2],[a3,b3]]
        data > pipe / (pipe1 + pipe2) / twist
        data > pipe / (pipe1 + pipe2) / twist / flatten   # if you want flat
    """
    return [list(group) for group in zip(*lists)]

def named(keys):
    """Map a flat list to a dict using positional key names.
        [0.73, 0.61, 0.44] / named(["micro", "meso", "macro"])
        → {"micro": 0.73, "meso": 0.61, "macro": 0.44}
    """
    return lambda values: dict(zip(keys, values))

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

# ── Debugging  ────────────────────────────────────────────────────────────

def tap(func):
    """Call func as side effect, pass value through unchanged.
        pipe / tap(log_to_file) / tap(send_metric)
    """
    def _tap(value):
        func(value)
        return value
    return _tap