from bmssp import DQueue

def test_dqueue_prepend_sorted():
    dq = DQueue(M=2, B=10)
    # Unsordered prepends: distances 5,1,3
    dq.batch_prepend([
        ("x", 5.0),
        ("y", 1.0),
        ("z", 3.0),
    ])
    B_i, nodes = dq.pull()
    assert B_i == 1.0
    assert nodes == {"y", "z"}
