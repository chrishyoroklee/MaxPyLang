"""
Static checks on connect(), run by tests/test_static_types.py under ty and mypy.

Every line ending in `# error` must be flagged, and no other line may be.
"""

import maxpylang as mp
from maxpylang.objects import (
    average_tilde,
    cycle_tilde,
    ezdac_tilde,
    flonum,
    jit_graph,
    mc_cycle_tilde,
    metro,
    send_tilde,
    snapshot_tilde,
    toggle,
)

patch = mp.MaxPatch()
osc = patch.place(cycle_tilde(440))[0]
mc = patch.place(mc_cycle_tilde)[0]
dac = patch.place(ezdac_tilde)[0]
avg = patch.place(average_tilde)[0]
snap = patch.place(snapshot_tilde)[0]
num = patch.place(flonum)[0]
met = patch.place(metro(500, active=1))[0]
tog = patch.place(toggle)[0]
snd_sig = patch.place(send_tilde("audio"))[0]
graph = patch.place(jit_graph)[0]

# valid
patch.connect((osc.outs[0], dac.ins[0]), (osc.outs[0], dac.ins[1]))
patch.connect((met.outs[0], osc.ins[0]))  # control into an audio inlet is never flagged
patch.connect((mc.outs[0], dac.ins[0]))  # multichannel audio into an audio inlet
patch.connect((avg.outs[0], snap.ins[0]), (snap.outs[0], num.ins[0]))
patch.connect((osc.outs[0], snd_sig.ins[0]), (tog.outs[0], met.ins[0]))
patch.connect((osc.outs[0], dac.ins[0], [[10.0, 20.0]]), verbose=False)  # with midpoints
patch.connect([osc.outs[0], num.ins[0]])  # list form: checked only at runtime
patch.connect([osc.outs[0], dac.ins[0]], (met.outs[0], osc.ins[1]))
untyped = patch.place("sig~ 1")[0]
patch.connect((untyped.outs[0], num.ins[0]))  # string-placed objects are not typed

# audio into a control-only inlet
patch.connect((osc.outs[0], num.ins[0]))  # error
patch.connect((avg.outs[0], num.ins[0]))  # error
patch.connect((osc.outs[0], tog.ins[0]))  # error
patch.connect((osc.outs[0], graph.ins[0]))  # error
patch.connect((met.outs[0], osc.ins[0]), (osc.outs[0], num.ins[0]))  # error
patch.connect([met.outs[0], osc.ins[0]], (osc.outs[0], num.ins[0]))  # error

# index past a fixed count
patch.connect((tog.outs[3], met.ins[0]))  # error
patch.connect((tog.outs[0], met.ins[2]))  # error

# malformed
patch.connect((met.ins[0], tog.outs[0]))  # error
