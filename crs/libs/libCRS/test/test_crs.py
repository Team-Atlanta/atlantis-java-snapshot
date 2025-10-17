from libCRS import Config, CP, CRS, Module, LLM_Module, HarnessRunner

from helper import set_up_cp


class Module1(Module):
    def _init(self):
        return

    async def _async_prepare(self):
        self.log("Prepare")

    async def _async_run(self, hrunner: HarnessRunner):
        self.logH(hrunner, "Run")

    async def _async_test(self, hrunner: HarnessRunner):
        self.logH(hrunner, "Test")

    async def _async_get_mock_result(self, hrunner: HarnessRunner | None):
        pass

class Module2(Module):
    def _init(self):
        return

    async def _async_prepare(self):
        self.log("Prepare")

    async def _async_run(self, hrunner: HarnessRunner):
        self.logH(hrunner, "Run")

    async def _async_test(self, hrunner: HarnessRunner):
        self.logH(hrunner, "Test")

    async def _async_get_mock_result(self, hrunner: HarnessRunner | None):
        pass

class Module3(LLM_Module):
    def _init(self):
        return

    async def _async_prepare(self):
        self.log("Prepare")

    async def _async_run(self, hrunner: HarnessRunner):
        self.logH(hrunner, "Run")

    async def _async_test(self, hrunner: HarnessRunner):
        self.logH(hrunner, "Test")

    async def _async_get_mock_result(self, hrunner: HarnessRunner | None):
        pass

class SampleHR(HarnessRunner):
    async def async_run(self):
        await self.crs.Module1.async_run(self)
        await self.crs.Module2.async_run(self)
        await self.crs.Module3.async_run(self)

class SampleCRS(CRS):
    def __init__(self, target_cp_name: str, *args, **kwargs):
        self.target_cp_name = target_cp_name
        super().__init__(*args, **kwargs)

    def _is_target_cp(self, cp: CP) -> bool:
        return cp.name == self.target_cp_name

    def _init_modules(self) -> list[Module]:
        return [Module1("Module1", self), Module2("Module2", self), Module3("Module3", self)]

    async def _async_prepare(self):
        self.log("Prepare")
        await self.async_prepare_modules()

def test_crs(shared_cp_root, shared_crs_scratch_space, sample_cp_info, tmp_path):
    conf = Config(0, 1)
    cp = set_up_cp(shared_cp_root, sample_cp_info)
    crs = SampleCRS(sample_cp_info.name, "SampleCRS", SampleHR, conf, tmp_path)
    crs.run()
