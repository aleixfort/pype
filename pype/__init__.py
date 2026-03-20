"""
pype — a minimal functional pipeline for Python

    from pype import pipe, flatten, field, sort, debug

    result = records > (
        pipe
        @ having(status="active")
        // field("name")
        / sort()
        / " ".join
    )

Operators  (/ // @ + are same precedence — always left-to-right):

    /   pass whole value to func, or compose two pipelines
    //  map func over each element          (one in → one out)
    @   filter elements  (keep where func(x) is truthy)
    +   fork into parallel pipelines        /  (pipe_a + pipe_b)  /
    >   fire the pipeline, return raw value

See README.md for full documentation.
"""

from pype.core import pipe, Pipeline

from pype.utils import (
    # flatten
    flatten,
    flatten_deep,
    # sequence
    sort,
    unique,
    take,
    drop,
    chunk,
    window,
    compact,
    group,
    # dict and object access
    field,
    attr,
    # predicates
    equals,
    instance,
    between,
    nonzero,
    matching,
    having,
    # debugging
    debug,
    tap,
    capture,
    # error handling
    safe,
)

__all__ = [
    # core
    'pipe',
    'Pipeline',
     # flatten
    'flatten',
    'flatten_deep',
    # sequence
    'sort',
    'unique',
    'take',
    'drop',
    'chunk',
    'window',
    'compact',
    'group',
    # dict and object access
    'field',
    'attr',
    # predicates
    'equals',
    'instance',
    'between',
    'nonzero',
    'matching',
    'having',
    # debugging
    'debug',
    'tap',
    'capture',
    # error handling
    'safe',
]
