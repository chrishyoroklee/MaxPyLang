"""Generated files in maxpylang/objects match what their generators produce now."""

from pathlib import Path

from maxpylang.importobjs import build_objects_init

OBJECTS = Path(__file__).resolve().parents[1] / "maxpylang" / "objects"


def test_objects_init_matches_generator():
    assert (OBJECTS / "__init__.py").read_text() == build_objects_init(["jit", "max", "msp"])


def test_stub_module_puts_each_docstring_after_its_stub():
    from maxpylang.importobjs import build_stub_module

    text = build_stub_module("msp", {"cycle_tilde": "cycle~"},
                             {"cycle~": {"doc": {"digest": "Sinusoidal oscillator"}}})
    assert "cycle_tilde = MaxObject('cycle~')\n\"\"\"\ncycle~ - Sinusoidal oscillator\n\"\"\"" in text
