from libDeepGen.tasks import ScriptSelector

def test_script_selector():
    selector = ScriptSelector("/home/hanqing/aixcc/libDeepGen/workdir-libDeepGen/summary.json")
    x, y, z = selector.pick_next_script()
    assert x is not None
    assert y is not None
    assert z is not None
    x2, y2, z2 = selector.pick_next_script()
    assert x == x2
    assert y == y2
    assert z == z2
    print(x, y)
    print(x2, y2)