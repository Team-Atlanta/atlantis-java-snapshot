from abc import ABC, abstractmethod
import asyncio
import logging
from pathlib import Path
import sys

from .crs import CRS, HarnessRunner
from .util import async_run_cmd

__all__ = ["Module", "LLM_Module"]


class Module(ABC):
    def __init__(self, name: str, crs: CRS, run_per_harness: bool = True):
        self.name = name
        self.crs = crs
        self.prepared = False
        self.done = {}
        self.run_per_harness = run_per_harness
        self.tests_without_harness = []
        self.tests_with_harness = []

    def get_workdir(self, name: str) -> Path:
        return self.crs.get_workdir(f"{self.name}/{name}")

    def is_on(self) -> bool:
        return self.crs.config.is_module_on(self.name)

    def log(
        self,
        msg: str,
        prefix: str | None = None,
        postfix: str | None = None,
        is_err=False,
    ):
        log = logging.error if is_err else logging.info
        if prefix:
            return log(f"[{prefix}][{self.name}] {msg}")
        if postfix:
            return log(f"[{self.name}][{postfix}] {msg}")
        return log(f"[{self.name}] {msg}")

    def logH(self, hrunner: HarnessRunner | None, msg: str, is_err=False):
        if hrunner:
            self.log(msg, hrunner.harness.name, is_err=is_err)
        else:
            self.log(msg, is_err=is_err)

    async def async_prepare(self):
        if self.is_on() and not self.prepared:
            await self._async_prepare()
        self.prepared = True
        if self.crs.config.test and self.crs.config.test_wo_harness:
            await self.__async_test(None)

    def prepare(self):
        return asyncio.run(self.async_prepare())

    async def async_wait_prepared(self):
        while not self.prepared:
            await asyncio.sleep(1)

    def wait_prepared(self):
        return asyncio.run(self.async_wait_prepared())

    async def async_wait_done(self, hrunner: HarnessRunner | None = None):
        while hrunner not in self.done:
            await asyncio.sleep(1)

    def wait_done(self, hrunner: HarnessRunner | None = None):
        return asyncio.run(self.async_wait_done(hrunner))

    async def async_run(self, harness_runner: HarnessRunner | None = None):
        if self.run_per_harness ^ (harness_runner is not None):
            return
        if not self.is_on():
            self.logH(harness_runner, "Skip running and use mock result")
            ret = await self._async_get_mock_result(harness_runner)
        else:
            await self.async_wait_prepared()
            if self.crs.config.test:
                ret = await self.__async_test(harness_runner)
            else:
                ret = await self._async_run(harness_runner)
        self.done[harness_runner] = True
        return ret

    def run(self, harness_runner: HarnessRunner | None = None):
        return asyncio.run(self.async_run(harness_runner))

    async def __async_test(self, harness_runner: HarnessRunner | None = None) -> bool:
        if harness_runner == None:
            tests = self.tests_without_harness
            postfix = "tests w/o harness"
        else:
            tests = self.tests_with_harness
            postfix = f"tests w/ {harness_runner.harness.name}"
        if len(tests) == None:
            if harness_runner == None:
                self.logH(harness_runner, "Does not have tests_without_harness")
            else:
                self.logH(harness_runner, "Does not have tests_with_harness")
            return True
        for test in tests:
            if harness_runner == None:
                ret = await test()
            else:
                ret = await test(harness_runner)
            self.log(str(ret), postfix=postfix, is_err=not ret.is_passed)
            if not ret.is_passed:
                sys.exit(-1)
                return False
        return True

    async def async_test(self, harness_runner: HarnessRunner | None = None) -> bool:
        if not self.is_on():
            return False
        await self.async_wait_prepared()
        return self.__async_test(harness_runner)

    def test(self, harness_runner: HarnessRunner | None = None) -> bool:
        return asyncio.run(self.async_test(harness_runner))

    @abstractmethod
    async def _init(self):
        pass

    @abstractmethod
    async def _async_prepare(self):
        pass

    @abstractmethod
    async def _async_run(self, harness_runner: HarnessRunner | None):
        pass

    @abstractmethod
    async def _async_get_mock_result(self, harness_runner: HarnessRunner | None):
        pass


class LLM_Module(Module):
    def is_on(self) -> bool:
        return self.crs.config.llm_on and self.crs.config.is_module_on(self.name)

    async def async_run_llm_cmd(self, msg: str, *args, **kwargs):
        async with self.crs.llm_lock:
            if await self.crs.async_in_llm_limit():
                self.log(msg)
                return await async_run_cmd(*args, **kwargs)
            else:
                self.log("Out of LLM credit")
