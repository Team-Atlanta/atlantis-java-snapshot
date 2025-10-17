from threading import Thread

from libCRS import Config

from helper import set_up_cp


def helper_test_distribute(node_cnt, cp, workdir):
    # Call Config.distribute() in separate threads to test for possible
    # race conditions (since it writes config files to disk)
    jobs = []
    confs = []
    for idx in range(node_cnt): confs.append(Config(idx, node_cnt))
    for c in confs:
        jobs.append(Thread(target=c.distribute, args=[cp, workdir]))
    for job in jobs: job.start()
    for job in jobs: job.join()

    # Check that all nodes have at least one harness
    assert all(x.target_harness for x in confs)

    # Check that all harnesses are assigned to a node
    all_harness_names = set(h.name for h in cp.harnesses.values())
    all_assigned_harnesses = set(x for conf in confs for x in conf.target_harness)
    assert all_assigned_harnesses == all_harness_names

    # Check that harnesses are distributed evenly (if the number of nodes doesn't
    # evenly divide the number of harnesses, some nodes may have 1 more than others)
    fewest = min(len(x.target_harness) for x in confs)
    assert all(len(x.target_harness) in {fewest, fewest + 1} for x in confs)

def test_distribute(shared_cp_root, sample_cp_infos, tmp_path):
    for cp_info in sample_cp_infos:
        cp = set_up_cp(shared_cp_root, cp_info)
        helper_test_distribute(2, cp, tmp_path)
