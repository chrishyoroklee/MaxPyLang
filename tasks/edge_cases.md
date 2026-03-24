# Naming Edge Cases for Class-Based API Migration

## Table of Contents
1. [Sanitization Rules](#1-sanitization-rules)
2. [Tilde (~) — Audio Objects](#2-tilde----audio-objects)
3. [Dot (.) — Namespace Hierarchies](#3-dot----namespace-hierarchies)
4. [Dot + Tilde Combined](#4-dot--tilde-combined)
5. [Hyphen (-) — Only 1 Object](#5-hyphen----only-1-object)
6. [Leading Digit — Only 1 Object](#6-leading-digit--only-1-object)
7. [Python Keyword Collisions](#7-python-keyword-collisions)
8. [Python Builtin Collisions](#8-python-builtin-collisions)
9. [Operator Symbols — Alias Resolution](#9-operator-symbols--alias-resolution)
10. [Ambiguity: Underscore Flattening](#10-ambiguity-underscore-flattening)
11. [Cross-Package Name Collisions](#11-cross-package-name-collisions)
12. [Summary Table](#12-summary-table)

---

## 1. Sanitization Rules

The `sanitize_py_name()` function in `importobjs.py` (line 595) converts Max object names to valid Python identifiers. Transformations are applied **in this order**:

```python
def sanitize_py_name(max_name):
    name = max_name.replace("~", "_tilde")   # Step 1
    name = name.replace(".", "_")             # Step 2
    name = name.replace("-", "_")             # Step 3
    if name and name[0].isdigit():            # Step 4
        name = "_" + name
    if keyword.iskeyword(name) or name in dir(builtins):  # Step 5
        name = name + "_"
    return name
```

| Step | Rule | Example |
|------|------|---------|
| 1 | `~` → `_tilde` | `cycle~` → `cycle_tilde` |
| 2 | `.` → `_` | `jit.movie` → `jit_movie` |
| 3 | `-` → `_` | `windowed-fft~` → `windowed_fft_tilde` |
| 4 | Leading digit → `_` prefix | `2d.wave~` → `_2d_wave_tilde` |
| 5 | Python keyword/builtin → `_` suffix | `if` → `if_`, `dict` → `dict_` |

**Order matters:** `in~` first becomes `in_tilde` (step 1), then the keyword check (step 5) does NOT trigger because `in_tilde` is not a keyword. But `in` (without tilde) stays `in` through steps 1-4, then becomes `in_` at step 5.

---

## 2. Tilde (`~`) — Audio Objects

**Rule:** `~` → `_tilde`

Applies to ~460 MSP audio-rate objects. This is the most common transformation.

```python
# Class-based usage
cycle_tilde(440)         # cycle~
ezdac_tilde()            # ezdac~
noise_tilde()            # noise~
phasor_tilde(1)          # phasor~
lores_tilde()            # lores~
delay_tilde()            # delay~
tapin_tilde()            # tapin~
tapout_tilde(500)        # tapout~
buffer_tilde("mybuf")    # buffer~
```

**Impact on class-based design:** None — `_tilde` suffix is unambiguous and well-established. Users already use these names with the current stub system.

---

## 3. Dot (`.`) — Namespace Hierarchies

**Rule:** `.` → `_`

Used for Max's hierarchical package namespaces. Objects can have 2, 3, or even 4 dot levels.

```python
# 2 levels (package.object)
jit_movie()              # jit.movie
dict_codebox()           # dict.codebox
zl_join()                # zl.join
mc_assign()              # mc.assign
array_change()           # array.change

# 3 levels (package.sub.object)
jit_gl_camera()          # jit.gl.camera
jit_anim_drive()         # jit.anim.drive
jit_la_determinant()     # jit.la.determinant
jit_net_recv()           # jit.net.recv
jit_phys_6dof()          # jit.phys.6dof

# 4 levels
jit_gl_pix_codebox()     # jit.gl.pix.codebox
```

**Concern:** `dict_codebox` — is that `dict.codebox` or a single object named `dict_codebox`? Answer: it's always `dict.codebox` because Max object names use dots, never underscores internally. But users need to **know** this convention.

---

## 4. Dot + Tilde Combined

Objects with both namespace dots and the audio-rate tilde.

```python
gen_codebox_tilde()      # gen.codebox~
mc_jit_peek_tilde()      # mc.jit.peek~
jit_catch_tilde()        # jit.catch~
jit_buffer_tilde()       # jit.buffer~
jit_poke_tilde()         # jit.poke~
jit_release_tilde()      # jit.release~
mc_plus_tilde()          # mc.plus~
mcs_cycle_tilde()        # mcs.cycle~
```

**Impact on class-based design:** None — transformations compose cleanly. The name is longer but unambiguous.

---

## 5. Hyphen (`-`) — Only 1 Object

**Rule:** `-` → `_`

Only a single object in the entire database uses a hyphen:

```python
windowed_fft_tilde()     # windowed-fft~
```

**Impact on class-based design:** None — trivial case.

---

## 6. Leading Digit — Only 1 Object

**Rule:** If name starts with a digit, prepend `_`

Only a single object starts with a digit:

```python
_2d_wave_tilde()         # 2d.wave~
```

**Note:** When a dot/namespace comes first, the digit is no longer leading:
- `jit.3m` → `jit_3m` (NOT `_jit_3m` — the `j` is the leading character)
- `mc.2d.wave~` → `mc_2d_wave_tilde` (NOT `_mc_2d_wave_tilde`)
- `jit.phys.6dof` → `jit_phys_6dof` (the `j` is leading)

**Concern:** The `_` prefix makes it look like a private/internal name in Python convention. This is cosmetic and acceptable — only 1 object is affected.

---

## 7. Python Keyword Collisions

**Rule:** If the sanitized name is a Python keyword, append `_`

Only **3 actual Max objects** collide with Python keywords:

| Max name | Package | Python stub | Keyword |
|----------|---------|-------------|---------|
| `if` | max | `if_()` | `if` |
| `in` | max | `in_()` | `in` |
| `in` | msp | `in_()` | `in` |

**Note:** `pass` exists only as `pass~` in MSP, which becomes `pass_tilde()` (step 1 runs before step 5), so the keyword check never triggers for it.

```python
# Class-based usage
if_(cond, then_val, else_val)   # if
in_(1)                           # in (with inlet number)
```

**Impact on class-based design:** The trailing `_` looks slightly odd but is standard Python convention (PEP 8) for avoiding keyword conflicts.

---

## 8. Python Builtin Collisions

**Rule:** If the sanitized name matches a Python builtin, append `_`

**9 actual Max objects** collide with Python builtins:

| Max name | Python stub | Shadows builtin |
|----------|-------------|-----------------|
| `abs` | `abs_()` | `abs()` |
| `dict` | `dict_()` | `dict()` |
| `float` | `float_()` | `float()` |
| `int` | `int_()` | `int()` |
| `iter` | `iter_()` | `iter()` |
| `next` | `next_()` | `next()` |
| `pow` | `pow_()` | `pow()` |
| `print` | `print_()` | `print()` |
| `round` | `round_()` | `round()` |

```python
# Class-based usage
int_(0)                  # int (Max integer box)
float_(0.0)              # float (Max float box)
dict_()                  # dict (Max dictionary)
abs_()                   # abs (Max absolute value)
print_()                 # print (Max print to console)
```

**Note:** `abs~` (MSP audio version) becomes `abs_tilde()` — the tilde transformation at step 1 avoids the builtin collision entirely.

**Impact on class-based design:** Users must remember the `_` suffix for these common names. This is the same as the current stub system — no new burden.

---

## 9. Operator Symbols — Alias Resolution

Max lets users type `+`, `*`, `>`, etc. directly in a box. These are **not** stored as object names in the database. Instead, `obj_aliases.json` maps them to word names **before** any stub lookup occurs.

### Control-rate operators (max package)

| Symbol | Alias resolves to | Stub name |
|--------|-------------------|-----------|
| `+` | `plus` | `plus()` |
| `-` | `minus` | `minus()` |
| `*` | `times` | `times()` |
| `/` | `div` | `div()` |
| `%` | `modulo` | `modulo()` |
| `>` | `greaterthan` | `greaterthan()` |
| `>=` | `greaterthaneq` | `greaterthaneq()` |
| `<` | `lessthan` | `lessthan()` |
| `<=` | `lessthaneq` | `lessthaneq()` |
| `==` | `equals` | `equals()` |
| `!=` | `notequals` | `notequals()` |
| `&&` | `logand` | `logand()` |
| `\|\|` | `logor` | `logor()` |
| `&` | `bitand` | `bitand()` |
| `\|` | `bitor` | `bitor()` |
| `<<` | `shiftleft` | `shiftleft()` |
| `>>` | `shiftright` | `shiftright()` |
| `!/` | `rdiv` | `rdiv()` |
| `!-` | `rminus` | `rminus()` |

### Audio-rate operators (msp package)

| Symbol | Alias resolves to | Stub name |
|--------|-------------------|-----------|
| `+~` | `plus~` | `plus_tilde()` |
| `-~` | `minus~` | `minus_tilde()` |
| `*~` | `times~` | `times_tilde()` |
| `/~` | `div~` | `div_tilde()` |
| `%~` | `modulo~` | `modulo_tilde()` |
| `>~` | `greaterthan~` | `greaterthan_tilde()` |
| `>=~` | `greaterthaneq~` | `greaterthaneq_tilde()` |
| `<~` | `lessthan~` | `lessthan_tilde()` |
| `<=~` | `lessthaneq~` | `lessthaneq_tilde()` |
| `==~` | `equals~` | `equals_tilde()` |
| `!=~` | `notequals~` | `notequals_tilde()` |
| `+=~` | `plusequals~` | `plusequals_tilde()` |
| `!/~` | `rdiv~` | `rdiv_tilde()` |
| `!-~` | `rminus~` | `rminus_tilde()` |

### Multichannel operator aliases (mc package)

All `mc.*~` operators follow the same pattern: `mc.+~` → `mc.plus~` → `mc_plus_tilde()`.

```python
# Class-based usage
plus(1, 2)               # + (adds two numbers)
times(3)                 # * (multiplies)
plus_tilde()             # +~ (audio addition)
times_tilde()            # *~ (audio multiplication)
mc_plus_tilde()          # mc.+~ (multichannel audio addition)
```

**No stubs exist for the symbol forms** — users must use the word names. This is fine for the class-based API since `+`, `*`, etc. can't be Python identifiers anyway.

**Impact on class-based design:** None — alias resolution happens at `MaxObject` construction time (inside `get_ref()`), which is downstream of `MaxObjectSpec.__call__()`. If a user writes `MaxObject("+")` directly, aliases still resolve. But in the class-based world, users just use `plus()`.

---

## 10. Ambiguity: Underscore Flattening

Multiple transformations all collapse to `_`, which could theoretically cause collisions:

| Separator | Max example | Becomes |
|-----------|------------|---------|
| `.` (dot) | `dict.iter` | `dict_iter` |
| `-` (hyphen) | `windowed-fft~` | `windowed_fft_tilde` |
| `_` (already underscore) | (none exist) | — |

**Could two different Max objects produce the same Python name?**

In theory: yes, if Max had both `foo.bar` and `foo-bar`, both would become `foo_bar`.

In practice: **no**. Max object names never use underscores, and no two objects differ only by `.` vs `-`. There are zero actual collisions in the ~1140 object database.

**Impact on class-based design:** No action needed. This is a theoretical risk only.

---

## 11. Cross-Package Name Collisions

The `__init__.py` imports all three packages with `from .{pkg} import *`. If two packages define the same object name, the **last import wins** (silently shadows the first).

### Actual collision: `in` exists in both `max` and `msp`

| Package | Max name | JSON file | Stub name |
|---------|----------|-----------|-----------|
| max | `in` | `max/in.json` | `in_` |
| msp | `in` | `msp/in.json` | `in_` |
| msp | `in~` | `msp/in~.json` | `in_tilde` |

Current import order in `__init__.py`:
```python
from .jit import *   # first
from .max import *   # second — defines in_
from .msp import *   # third — SHADOWS max's in_ with msp's in_
```

**Result:** `in_` refers to the MSP version. The Max version is inaccessible via the flat import.

### Other potential collisions

| Object | Exists in max? | Exists in msp? | Exists in jit? |
|--------|---------------|----------------|----------------|
| `in` | Yes | Yes | No |
| `out` | No | Yes (`out`, `out~`) | No |
| `pass` | No | Yes (`pass~` only) | No |

Only `in` has an actual cross-package collision.

### Workaround for users who need the shadowed version

```python
# Access package-specific versions directly
from maxpylang.objects.max import in_ as max_in
from maxpylang.objects.msp import in_ as msp_in
```

**Impact on class-based design:** This is a **pre-existing issue** that the class-based migration doesn't fix but also doesn't make worse. The same shadowing behavior occurs whether the stubs are `MaxObject` instances or `MaxObjectSpec` factories.

**Potential future fix:** Offer namespaced imports like `from maxpylang.objects.max import in_` alongside the flat `from maxpylang.objects import in_`.

---

## 12. Summary Table

| Edge Case | Count | Current Handling | Class-Based Impact | Action Needed |
|-----------|-------|-----------------|-------------------|---------------|
| `~` → `_tilde` | ~460 | Works | `cycle_tilde(440)` — clean | None |
| `.` → `_` | ~300+ | Works | `jit_movie()` — clean | None |
| `-` → `_` | 1 | Works | `windowed_fft_tilde()` — clean | None |
| Leading digit → `_` prefix | 1 | Works | `_2d_wave_tilde()` — looks private | Cosmetic, acceptable |
| Python keywords | 3 | `_` suffix | `if_()`, `in_()` — standard PEP 8 | None |
| Python builtins | 9 | `_` suffix | `int_()`, `dict_()` — must remember `_` | None |
| Operator symbols | 52 aliases | Alias → word name | `plus()`, `times_tilde()` — natural | None |
| Underscore flattening | 0 collisions | No actual conflicts | Theoretical risk only | None |
| Cross-package shadowing | 1 (`in`) | Last import wins | Pre-existing issue | Consider namespaced imports |

**Bottom line:** All naming edge cases are already handled by `sanitize_py_name()`. The class-based migration (`MaxObjectSpec`) inherits these rules as-is. No new edge cases are introduced by making stubs callable.
