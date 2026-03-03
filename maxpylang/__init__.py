"""
maxpylang - Python library for creating Max/MSP patches.

Quick start:
    import maxpylang as mp
    patch = mp.MaxPatch()
    osc = patch.place("cycle~ 440")[0]
    dac = patch.place("ezdac~")[0]
    patch.connect([osc.outs[0], dac.ins[0]])
    patch.save("hello_world")

Regenerate stubs (optional, requires Max open):
    mp.import_objs()
    Vanilla stubs (max, msp, jit) ship with the package.
    Use import_objs() to add third-party packages or refresh stubs.
"""

from .tools import constants
from .maxobject import MaxObject
from .maxpatch import MaxPatch
from .importobjs import import_objs
from .xlet import Inlet, Outlet

try:
    from . import objects
except ImportError:
    pass  # objects not yet generated
