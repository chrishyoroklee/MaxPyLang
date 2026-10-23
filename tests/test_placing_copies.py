"""Placing an object never aliases a stub or an object already in a patch."""

import warnings

import pytest

import maxpylang as mp
from maxpylang.objects import cycle_tilde, metro


@pytest.fixture(autouse=True)
def _quiet():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        yield


def test_calling_a_stub_builds_a_new_object_with_args():
    osc = cycle_tilde(440)
    assert osc is not cycle_tilde
    assert osc.name == "cycle~"
    assert osc._args == [440]
    assert cycle_tilde._args == []


def test_calling_a_stub_turns_keywords_into_box_attributes():
    met = metro(500, active=1)
    assert met._args == [500]
    assert met._text_attribs == {"active": ["1"]}


def test_placing_a_stub_twice_gives_two_objects():
    patch = mp.MaxPatch(verbose=False)
    a = patch.place(cycle_tilde)[0]
    b = patch.place(cycle_tilde)[0]
    assert a is not b
    assert a is not cycle_tilde and b is not cycle_tilde


def test_placing_a_stub_leaves_the_stub_unplaced():
    patch = mp.MaxPatch(verbose=False)
    osc = patch.place(cycle_tilde)[0]
    patch.connect((osc.outs[0], osc.ins[0]), verbose=False)
    assert cycle_tilde.outs[0].destinations == []


def test_placing_one_object_many_times_gives_distinct_objects():
    patch = mp.MaxPatch(verbose=False)
    obj = mp.MaxObject("cycle~ 440")
    placed = patch.place(obj, num_objs=3)
    assert placed[0] is obj
    assert len({id(o) for o in placed}) == 3
    assert patch.objs == {"obj-1": placed[0], "obj-2": placed[1], "obj-3": placed[2]}
