"""
pype.core — the Pipeline class and pipe sentinel.
"""


# ── Step executors ────────────────────────────────────────────────────────────

def _exec_pass(value, func):
    return func(value)

def _exec_map(value, func):
    return [func(x) for x in value]

def _exec_filter(value, func):
    return [x for x in value if func(x)]

def _exec_fork(value, pipelines):
    return [value > p for p in pipelines]

_run = {
    'pass':   _exec_pass,
    'map':    _exec_map,
    'filter': _exec_filter,
    'fork':   _exec_fork,
}


# ── Pipeline ──────────────────────────────────────────────────────────────────

class Pipeline:
    """Lazy functional pipeline. Build with operators, fire with >."""

    __slots__ = ('_steps',)

    def __init__(self, steps=()):
        self._steps = tuple(steps)

    def _add(self, op, arg=None):
        return Pipeline(self._steps + ((op, arg),))

    def __truediv__(self, other):
        """/  : pass whole value to func  |  compose two pipelines"""
        if isinstance(other, Pipeline):
            return Pipeline(self._steps + other._steps)
        if callable(other):
            return self._add('pass', other)
        raise TypeError(f"/ expects a callable or Pipeline — got {type(other).__name__}")

    def __floordiv__(self, func):
        """// : map func over each element  (one in → one out, same length)"""
        if not callable(func):
            raise TypeError(f"// expects a callable — got {type(func).__name__}")
        return self._add('map', func)

    def __matmul__(self, func):
        """@ func : keep elements where func(x) is truthy"""
        if not callable(func):
            raise TypeError(f"@ expects a callable — got {type(func).__name__}")
        return self._add('filter', func)

    def __add__(self, other):
        """+  : fork — run same input through both pipelines, return [a, b]
               always wrap in parens:  /  (pipe_a + pipe_b)  /
        """
        if not isinstance(other, Pipeline):
            raise TypeError(f"+ expects a Pipeline — got {type(other).__name__}")
        if self._steps and self._steps[-1][0] == 'fork':
            pipelines = self._steps[-1][1] + (other,)
            return Pipeline(self._steps[:-1] + (('fork', pipelines),))
        return Pipeline((('fork', (self, other)),))

    def __lt__(self, value):
        """value > pipe  →  fires the pipeline, returns raw value"""
        for i, (op, arg) in enumerate(self._steps):
            try:
                value = _run[op](value, arg)
            except Exception as e:
                raise RuntimeError(
                    f"\npype: step {i+1}/{len(self._steps)} failed"
                    f"\n  op    : {op}"
                    f"\n  func  : {getattr(arg, '__name__', repr(arg))}"
                    f"\n  input : {repr(value)[:120]}"
                ) from e
        return value

    def __repr__(self):
        return f"Pipeline({list(self._steps)})"

pipe     = Pipeline()
