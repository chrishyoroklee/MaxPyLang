# Migration Plan: String Syntax → Class-Based Object API

## Table of Contents
1. [Problem Statement](#1-problem-statement)
2. [Current Architecture](#2-current-architecture)
3. [Target Architecture](#3-target-architecture)
4. [Design Decisions](#4-design-decisions)
5. [Implementation Phases](#5-implementation-phases)
6. [Edge Cases & Challenges](#6-edge-cases--challenges)
7. [File Change Summary](#7-file-change-summary)
8. [Verification Plan](#8-verification-plan)

---

## 1. Problem Statement

MaxPyLang currently has two incompatible ways to create objects:

| Approach | Example | Pros | Cons |
|----------|---------|------|------|
| **String syntax** | `patch.place("cycle~ 440")` | Supports args, attributes | No autocomplete, fragile string concat, Max-specific `@` syntax |
| **Stub instances** | `patch.place(cycle_tilde)` | IDE autocomplete for object names | Cannot pass arguments, must use `edit()` after |

Neither approach offers the full Python developer experience. The goal is a **single, unified class-based API** that combines the discoverability of stubs with the expressiveness of string syntax.

### What's Wrong Today

```python
# String concatenation for dynamic args — fragile, no type safety
freq = 440
patch.place("cycle~ " + str(freq))

# Stubs can't take args — requires awkward two-step
osc = patch.place(cycle_tilde)[0]
osc.edit(text="440")

# Attributes use Max-specific @ syntax inside strings
patch.place("metro 500 @active 1")

# No IDE help for which args/attribs an object accepts
patch.place("cycle~ ???")  # what arguments does cycle~ take?
```

### What We Want

```python
# Direct Python arguments — type safe, clean
osc = patch.place(cycle_tilde(440))[0]

# Attributes as keyword arguments — Pythonic
m = patch.place(metro(500, active=1))[0]

# Dynamic I/O objects work naturally
p = patch.place(pack(0, 0, 0))[0]  # → 3 inlets

# IDE autocomplete for object names + docstrings for args
cycle_tilde(  # IDE shows: frequency(number), buffer_name(symbol), ...
```

---

## 2. Current Architecture

### Object Creation Flow

```
User Code                    Internal Pipeline
─────────                    ─────────────────
"cycle~ 440"  ──┐
                ├──→ MaxObject.__init__(text)
cycle_tilde   ──┘       │
                         ├──→ parse_text() → name="cycle~", args=[440], text_attribs={}
                         ├──→ get_ref("cycle~") → finds cycle~.json in data/OBJ_INFO/msp/
                         ├──→ get_info() → loads default dict, arg specs, attrib specs, I/O rules
                         ├──→ args_valid() → validates arg types against spec
                         ├──→ make_xlets_from_self_dict() → creates Inlet/Outlet objects
                         ├──→ update_ins_outs() → adjusts I/O for dynamic objects
                         └──→ update_text() → rebuilds text field in dict
```

### Key Internal State (MaxObject instance)

| Field | Type | Description |
|-------|------|-------------|
| `_name` | `str` | Object class name (e.g. `"cycle~"`) |
| `_args` | `list` | Positional args (e.g. `[440.0]`) |
| `_text_attribs` | `dict` | In-box @-attributes (e.g. `{"active": ["1"]}`) |
| `_dict` | `dict` | Full JSON representation for .maxpat serialization |
| `_ref_file` | `str\|None` | Path to JSON ref file, `"abstraction"`, or `None` |
| `_ins` / `_outs` | `list` | Inlet/Outlet objects |
| `_ext_file` | `str\|None` | External file path (for js/abstractions) |

### Stub Files (Current)

`maxpylang/objects/msp.py` (auto-generated, ~10k lines, ~460 objects):
```python
from maxpylang.maxobject import MaxObject

__all__ = ['cycle_tilde', 'ezdac_tilde', ...]
_NAMES = {'cycle_tilde': 'cycle~', 'ezdac_tilde': 'ezdac~', ...}

# stdout suppressed during instantiation (each creates a full MaxObject)
_devnull = open(_os.devnull, 'w')
_sys.stdout = _devnull

cycle_tilde = MaxObject('cycle~')    # reads JSON, parses text, creates xlets
ezdac_tilde = MaxObject('ezdac~')    # same for every object...
# ... ~460 more

_sys.stdout = _old_stdout
```

**Problems:** Slow import (each stub reads a JSON file + full instantiation), stdout suppression hack, stubs are instances not factories.

### Reference Data (JSON per object)

Example `data/OBJ_INFO/msp/cycle~.json`:
```json
{
  "default": {
    "box": {
      "maxclass": "newobj",
      "numinlets": 2, "numoutlets": 1,
      "outlettype": ["signal"],
      "text": "cycle~"
    }
  },
  "args": {
    "required": [],
    "optional": [
      {"name": "frequency", "units": "hz", "type": ["number"]},
      {"name": "buffer-name", "type": ["symbol"]},
      {"name": "sample-offset", "type": ["int"]}
    ]
  },
  "attribs": [
    {"name": "COMMON"},
    {"name": "buffer", "type": "symbol", "size": "1"},
    {"name": "frequency", "type": "float", "size": "1"},
    {"name": "phase", "type": "float", "size": "1"}
  ],
  "in/out": {}
}
```

Example `data/OBJ_INFO/max/pack.json` (dynamic I/O):
```json
{
  "args": {
    "required": [],
    "optional": [{"name": "list-elements", "type": ["any"]}]
  },
  "in/out": {
    "numinlets": [{"argtype": "a", "index": "all", "type": null}]
  }
}
```

---

## 3. Target Architecture

### New Class: `MaxObjectSpec`

A **lightweight callable factory** that stores object metadata and produces `MaxObject` instances when invoked.

```
User Code                        Internal Pipeline (unchanged)
─────────                        ────────────────────────────
cycle_tilde(440)
    │
    ├──→ MaxObjectSpec.__call__()
    │       ├──→ builds text: "cycle~ 440"
    │       ├──→ partitions kwargs → text_attribs vs extra_attribs
    │       └──→ MaxObject(text, **extra_attribs)  ──→ existing pipeline
    │
    └──→ Returns MaxObject instance (same as before)
```

Key insight: **`MaxObjectSpec` is a thin wrapper that delegates to the existing `MaxObject` pipeline.** No changes needed to serialization, connection logic, or patch saving.

### API Comparison (Before → After)

```python
# ── Basic object with args ──
# Before:
osc = patch.place("cycle~ 440")[0]
# After:
osc = patch.place(cycle_tilde(440))[0]

# ── Object with @-attributes ──
# Before:
m = patch.place("metro 500 @active 1")[0]
# After:
m = patch.place(metro(500, active=1))[0]

# ── Dynamic I/O ──
# Before:
p = patch.place("pack 0 0 0")[0]        # 3 inlets
t = patch.place("trigger b i f")[0]      # 3 outlets
# After:
p = patch.place(pack(0, 0, 0))[0]       # 3 inlets
t = patch.place(trigger("b", "i", "f"))[0]  # 3 outlets

# ── No-arg objects ──
# Before:
dac = patch.place(ezdac_tilde)[0]       # stub instance
# After:
dac = patch.place(ezdac_tilde())[0]     # factory call with no args

# ── Dynamic args in loops ──
# Before:
for freq in [220, 440, 880]:
    patch.place(f"cycle~ {freq}")        # f-string construction
# After:
for freq in [220, 440, 880]:
    patch.place(cycle_tilde(freq))       # native Python args

# ── Editing after placement ──
# Before:
osc.edit(text="880")
# After (Phase 3):
osc.edit(880)

# ── Abstractions (unchanged) ──
synth = mp.MaxObject("my_synth", abstraction=True, inlets=2, outlets=2)
placed = patch.place(synth)[0]
```

---

## 4. Design Decisions

### Why callable factories, not subclasses?

**Option A — One class per object** (`class Cycle(MaxObject): ...`):
- Would need ~1140 class definitions
- Inheritance hierarchy unclear (Cycle inherits from MaxObject?)
- `place()` returns `MaxObject`, not `Cycle` — confusing
- Class identity checks (`isinstance(obj, Cycle)`) not useful since all objects serialize the same way

**Option B — Enhanced `MaxObject` constructor** (`MaxObject("cycle~", freq=440)`):
- Still requires string name — no autocomplete benefit
- Mixes factory pattern into the data class

**Option C — Callable factories (chosen)** (`cycle_tilde(440) → MaxObject`):
- Stubs already exist with correct names — just make them callable
- Returns `MaxObject` (consistent with current API)
- Metadata stored once, objects created on demand
- Massive import speedup (no more eager instantiation)
- Generation pipeline stays simple

### How are kwargs partitioned?

When a user writes `metro(500, active=1)`, the `active` kwarg needs to become `@active 1` in the Max text string (it's an object-specific attribute). But `fontsize=12` would be a common box attribute passed as `**extra_attribs` to `MaxObject`.

`MaxObjectSpec._partition_attribs()` uses the embedded `attrib_spec` to decide:
- If the kwarg name matches an entry in `attrib_spec` (excluding `COMMON`) → text attribute (`@name val`)
- Otherwise → extra attribute (passed as `**kwargs` to `MaxObject` constructor)

### What about no-arg calls?

`ezdac_tilde()` with no arguments produces `MaxObject('ezdac~')` — identical to the current stub behavior. The `()` is required because `ezdac_tilde` is now a factory, not an instance.

**Breaking change:** `patch.place(ezdac_tilde)` (without parens) will still work during the transition because `place()` will detect `MaxObjectSpec` and call it with no args. But this will emit a deprecation warning.

### What about `place()` accepting `MaxObjectSpec` directly?

For convenience during transition, `place()` will detect if an argument is a `MaxObjectSpec` (not yet called) and call it with no args. This means `patch.place(ezdac_tilde)` and `patch.place(ezdac_tilde())` both work, but the former emits a deprecation warning nudging toward the latter.

---

## 5. Implementation Phases

### Phase 0: `MaxObjectSpec` Foundation

**Goal:** Add the new factory class, wire it into `place()`, validate with tests. No changes to existing behavior.

#### 5.0.1 — Create `maxpylang/maxobjectspec.py`

```python
"""
Callable factory for Max objects.

MaxObjectSpec stores object metadata (arg specs, attribute specs) and
produces MaxObject instances when called with Python arguments.
"""
import warnings


class MaxObjectSpec:
    """
    A callable factory that creates MaxObject instances.

    Instead of constructing MaxObjects from text strings, use a
    MaxObjectSpec to pass arguments as native Python values:

        cycle_tilde(440)          →  MaxObject('cycle~ 440')
        metro(500, active=1)      →  MaxObject('metro 500 @active 1')
        pack(0, 0, 0)             →  MaxObject('pack 0 0 0')
    """

    def __init__(self, max_name, arg_spec=None, attrib_spec=None, docstring=""):
        self._max_name = max_name
        self._arg_spec = arg_spec or {"required": [], "optional": []}
        self._attrib_spec = attrib_spec or []
        if docstring:
            self.__doc__ = docstring

    def __call__(self, *args, **attribs):
        from .maxobject import MaxObject  # deferred to avoid circular import

        # Build text: "cycle~ 440 @phase 0.5"
        parts = [self._max_name]
        for arg in args:
            parts.append(str(arg))

        # Partition kwargs into text attribs vs extra (box) attribs
        text_attribs, extra_attribs = self._partition_attribs(attribs)
        for attr_name, attr_val in text_attribs.items():
            parts.append(f"@{attr_name}")
            if isinstance(attr_val, (list, tuple)):
                parts.extend(str(v) for v in attr_val)
            else:
                parts.append(str(attr_val))

        text = " ".join(parts)
        return MaxObject(text, **extra_attribs)

    def _partition_attribs(self, attribs):
        obj_attrib_names = {
            a['name'] for a in self._attrib_spec
            if a.get('name') and a.get('name') != 'COMMON'
        }
        text_attribs = {}
        extra_attribs = {}
        for key, val in attribs.items():
            if key in obj_attrib_names:
                text_attribs[key] = val
            else:
                extra_attribs[key] = val
        return text_attribs, extra_attribs

    @property
    def max_name(self):
        """The Max object class name (e.g. 'cycle~')."""
        return self._max_name

    @property
    def arg_spec(self):
        """Argument specification from the object's reference file."""
        return self._arg_spec

    @property
    def attrib_spec(self):
        """Attribute specification from the object's reference file."""
        return self._attrib_spec

    def __repr__(self):
        return f"MaxObjectSpec('{self._max_name}')"
```

#### 5.0.2 — Modify `maxpylang/tools/patchfuncs/placing.py`

**`get_obj_from_spec()` (line 383):** Add `MaxObjectSpec` handling.

```python
def get_obj_from_spec(self, obj_spec):
    from maxpylang.maxobjectspec import MaxObjectSpec

    if isinstance(obj_spec, str):
        obj = MaxObject(obj_spec)
    elif isinstance(obj_spec, MaxObjectSpec):
        obj = obj_spec()  # call factory with no args
    else:
        assert isinstance(obj_spec, MaxObject), \
            f"object must be specified as a string, MaxObject, or MaxObjectSpec"
        obj = obj_spec

    return obj
```

**`place_check_args()` (line 110-113):** Add `MaxObjectSpec` to isinstance check.

```python
from maxpylang.maxobjectspec import MaxObjectSpec

for obj in objs:
    assert isinstance(obj, (MaxObject, MaxObjectSpec, str, list)), \
        f"objs list must be strings, MaxObjects, or MaxObjectSpecs"
```

#### 5.0.3 — Modify `maxpylang/__init__.py`

Add `MaxObjectSpec` to exports.

#### 5.0.4 — Create `tests/test_maxobjectspec.py`

Test cases:
- `MaxObjectSpec('cycle~', arg_spec=...)(440)` → MaxObject with `name == "cycle~"`, `_args == [440.0]`
- `MaxObjectSpec('metro', ...)(500, active=1)` → text contains `"metro 500 @active 1"`
- `MaxObjectSpec('pack', ...)(0, 0, 0)` → MaxObject with 3 inlets (dynamic I/O)
- `MaxObjectSpec('trigger', ...)("b", "i", "f")` → MaxObject with 3 outlets
- `MaxObjectSpec('ezdac~', ...)()` → MaxObject with name `"ezdac~"` and no args
- `patch.place(MaxObjectSpec('cycle~', ...)())` → works, returns list of MaxObject
- `patch.place(MaxObjectSpec('cycle~', ...))` → works (auto-called with no args)
- Unknown attrib kwarg → emits warning

---

### Phase 1: Update Auto-Generation Pipeline

**Goal:** `importobjs.py` generates `MaxObjectSpec` instances instead of `MaxObject` instances. Regenerate all stub files.

#### 5.1.1 — Modify `maxpylang/importobjs.py` → `generate_stubs()` (line 693)

**Before** (current generation per object):
```python
stub_lines.append(f"{py_name} = MaxObject('{max_name}')")
```

**After:**
```python
import json as _json

# Embed specs directly from the JSON reference file
arg_spec_str = _json.dumps(obj_info.get('args', {}), indent=None)
attrib_spec_str = _json.dumps(obj_info.get('attribs', []), indent=None)

stub_lines.append(f"{py_name} = MaxObjectSpec(")
stub_lines.append(f"    '{max_name}',")
stub_lines.append(f"    arg_spec={arg_spec_str},")
stub_lines.append(f"    attrib_spec={attrib_spec_str},")
stub_lines.append(f"    docstring={repr(docstring)},")
stub_lines.append(f")")
```

**Other changes to `generate_stubs()`:**
- Line 731: Change import from `MaxObject` to `MaxObjectSpec`
- Lines 750-753: **Remove** stdout suppression hack (`_devnull`, `_old_stdout`)
- Lines 770-773: **Remove** stdout restoration
- Keep `_NAMES` dict for now (backward compat); mark for removal in Phase 5

**Generated output changes (example):**

```python
# Before
"""
cycle~ - Sinusoidal oscillator
...
"""
cycle_tilde = MaxObject('cycle~')

# After
"""
cycle~ - Sinusoidal oscillator
...
"""
cycle_tilde = MaxObjectSpec(
    'cycle~',
    arg_spec={"required": [], "optional": [{"name": "frequency", "units": "hz", "type": ["number"]}, ...]},
    attrib_spec=[{"name": "COMMON"}, {"name": "buffer", "type": "symbol", "size": "1"}, ...],
    docstring="cycle~ - Sinusoidal oscillator\n\nArgs:\n  frequency (number, optional)\n...",
)
```

#### 5.1.2 — Modify `maxpylang/objects/__init__.py`

Remove the `UnknownObjectWarning` suppression — no longer needed since `MaxObjectSpec.__init__` doesn't instantiate `MaxObject`.

```python
# Before
import warnings
from maxpylang.exceptions import UnknownObjectWarning

with warnings.catch_warnings():
    warnings.simplefilter("ignore", UnknownObjectWarning)
    try:
        from .jit import *
    except ImportError:
        pass
    ...

# After
try:
    from .jit import *
except ImportError:
    pass
try:
    from .max import *
except ImportError:
    pass
try:
    from .msp import *
except ImportError:
    pass
```

#### 5.1.3 — Regenerate stub files

Run `import_objs('vanilla', overwrite=True)` (requires Max open) to regenerate:
- `maxpylang/objects/max.py` (~470 objects)
- `maxpylang/objects/msp.py` (~460 objects)
- `maxpylang/objects/jit.py` (~210 objects)

**Performance impact:** Import time for `maxpylang.objects` drops from ~1140 JSON reads + MaxObject instantiations to ~1140 dict literal constructions. Expected speedup: 10-50x.

---

### Phase 2: Deprecation Warnings

**Goal:** Nudge users toward the new API. Old code still works but emits warnings.

#### 5.2.1 — Modify `maxpylang/maxobject.py` (line 32)

Add private `_from_spec` parameter:

```python
def __init__(self, text, from_dict=False, abstraction=False,
             inlets=None, outlets=None, _from_spec=False, **extra_attribs):
    ...
    if not from_dict and not abstraction and not _from_spec and isinstance(text, str):
        warnings.warn(
            f"String-based MaxObject construction is deprecated. "
            f"Use class-based stubs from maxpylang.objects instead.\n"
            f"  Example: cycle_tilde(440) instead of MaxObject('cycle~ 440')",
            DeprecationWarning, stacklevel=2
        )
    ...
```

#### 5.2.2 — Modify `maxpylang/maxobjectspec.py` → `__call__`

Pass `_from_spec=True` so the warning doesn't fire for factory-created objects:

```python
return MaxObject(text, _from_spec=True, **extra_attribs)
```

#### 5.2.3 — Modify `maxpylang/tools/patchfuncs/placing.py` → `get_obj_from_spec()`

Add deprecation warning for string args in `place()`:

```python
if isinstance(obj_spec, str):
    warnings.warn(
        f"Passing strings to place() is deprecated. "
        f"Use class-based stubs: place(cycle_tilde(440)) instead of place('cycle~ 440')",
        DeprecationWarning, stacklevel=3
    )
    obj = MaxObject(obj_spec, _from_spec=True)  # suppress double warning
```

Add deprecation warning for uncalled `MaxObjectSpec` in `place()`:

```python
elif isinstance(obj_spec, MaxObjectSpec):
    warnings.warn(
        f"Passing uncalled MaxObjectSpec to place() is deprecated. "
        f"Call it with parentheses: place({obj_spec.max_name}()) instead of place({obj_spec.max_name})",
        DeprecationWarning, stacklevel=3
    )
    obj = obj_spec()
```

---

### Phase 3: Enhanced `edit()` API

**Goal:** Make `edit()` accept native Python arguments, matching the `MaxObjectSpec` pattern.

#### 5.3.1 — Modify `maxpylang/tools/objfuncs/exposed.py` (line 24)

```python
# Before
def edit(self, text_add="append", text=None, **extra_attribs):

# After
def edit(self, *args, text_add="append", text=None, **attribs):
    """
    Edit an object by adding/replacing arguments and attributes.

    New API (class-based):
        obj.edit(440)                    # set/append positional arg
        obj.edit(440, phase=0.5)         # arg + attribute
        obj.edit(text_add="replace", 880)  # replace all args

    Legacy API (still supported):
        obj.edit(text="440")             # text-based append
        obj.edit(text="440", text_add="replace")
    """

    if text is not None:
        # Legacy path — existing behavior unchanged
        ... (current implementation)
    elif args or attribs:
        # New path — convert Python args to text, partition attribs
        new_args = list(args)
        # Partition attribs into text_attribs and extra_attribs
        # using object's reference info (same logic as MaxObjectSpec)
        ...
    else:
        return  # nothing to edit
```

Full backward compatibility: any code using `edit(text="...")` or `edit(**extra_attribs)` works unchanged.

---

### Phase 4: Documentation & Examples

**Goal:** Update all documentation and examples to use the new class-based API.

#### Files to update:

| File | Key Changes |
|------|-------------|
| `CLAUDE.md` | All code examples: string syntax → class-based calls |
| `examples/hello_world/main.py` | `"cycle~ 440"` → `cycle_tilde(440)` |
| `examples/attributes/main.py` | `"metro 500 @active 1"` → `metro(500, active=1)` |
| `examples/random_pitch_generator/tester3.py` | f-string args → Python args in loops |
| `examples/selective-midi-note-generator/tester2.py` | Same pattern |
| `examples/chess-paper-example/...` | Migrate |
| `examples/stocksonification_v1/...` | Migrate |
| `examples/basic-sonification-using-abstracted-csvReader/...` | Migrate |

#### Documentation pattern:

```python
# Before (CLAUDE.md)
osc = patch.place("cycle~ 440")[0]
gain = patch.place(gain_tilde)[0]
dac = patch.place(ezdac_tilde)[0]

# After (CLAUDE.md)
from maxpylang.objects import cycle_tilde, gain_tilde, ezdac_tilde

osc = patch.place(cycle_tilde(440))[0]
gain = patch.place(gain_tilde())[0]
dac = patch.place(ezdac_tilde())[0]
```

---

### Phase 5 (Future): Remove String Syntax

**Goal:** Clean removal after deprecation period.

| Removal | Location |
|---------|----------|
| String branch in `get_obj_from_spec()` | `placing.py` line 389 |
| Direct string `MaxObject.__init__` (public) | `maxobject.py` line 32 (keep `_from_spec` path) |
| `_NAMES` dict | `objects/max.py`, `msp.py`, `jit.py` |
| `text` parameter in `edit()` | `exposed.py` line 24 |
| `_from_spec` parameter | `maxobject.py` (no longer needed) |

**What stays:** `MaxObject(text, _from_spec=True)` — used internally by `MaxObjectSpec.__call__()`. The text-based pipeline is preserved as an internal mechanism; only the public string API is removed.

---

## 6. Edge Cases & Challenges

### 6.1 — Backward Compatibility: `place(stub)` Without Parens

Currently: `patch.place(cycle_tilde)` works because `cycle_tilde` is a `MaxObject`.
After Phase 1: `cycle_tilde` is a `MaxObjectSpec`, not a `MaxObject`.

**Solution:** `get_obj_from_spec()` detects `MaxObjectSpec` and calls it with no args. Phase 2 adds a deprecation warning encouraging `place(cycle_tilde())`.

### 6.2 — Attribute Name Collisions

`cycle~` has both an arg named `frequency` and an attribute named `frequency`. In `MaxObjectSpec.__call__`, positional args go to `*args` and attributes go to `**kwargs` — no collision:

```python
cycle_tilde(440, frequency=220)
# → *args=(440,), **attribs={"frequency": 220}
# → text: "cycle~ 440 @frequency 220"
```

The positional `440` becomes the in-box argument; the keyword `frequency=220` becomes the `@frequency` attribute. This matches how Max itself distinguishes between typed-in arguments and explicitly set attributes.

### 6.3 — Dynamic Argument Building in Loops

Current pattern in examples:
```python
for i in range(voices):
    freqs.append(f"cycle~ {220 * (i+1)}")
    patch.place(freqs[-1])
```

New pattern:
```python
for i in range(voices):
    patch.place(cycle_tilde(220 * (i+1)))
```

### 6.4 — Objects With No Stubs (User Abstractions)

Abstractions are not in the stub files. They continue using `MaxObject` directly:
```python
synth = mp.MaxObject("my_synth 440", abstraction=True, inlets=2, outlets=2)
```
This path is unaffected — `abstraction=True` bypasses the deprecation warning.

### 6.5 — Import Performance

Current: ~1140 `MaxObject` instantiations at import (each reads JSON, creates xlets).
After: ~1140 `MaxObjectSpec` constructions (dict literal storage only).

The JSON data is embedded directly in the generated stub files, so no file I/O happens at import. Expected: 10-50x faster import.

Trade-off: Stub files will be larger (embedded JSON dicts). Currently `msp.py` is ~296KB with ~460 `MaxObject('name')` lines. After embedding specs, each object adds ~200-500 bytes of dict literals. File sizes may roughly double but this is acceptable — they're auto-generated and not meant for human reading.

### 6.6 — Circular Import

`MaxObjectSpec` imports `MaxObject` in `__call__` (deferred import). No circular dependency because:
- `maxobjectspec.py` does NOT import `maxobject` at module level
- `maxobject.py` does NOT import `maxobjectspec` at all
- `objects/*.py` imports `MaxObjectSpec` (one direction only)

---

## 7. File Change Summary

| Phase | File | Action | Lines Affected |
|-------|------|--------|----------------|
| 0 | `maxpylang/maxobjectspec.py` | **CREATE** | ~80 lines |
| 0 | `maxpylang/__init__.py` | Modify | Add 1 import |
| 0 | `maxpylang/tools/patchfuncs/placing.py` | Modify | Lines 110-113, 383-399 |
| 0 | `tests/test_maxobjectspec.py` | **CREATE** | ~60 lines |
| 1 | `maxpylang/importobjs.py` | Modify | Lines 693-796 (`generate_stubs`) |
| 1 | `maxpylang/objects/__init__.py` | Modify | Remove warning suppression |
| 1 | `maxpylang/objects/max.py` | **REGENERATE** | Auto-generated |
| 1 | `maxpylang/objects/msp.py` | **REGENERATE** | Auto-generated |
| 1 | `maxpylang/objects/jit.py` | **REGENERATE** | Auto-generated |
| 2 | `maxpylang/maxobject.py` | Modify | Line 32 (add `_from_spec`) |
| 2 | `maxpylang/maxobjectspec.py` | Modify | `__call__` (pass `_from_spec`) |
| 2 | `maxpylang/tools/patchfuncs/placing.py` | Modify | `get_obj_from_spec` (warnings) |
| 3 | `maxpylang/tools/objfuncs/exposed.py` | Modify | Line 24 (`edit` signature) |
| 4 | `CLAUDE.md` | Modify | All code examples |
| 4 | `examples/*` | Modify | All example scripts |

---

## 8. Verification Plan

### Per-Phase Verification

| Phase | Verification Steps |
|-------|-------------------|
| 0 | Create `MaxObjectSpec` manually, call with args, verify `MaxObject` output matches string-created equivalent. Place in patch, save, open in Max. |
| 1 | `import maxpylang.objects` succeeds. `cycle_tilde` is a `MaxObjectSpec`. `cycle_tilde(440)` produces correct `MaxObject`. Time import (should be much faster). |
| 2 | String syntax still works but prints `DeprecationWarning`. New syntax produces no warnings. |
| 3 | `obj.edit(880)` works. `obj.edit(text="880")` still works. Verify both produce same result. |
| 4 | All examples run successfully with new syntax. Generated patches open correctly in Max. |

### End-to-End Test

```python
import maxpylang as mp
from maxpylang.objects import cycle_tilde, gain_tilde, ezdac_tilde, metro, toggle, pack

patch = mp.MaxPatch()

# Test basic args
osc = patch.place(cycle_tilde(440))[0]
assert osc.name == "cycle~"
assert len(osc.ins) == 2
assert len(osc.outs) == 1

# Test attributes
m = patch.place(metro(500, active=1))[0]
assert "metro 500 @active 1" in m._dict['box']['text']

# Test dynamic I/O
p = patch.place(pack(0, 0, 0))[0]
assert len(p.ins) == 3

# Test no-arg
dac = patch.place(ezdac_tilde())[0]
assert dac.name == "ezdac~"

# Test connections still work
patch.connect([osc.outs[0], dac.ins[0]])

# Test save
patch.save("test_class_api")
# → Open test_class_api.maxpat in Max, verify it works
```
