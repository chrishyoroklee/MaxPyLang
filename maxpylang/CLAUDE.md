# MaxPyLang

Python library for programmatically creating and editing Max/MSP patches (`.maxpat` files).

## Quick Start

```python
import maxpylang as mp

patch = mp.MaxPatch()
osc = patch.place("cycle~ 440")[0]
dac = patch.place("ezdac~")[0]
patch.connect([osc.outs[0], dac.ins[0]])
patch.save("hello_world")
```

## Core API

### MaxPatch

```python
patch = mp.MaxPatch(template=None, load_file=None, reorder=True, verbose=True)
```

- `template` — path to a `.maxpat` template file
- `load_file` — path to an existing `.maxpat` to load and modify

**Methods:**

```python
patch.place(*objs, num_objs=1, spacing_type="grid", spacing=[80,80],
            starting_pos=None, verbose=False) -> list[MaxObject]
```
Places objects in the patch. Always returns a **list** — use `[0]` for a single object.

```python
patch.connect(*connections, verbose=True)
```
Each connection is `[outlet, inlet]`: `patch.connect([obj1.outs[0], obj2.ins[0]])`.

```python
patch.save(filename="default.maxpat", verbose=True, check=True)
```
Auto-appends `.maxpat` if missing.

```python
patch.set_position(new_x, new_y)
```
Moves the internal cursor for next placement.

**Properties:** `patch.objs` (dict), `patch.num_objs` (int), `patch.curr_position` (list)

### MaxObject

```python
obj = mp.MaxObject("cycle~ 440")
obj = mp.MaxObject("metro 500 @active 1")   # with attributes
```

**Properties:**
- `obj.name` — object class name (e.g. `"cycle~"`)
- `obj.ins` — list of Inlets (0-indexed)
- `obj.outs` — list of Outlets (0-indexed)

**Methods:**
```python
obj.edit(text_add="append", text=None, **extra_attribs)  # modify object
obj.move(x, y)                                           # reposition
```

### Connections

Inlets and outlets are 0-indexed. Wire them with `connect()`:

```python
patch.connect([src.outs[0], dst.ins[0]])          # single connection
patch.connect([a.outs[0], b.ins[0]],
              [b.outs[0], c.ins[0]])               # multiple connections
```

## Stub Objects

Pre-instantiated MaxObject stubs for IDE autocomplete:

```python
from maxpylang.objects import cycle_tilde, ezdac_tilde, metro, toggle
```

**Naming rules:**
| Max name | Python name | Rule |
|----------|------------|------|
| `cycle~` | `cycle_tilde` | `~` becomes `_tilde` |
| `jit.movie` | `jit_movie` | `.` becomes `_` |
| `live.dial` | `live_dial` | `-` becomes `_` |
| `2d.wave~` | `_2d_wave_tilde` | leading digit gets `_` prefix |
| `in` | `in_` | Python keyword gets `_` suffix |

Stubs are real MaxObjects — pass them directly to `place()`:

```python
osc = patch.place(cycle_tilde)[0]   # equivalent to patch.place("cycle~")[0]
```

Stubs have no arguments. Use `edit()` to add them, or use string syntax when you need arguments:

```python
# stub (no args) — use for objects that don't need arguments
dac = patch.place(ezdac_tilde)[0]

# string (with args) — simpler when arguments are needed
osc = patch.place("cycle~ 440")[0]
```

## Common Patterns

### Audio chain

```python
from maxpylang.objects import gain_tilde, ezdac_tilde

patch = mp.MaxPatch()
osc = patch.place("cycle~ 440")[0]        # string syntax: has arguments
gain = patch.place(gain_tilde)[0]          # stub syntax: no arguments needed
dac = patch.place(ezdac_tilde)[0]          # stub syntax: no arguments needed
patch.connect([osc.outs[0], gain.ins[0]],
              [gain.outs[0], dac.ins[0]],
              [gain.outs[0], dac.ins[1]])
patch.save("audio_chain")
```

### Multiple objects with loops

```python
n = 10
toggles = patch.place("toggle", num_objs=n, starting_pos=[0, 100])
gates = patch.place("gate", num_objs=n, starting_pos=[0, 200])

for t, g in zip(toggles, gates):
    patch.connect([t.outs[0], g.ins[0]])
```

### Attributes via `@` syntax

```python
patch.place("metro 500 @active 1")[0]
patch.place("jit.movie @moviefile crashtest.mov")[0]
```

### Loading and modifying existing patches

```python
patch = mp.MaxPatch(load_file="existing.maxpat")
for key, obj in patch.objs.items():
    print(obj.name)
patch.save("modified")
```

## Key Rules

- `place()` **always returns a list** — use `[0]` for single objects
- Object names are **case-sensitive** and must match Max names exactly
- Coordinates are floats
- `save()` auto-appends `.maxpat`
- `verbose=False` suppresses console output
- Inlet/outlet indices are **0-based**

## Patch Layout

Call `set_position(x, y)` **before every `place()` call**. Without it, objects pile up and cords cross.

```python
Y_STEP = 40       # between objects in a chain
SECTION_GAP = 80  # between logical sections
COL_WIDTH = 150   # between parallel columns

patch.set_position(30, 100)
osc = patch.place("cycle~")[0]

patch.set_position(30, 140)          # +Y_STEP
filt = patch.place("lores~")[0]

patch.set_position(30 + COL_WIDTH, 100)  # parallel column
lfo = patch.place("cycle~ 2")[0]
```

**Rules:**
- Top-to-bottom signal flow (increasing `y`)
- Parallel chains side by side (same `y`, different `x`)
- Labels (`comment`) 20px above their object
- Section headers: `patch.place("comment === SECTION NAME ===")`
- `loadbang`/defaults to the right of main flow
- Group `connect()` calls by section, not scattered throughout
