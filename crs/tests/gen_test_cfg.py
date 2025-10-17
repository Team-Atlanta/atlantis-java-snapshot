import json
import os

data = {}

data["ttl_fuzz_time"] = int(os.getenv("CRS_TTL_TIME", 60))
print("CRS test cfg, used time limit: " + str(data["ttl_fuzz_time"]))

harness = os.getenv("CRS_HARNESS") or ""
if not harness:
    print("ERROR: No target harnesses specified (CRS_HARNESS), exiting")
    os._exit(1)
if harness != "*":
    data["target_harnesses"] = [h.strip() for h in harness.strip().split(",")]
    print("CRS test cfg, used target harnesses: " + str(data["target_harnesses"]))
else:
    data.pop("target_harnesses", None)
    print("CRS test cfg, no target harnesses specified, using all harnesses")

with open("/tmp/test.config", "w") as f:
    json.dump(data, f, indent=2)
print("CRS test cfg, written to /tmp/test.config: \n" + str(data))
