from helper import set_up_cp


def test_build(shared_cp_root, sample_cp_infos):
    for cp_info in sample_cp_infos:
        cp = set_up_cp(shared_cp_root, cp_info)
        assert cp.build()
