# libCRS

# How to install
```
pip install .
```

# How to submit POVs
- If you have HarnessRunner object, check the following methods
  - `HarnessRunner.async_submit_pov`
  - `HarnessRunner.async_submit_povs`
  - `HarnessRunner.async_loop_submit_povs`
- If you have CRS object, check the following methods
  - `CRS.async_submit_pov`
  - `CRS.submit_pov`
- If you want to submit without HarnessRunner and CRS,
```
export TARGET_CP=<target cp name> // libCRS will append this if your module is executed by libCRS.

python3 -m libCRS.submit submit_vd
        --harness <harness_id>
        --pov <pov_path>
        --sanitizer-output <OPTIONAL, key for the uniquenss of PoV>
        --finder <OPTIONAL, finder of this pov>
```

# How to submit GPs
```
python3 -m libCRS.submit submit_gp
        --cpv-uuid <cpv-uuid>
        --patch <path to patch file>
        --finder <OPTIONAL, finder of this patch>
```

# How to check submission results
```
python3 -m libCRS.submit show
```
