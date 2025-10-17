import asyncio
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import aiofiles
import pytest
from langchain_core.messages.ai import AIMessage
from langchain_openai import ChatOpenAI
from unidiff import PatchedFile

from vuli.blackboard import Blackboard
from vuli.common.setting import Setting
from vuli.cp import CP
from vuli.delta import DeltaManager, DeltaReachableAnalyzer, LLMDeltaHandler
from vuli.joern import Joern
from vuli.model_manager import ModelManager
from vuli.sink import Origin, SinkManager, SinkProperty
from vuli.struct import VulInfo


@pytest.fixture(autouse=True)
def setup():
    asyncio.run(Blackboard().clear())
    DeltaManager().clear()


@pytest.mark.asyncio
@patch("vuli.delta.LLMDeltaHandler._condition")
@patch.object(Blackboard, "save", new_callable=AsyncMock)
@patch.object(Joern, "run_query", new_callable=AsyncMock)
@patch.object(ModelManager, "_invoke_atomic")
async def test_llm_handler(handler_1, handler_2, patch_3, patch_4):
    patch_4.return_value = True

    def mock_1(*args, **kwargs) -> Any:
        return AIMessage(
            content="""
```json
[
    {"hunk_number": 1, "line_number_in_hunk": 29, "vulnerability_type": "Infinite loop", "related_code": "i = serverAddr.indexOf(':');"}
]
```"""
        )

    def mock_2(*args, **kwargs) -> Any:
        return [{"id": 0, "v_type": "Infinite loop"}]

    handler_1.side_effect = mock_1
    handler_2.side_effect = mock_2
    await ModelManager().clear()
    await ModelManager().add_model(
        lambda input, output: input * 0.0000025 + output * 0.00001,
        "gpt-4.1",
        ChatOpenAI(api_key="tmp", base_url="url", model="mock", temperature=1.0),
    )
    content = """diff --git a/zookeeper-server/src/main/java/org/apache/zookeeper/server/util/MessageTracker.java b/zookeeper-server/src/main/java/org/apache/zookeeper/server/util/MessageTracker.java
index a81a12b..91952ca 100644
--- a/zookeeper-server/src/main/java/org/apache/zookeeper/server/util/MessageTracker.java
+++ b/zookeeper-server/src/main/java/org/apache/zookeeper/server/util/MessageTracker.java
@@ -105,7 +105,9 @@ private static void logMessages(
         CircularBuffer<BufferedMessage> messages,
         Direction direction) {
         String sentOrReceivedText = direction == Direction.SENT ? "sentBuffer to" : "receivedBuffer from";
-
+        if (serverAddr.contains(":")) {
+            verifyIPv6(serverAddr);
+        }
         if (messages.isEmpty()) {
             LOG.info("No buffered timestamps for messages {} {}", sentOrReceivedText, serverAddr);
         } else {
@@ -116,6 +118,34 @@ private static void logMessages(
         }
     }

+    private static void verifyIPv6(String serverAddr) {
+        int maxColons = 8;
+        int cntColons = 0;
+        int i = serverAddr.indexOf(':');
+        while (i > -1 && i < serverAddr.length() && cntColons < maxColons) {
+            cntColons++;
+            i = serverAddr.indexOf(':', i + 1);
+        }
+        //is there an extra?
+        int extraColons = countExtraColons(i, serverAddr);
+        //count extras
+        if (cntColons > 0 && (cntColons < maxColons || extraColons == 0)) {
+            return;
+        }
+        throw new IllegalArgumentException("bad ipv6: " + serverAddr + " too many colons=" + extraColons);
+    }
+
+    private static int countExtraColons(int i, String serverAddr) {
+        if (i == -1) {
+            return 1;
+        }
+        int cnt = 1;
+        while (i > 0) {
+            cnt++;
+            i = serverAddr.indexOf(':');
+        }
+        return cnt;
+    }
     /**
      * Direction for message track.
      */
diff --git a/zookeeper-server/src/test/java/org/apache/zookeeper/server/util/MessageTrackerTest.java b/zookeeper-server/src/test/java/org/apache/zookeeper/server/util/MessageTrackerTest.java
index d400cf9..9e1d6b3 100644
--- a/zookeeper-server/src/test/java/org/apache/zookeeper/server/util/MessageTrackerTest.java
+++ b/zookeeper-server/src/test/java/org/apache/zookeeper/server/util/MessageTrackerTest.java
@@ -20,6 +20,9 @@

 import static org.junit.jupiter.api.Assertions.assertEquals;
 import static org.junit.jupiter.api.Assertions.assertNull;
+import static org.junit.jupiter.api.Assertions.assertThrows;
+import static org.junit.jupiter.api.Assertions.assertTrue;
+
 import org.junit.jupiter.api.AfterEach;
 import org.junit.jupiter.api.BeforeEach;
 import org.junit.jupiter.api.Test;
@@ -127,4 +130,30 @@ public void testDumpToLog() {
         assertNull(messageTracker.peekSent());
         assertNull(messageTracker.peekReceived());
     }
+
+    @Test
+    public void testIPv6VerificationGood() {
+        MessageTracker messageTracker = new MessageTracker(10);
+        //see https://www.ibm.com/docs/en/ts4500-tape-library?topic=functionality-ipv4-ipv6-address-formats
+        for (String serverAddr : new String[] {
+                "2001:db8:3333:4444:5555:6666:7777:8888",
+                "2001:db8:3333:4444:CCCC:DDDD:EEEE:FFFF",
+                "::", "2001:db8::", "2001:db8::1234:5678",
+                "2001:0db8:0001:0000:0000:0ab9:C0A8:0102"
+        }) {
+            messageTracker.dumpToLog(serverAddr);
+        }
+    }
+
+    @Test
+    public void testIPv6TooManyColons() {
+        final String serverAddr = "2001:db8:1234:0000:0000:0000:0000:0000:0000";
+        MessageTracker messageTracker = new MessageTracker(10);
+        IllegalArgumentException thrown = assertThrows(
+                IllegalArgumentException.class,
+                () -> messageTracker.dumpToLog(serverAddr),
+                "Expected dumpToLog to throw IllegalArgumentException, but it didn't"
+        );
+        assertTrue(thrown.getMessage().contains("too many colons=1"));
+    }
 }"""
    t = tempfile.NamedTemporaryFile()
    async with aiofiles.open(t.name, mode="wt") as f:
        await f.write(content)
        await f.flush()

    CP()._diff_path = Path(t.name)
    Setting().dev = False
    DeltaManager().add(LLMDeltaHandler())
    await DeltaManager().handle()
    result: dict[int, SinkProperty] = await SinkManager().get()
    assert result.get(0) == SinkProperty(
        bug_types=set({"sink-Timeout"}), origins=set({Origin.FROM_DELTA})
    )


@pytest.mark.asyncio
@patch("vuli.delta.LLMDeltaHandler._run", new_callable=AsyncMock)
async def test_llmdeltahandler_no_reachable_harnesses(patch_1):
    Blackboard()._diff_harnesses.clear()
    await LLMDeltaHandler(threashold=-1).handle([])
    assert patch_1._mock_call_count == 0

    Blackboard()._diff_harnesses = set({"Harness"})
    await LLMDeltaHandler(threashold=-1).handle([])
    patch_1.assert_called_once()


@pytest.mark.asyncio
@patch("vuli.delta.LLMDeltaHandler._total_text_len")
@patch("vuli.delta.LLMDeltaHandler._run", new_callable=AsyncMock)
async def test_llmdeltahandler_over_threashold(patch_1, patch_2):
    patch_2.return_value = 2000
    Blackboard()._diff_harnesses = set({"Harness"})
    await LLMDeltaHandler(threashold=1000).handle([])
    assert patch_1._mock_call_count == 0
    await LLMDeltaHandler(threashold=3000).handle([])
    patch_1.assert_called_once()


@pytest.mark.asyncio
@patch("vuli.delta.DeltaReachableAnalyzer._find_path", new_callable=AsyncMock)
@patch.object(CP, "get_harnesses")
@patch("vuli.delta.LLMDeltaHandler._run", new_callable=AsyncMock)
@patch.object(Blackboard, "_save", new_callable=AsyncMock)
@patch("vuli.delta.DeltaReachableAnalyzer._collect_methods", new_callable=AsyncMock)
@patch.object(DeltaManager, "_get_patched_file", new_callable=AsyncMock)
async def test_llmdeltahandler_no_reachable_harness_in_workflow(
    patch_1, patch_2, patch_3, patch_4, patch_5, patch_6
):
    patch_1.return_value = [PatchedFile()]
    patch_2.return_value = [{"id": "1", "name": "name", "line": "10"}]
    patch_3.return_value = None
    patch_5.return_value = set()
    DeltaManager().clear()
    DeltaManager().add(DeltaReachableAnalyzer(), LLMDeltaHandler())
    await DeltaManager().handle()
    assert patch_4._mock_call_count == 0

    patch_5.return_value = set({"Harness"})
    patch_6.return_value = [
        VulInfo(harness_id="Harness", sink_id=1, v_paths=[], v_point=None)
    ]
    await DeltaManager().handle()
    patch_4.assert_called_once()


@pytest.mark.asyncio
@patch.object(Blackboard, "_save", new_callable=AsyncMock)
async def test_llmdeltahandler_total_text_len(patch_1):
    class TestHandler(LLMDeltaHandler):
        def __init__(self):
            super().__init__()
            self._result: int = 0

        async def _run(self, patched_files: list[PatchedFile]) -> None:
            self._result = self._total_text_len(patched_files)

    content = """--- a/a.java
+++ b/a.java
@@ -105,6 +105,9 @@
 1
 2
 3
+4
+5
+6
 7
 8
 9
"""
    t = tempfile.NamedTemporaryFile()
    async with aiofiles.open(t.name, mode="wt") as f:
        await f.write(content)
        await f.flush()
    CP()._diff_path = Path(t.name)
    Setting().dev = False
    Blackboard()._diff_harnesses = set({"Harness"})
    handler = TestHandler()
    DeltaManager().add(handler)
    await DeltaManager().handle()
    assert handler._result == 27
