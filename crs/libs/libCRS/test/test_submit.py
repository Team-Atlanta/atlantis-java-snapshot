from libCRS import Config, CP, CRS, Module, HarnessRunner, util

from helper import set_up_cp


def check_vapi_result():
    return util.run_cmd(["python3", "-m", "libCRS.submit", "check"])

def get_submit_result():
    ret = util.run_cmd(["python3", "-m", "libCRS.submit", "show"])
    return ret.stdout.decode("utf-8")

class Module1(Module):
    def _init(self):
        return

    async def _async_prepare(self):
        self.log("Prepare")

    async def _async_run(self, hrunner: HarnessRunner):
        self.logH(hrunner, "Run")
        workdir = hrunner.get_workdir("Module1")
        pov = workdir / "pov"
        with open(pov, "wb") as f: f.write(b"AAAA")
        await hrunner.async_submit_pov(pov, finder = "Module1")

    async def _async_test(self, hrunner: HarnessRunner):
        self.logH(hrunner, "Test")

    async def _async_get_mock_result(self, hrunner: HarnessRunner | None):
        pass

class SampleHR(HarnessRunner):
    async def async_run(self):
        await self.crs.Module1.async_run(self)

class SampleCRS(CRS):
    def __init__(self, target_cp_name: str, *args, **kwargs):
        self.target_cp_name = target_cp_name
        super().__init__(*args, **kwargs)

    def _is_target_cp(self, cp: CP) -> bool:
        return cp.name == self.target_cp_name

    def _init_modules(self) -> list[Module]:
        return [Module1("Module1", self)]

    async def _async_prepare(self):
        self.log("Prepare")
        await self.async_prepare_modules()

def test_crs(shared_cp_root, shared_crs_scratch_space, sample_cp_info, tmp_path):
    conf = Config(0, 1)
    cp = set_up_cp(shared_cp_root, sample_cp_info)
    crs = SampleCRS(sample_cp_info.name, "SampleCRS", SampleHR, conf, tmp_path)
    crs.run()

    assert check_vapi_result().returncode == 0

    result = get_submit_result()
    print(result)
    for harness in crs.cp.harnesses.keys():
        assert harness in result
