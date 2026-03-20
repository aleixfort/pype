# pype

A minimal functional pipeline for Python. Build lazy, reusable pipelines with a small set of intuitive operators. Fire them with `>`.

```python
from pype import pipe, flatten, field, sort, having

result = records > (
    pipe
    @ having(status="active")
    // field("name")
    / sort()
    / " ".join
)
```

---

## Quick reference
### Core
```
value > pipe               fire pipeline, return raw value

/   func                   pass whole value to func
/   pipeline               compose two pipelines (sequential)
//  func                   map over each element
@   func                   filter — keep where func(x) is truthy
+   pipeline               fork — always inside parens:  / (a + b) /

All of  / // @ +  are multiplicative — same precedence, left-to-right.
>  is lower precedence    — pipeline always builds fully before firing.
```
### Utils
```
flatten                    one level of nesting → flat list
flatten_deep               any depth → flat list

sort(key, reverse)         sorted() with args
unique                     deduplicate preserving order
compact                    remove falsy values
take(n)                    first n elements
drop(n)                    skip first n elements
chunk(n)                   split into n-sized groups
window(n)                  sliding windows of size n
group(key)                 group into dict by key function

field(key, default)        extract dict key            — use with //
attr(name, default)        extract object attribute    — use with //

equals(value)              predicate — x == value
instance(type)             predicate — isinstance check
between(lo, hi)            predicate — range check
nonzero                    predicate — truthy values
matching(pattern)          predicate — substring or regex
having(**kwargs)           predicate — dict key/value match

debug(label)               print and pass through      — use with /
tap(func)                  side effect and pass through — use with /
capture(store, key)        snapshot mid-pipeline value — use with /

safe(fallback)(func)       return fallback on exception
```

---

## Why pype?

Python has no native pipe operator. The workarounds are either verbose (nested function calls, step-by-step assignment) or fragile (operator precedence traps). pype solves this with three design decisions:

**One.** All pipeline operators (`/` `//` `@` `+`) share the same precedence level. They always evaluate left-to-right, with no surprises.

**Two.** The pipeline is lazy. Nothing executes until `>` fires it. This means pipelines are values — you can name them, compose them, pass them around, and reuse them.

**Three.** The operator set is minimal and maps directly onto map/filter/reduce. Everything else is a plain function.

---

## Installation

```bash
pip install pype          # coming soon
# or just copy the pype/ folder into your project
```

```python
from pype import pipe                               # minimum
from pype import pipe, flatten, sort, debug         # with utilities
from pype import *                                  # everything
```

### Package structure

```
pype/
    __init__.py     # re-exports everything
    core.py         # Pipeline class and pipe sentinel — zero dependencies
    utils.py        # flatten, sort, field, debug, and friends
```

`core.py` is self-contained. If you only want the pipeline with no utilities, copy just that file.

---

## Mental model

Every data pipeline is a combination of three operations:

```
//   map     — transform each element     (same length)
@    filter  — select elements            (shorter or equal)
/    reduce  — collapse to single value   (one result)
```

pype gives them clean operator syntax. Anything else — flatten, sort, group, debug — is a plain function you pass with `/`.

### List mode

The pipeline stays in list mode throughout. `//` and `@` always receive and return lists. Only `/` can change shape — intentionally, when you want to aggregate or reduce:

```python
pipe // transform    # list → list  (same length)
pipe @  predicate    # list → list  (shorter)
pipe /  aggregate    # list → value (intentional exit from list mode)
```

This means you never have to think about what shape the value is mid-pipeline. It's always a list until you decide otherwise.

---

## Operators

All of `/ // @ +` are multiplicative — **same precedence, always left-to-right**.
`>` is lower precedence — the pipeline **always builds fully before firing**.

### `/` — pass

Pass the whole value to a function:

```python
["hello", "world"] > pipe / len          # → 2
["hello", "world"] > pipe / sorted       # → ["hello", "world"]
["hello", "world"] > pipe / " ".join     # → "hello world"
```

Compose two named pipelines sequentially:

```python
clean   = pipe // str.strip // str.lower
shout   = pipe // str.upper

process = clean / shout                  # clean then shout
```

### `//` — map

Apply a function to each element. One in, one out. List stays same length:

```python
def double(x): return x * 2

["hello", "world"] > pipe // str.upper   # → ["HELLO", "WORLD"]
["hello", "world"] > pipe // len         # → [5, 5]
[1, 2, 3]          > pipe // double      # → [2, 4, 6]
```

### `@` — filter

Keep elements where `func(x)` is truthy. One rule, no exceptions:

```python
def is_long(w):  return len(w) > 3
def is_adult(n): return n >= 18

pipe @ is_long               # keep long words
pipe @ str.isupper           # keep uppercase strings
pipe @ nonzero               # keep truthy values
pipe @ instance(str)         # keep strings
pipe @ equals("cat")         # keep elements == "cat"
pipe @ between(18, 65)       # keep numbers in range
pipe @ matching("ing")       # keep elements containing substring
pipe @ having(role="admin")  # keep dicts matching key/value
```

Any callable that returns truthy/falsy works — `def` functions, built-ins, predicates from utils.

### `+` — fork

Split one input into two or more parallel pipelines. Always wrap in parentheses:

```python
import statistics

stats = data > pipe / (
    pipe / statistics.mean   +
    pipe / statistics.median +
    pipe / statistics.stdev
)
# → [mean, median, stdev]
```

Fork then converge — the next `/` step receives the list of results:

```python
"photo.jpg" > load / preprocess / (edges + blurred) / np.hstack / save("compare.jpg")
```

### `>` — fire

Fires the pipeline and returns the raw value:

```python
result = data > pipe // str.upper / " ".join
```

---

## Writing functions for pype

### Plain functions

Any `def` function works as a pipeline step — no wrappers, no inheritance. If it takes a value and returns a value, it plugs in:

```python
def remove_stopwords(words):
    stopwords = {"the", "a", "an", "is"}
    return [w for w in words if w not in stopwords]

def score(text):
    return len(text) * 0.1

result = sentences > (
    pipe
    // str.split
    / flatten
    / remove_stopwords
    // score
)
```

### Configurable functions

Pipeline steps always receive exactly one argument — the current value. But sometimes a step also needs configuration: a path, a threshold, a size. The solution is a **closure** — an outer function that captures the configuration and returns the actual step:

```python
def save(path):        # called at build time — captures path
    def _save(img):    # called at fire time  — receives the value
        cv2.imwrite(path, img)
        return img
    return _save
```

When you write `pipe / save("output.jpg")`, Python calls `save("output.jpg")` immediately and hands `_save` — already knowing its path — to the pipeline as a step.

This pattern appears anywhere a step needs configuration:

```python
def blur(radius):
    def _blur(img): return cv2.GaussianBlur(img, (radius, radius), 0)
    return _blur

def prefix(text):
    def _prefix(s): return text + s
    return _prefix

def above(threshold):
    def _above(n): return n > threshold
    return _above

pipe / blur(5) / save("out.jpg")    # images
pipe // prefix("Mr. ")              # strings
pipe @ above(100)                   # numbers
```

Think of it as pre-loading an argument. The outer call locks in the configuration; the inner function is what the pipeline actually runs. All utils that take arguments — `sort(key)`, `take(n)`, `field(key)`, `matching(pattern)` — follow exactly this pattern.

---

## Named pipelines

Pipelines are values. Name them, reuse them, compose them with `/`:

```python
def has_vowel(word): return any(v in word for v in "aeiou")

tokenize = pipe // str.split / flatten
clean    = pipe // str.strip // str.lower
voiced   = pipe @ has_vowel
join     = pipe / " ".join

# compose sub-pipelines into larger ones
process  = tokenize / clean / voiced / join

# reuse anywhere
result_a = ["  Hello World  "] > process
result_b = ["  FOO BAR BAZ  "] > process

# test each piece independently
["  Hello  "] > clean    # → ["hello"]
["hello"]     > voiced   # → ["hello"]
```

Named pipelines are the core of the pype pattern. Write small focused functions, wire them into named pipelines, compose those pipelines into larger ones. The pipeline is just the glue.

---

## Forking and merging

`+` splits one value into two or more parallel pipelines. The fork point determines what each branch receives — everything before the `(` has already run.

### Basic fork

```python
import statistics
from pype import pipe

result = data > pipe / (
    pipe / statistics.mean   +
    pipe / statistics.median +
    pipe / statistics.stdev
)
# → [mean, median, stdev]
```

### Fork then merge

The step after `)` receives the list of branch results as a whole, so any function that takes a list can merge them:

```python
result = data > pipe / (branch_a + branch_b) / merge_func
```

```python
# side by side images
"photo.jpg" > load / preproc / (edges + blurred) / np.hstack / save("compare.jpg")

# combine stats into a dict
def as_dict(results):
    keys = ["mean", "median", "stdev"]
    return dict(zip(keys, results))

stats = data > pipe / (
    pipe / statistics.mean   +
    pipe / statistics.median +
    pipe / statistics.stdev
) / as_dict
# → {"mean": 5.0, "median": 4.5, "stdev": 2.0}
```

### Preserving a value across a transformation

pipe can also pas the value through unchanged. Use it in a fork to preserve the value at the fork point while transforming it in the other branch:

```python
from pype import pipe

branch = pipe / step2 / step3 / step4

result = data > pipe / step1 / (branch + pipe) / merge
#                                          ↑ value after step1, untouched
```

Since the fork point is where you place the parentheses, you control exactly which version of the value gets preserved:

```python
# preserve original input
result = data > (branch + pipe) / merge

# preserve value after step1
result = data > pipe / step1 / (branch + pipe) / merge

# preserve value after step2
result = data > pipe / step1 / step2 / (branch + pipe) / merge
```

Named pipelines make this even cleaner:

```python
process  = pipe / step2 / step3 / step4
preserve = pipe

result = data > pipe / step1 / (process + preserve) / merge
```

For capturing values from further back — or accessing them after the pipeline has fired — use `capture` from utils instead.

---

## Utilities

All utilities live in `pype/utils.py` and are re-exported from `pype` directly.

### Flatten

```python
pipe // str.split / flatten        # one level: [[1,2],[3,4]] → [1,2,3,4]
pipe / flatten_deep                # any depth:  [1,[2,[3]]]  → [1,2,3]
```

### Sequence

```python
pipe / sort()                      # alphabetical
pipe / sort(key=len, reverse=True) # by length descending
pipe / unique                      # deduplicate preserving order
pipe / compact                     # remove falsy values
pipe / take(3)                     # first 3 elements
pipe / drop(3)                     # skip first 3
pipe / chunk(2)                    # [[1,2],[3,4],[5]]
pipe / window(2)                   # [(1,2),(2,3),(3,4)]
pipe / group(key)                  # → dict grouped by key function
```

### Dict and object access

```python
users   > pipe // field("name")            # extract dict key
users   > pipe // field("age", default=0)  # with fallback
objects > pipe // attr("created_at")       # extract object attribute
```

### Predicates for `@`

```python
pipe @ equals("cat")               # x == value
pipe @ instance(str)               # isinstance check
pipe @ between(0, 100)             # range check
pipe @ nonzero                     # truthy values
pipe @ matching("ing")             # substring or regex
pipe @ having(status="active")     # dict key/value match
```

### Debugging

```python
pipe / debug("label")              # print and pass through
pipe / tap(log_to_file)            # side effect and pass through

captured = {}
pipe / capture(captured, "words")  # snapshot mid-pipeline value
```

### Error handling

```python
pipe // safe(0)(int)               # replace failed int() with 0
pipe / safe([])(parse_json)        # return [] if parse fails
```

---

## OpenCV example

A real-world example showing named pipelines, configurable functions, fork, and batch processing:

```python
import cv2
import numpy as np
from pype import pipe

def blur(k=5):
    def _blur(img): return cv2.GaussianBlur(img, (k, k), 0)
    return _blur

def canny(lo, hi):
    def _canny(img): return cv2.Canny(img, lo, hi)
    return _canny

def dilate(n=1):
    kernel = np.ones((3, 3), np.uint8)
    def _dilate(img): return cv2.dilate(img, kernel, iterations=n)
    return _dilate

def save(path):
    def _save(img):
        cv2.imwrite(path, img)
        return img
    return _save

def to_gray(img): return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
def to_bgr(img):  return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

# named sub-pipelines
load    = pipe / cv2.imread
preproc = pipe / to_gray / blur(5)
edges   = pipe / canny(50, 150) / dilate(2) / to_bgr
blurred = pipe / blur(15) / to_bgr

# single image — edge detection
"photo.jpg" > load / preproc / edges / save("edges.jpg")

# fork — edges vs blurred side by side
"photo.jpg" > load / preproc / (edges + blurred) / np.hstack / save("compare.jpg")

# batch process a folder
import glob
paths = glob.glob("images/*.jpg")
paths > pipe // (load / preproc / edges / save("out.jpg"))
```

---

## Comparison with other libraries

| | **pype** | **pipe** | **sspipe** | **toolz** |
|---|---|---|---|---|
| Operators | `>` `/` `//` `@` `+` | `\|` | `\|` | function calls |
| Precedence-safe | ✅ all same level | ❌ mixes levels | ❌ mixes levels | ✅ no operators |
| Lazy pipeline object | ✅ | ❌ eager | ❌ eager | ❌ eager |
| Named composable pipelines | ✅ first class | ❌ | ❌ | partial via `compose` |
| Map | `//` | `select` | manual | `map` |
| Filter | `@` | `where` | manual | `filter` |
| Flatten | `/ flatten` | `traverse` | manual | `/ concat` |
| Type filter | `@ instance(str)` | ❌ | ❌ | ❌ |
| Fork / parallel | `+` | ❌ | `tee` (copy only) | `juxt` |
| Zero dependencies | ✅ | ✅ | ❌ | ❌ |

**pipe (JulienPalard)** — most popular Python pipe library. Uses `|` which mixes precedence levels — combining it with comparison operators silently produces wrong results. Pipelines are eager so you can't name or reuse a half-built pipeline.

**sspipe** — similar to `pipe`, also uses `|`. Adds parallel support via `tee` but only for copying values, not running different transformations.

**toolz** — serious functional programming library. No operator overloading, everything is a function call. Very composable via `compose` and `curry` but verbose. `pipe(value, f1, f2, f3)` executes immediately — not lazy.

**pype** — the key differentiator is the lazy pipeline object. Because nothing executes until `>`, pipelines are first-class values. The operator set maps directly to map/filter/reduce, making the mental model explicit.
