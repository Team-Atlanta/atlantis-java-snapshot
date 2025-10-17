# JavaCRSParams

JSON Schema missing a description, provide it using the `description` key in the root of the JSON document.

### Type: `object`

| Property         | Type              | Required | Possible values               | Deprecated | Default | Description                                                                                                                          | Examples |
| ---------------- | ----------------- | -------- | ----------------------------- | ---------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------ | -------- |
| modules          | `object`          | ✅       | [ModuleParams](#moduleparams) |            |         | Module parameters.                                                                                                                   |          |
| ttl_fuzz_time    | `integer`         | ✅       | integer                       |            |         | **Mandatory**, a positive integer for JavaCRS execution time in seconds.                                                             |          |
| e2e_check        | `boolean`         |          | boolean                       |            | `false` | **Optional**, if set, enable e2e check (per 10m) for JavaCRS. Default is False.                                                      |          |
| sync_log         | `boolean`         |          | boolean                       |            | `false` | **Optional**, if set, enable sync log to NFS right after e2e. Default is False.                                                      |          |
| target_harnesses | `array` or `null` |          | string                        |            | `null`  | **Optional**, if set, only the harness in target list will be ran in this CRS. By default is None, allowing any harness.             |          |
| verbose          | `boolean`         |          | boolean                       |            | `false` | **Optional**, verbose log mode. Default is False.                                                                                    |          |
| workdir          | `string`          |          | string                        |            | `null`  | **Optional**, JavaCRS working directory. If not set, it will be `${CRS_WORKDIR:-/crs-workdir}/worker-${NODE_IDX}` in bash semantics. |          |

______________________________________________________________________

# Definitions

## AIxCCJazzerParams

No description provided for this model.

#### Type: `object`

| Property    | Type                | Required | Possible values | Deprecated | Default   | Description                                                              | Examples |
| ----------- | ------------------- | -------- | --------------- | ---------- | --------- | ------------------------------------------------------------------------ | -------- |
| enabled     | `boolean`           | ✅       | boolean         |            |           | **Mandatory**, true/false to enable/disable this module.                 |          |
| keep_seed   | `boolean`           | ✅       | boolean         |            |           | **Mandatory**, true/false to keep the seed file.                         |          |
| len_control | `integer`           |          | integer         |            | `0`       | **Optional**, libfuzzer -len_control param. Default: 0.                  |          |
| max_len     | `integer` or `null` |          | integer         |            | `1048576` | **Optional**, libfuzzer -max_len param. If unset, will be 1048576 (1M).  |          |
| mem_size    | `integer`           |          | integer         |            | `4096`    | **Optional**, memory size in MB. Default value is 4096, require >= 2048. |          |

## AtlDirectedJazzerParams

No description provided for this model.

#### Type: `object`

| Property         | Type                | Required | Possible values | Deprecated | Default   | Description                                                                                                 | Examples |
| ---------------- | ------------------- | -------- | --------------- | ---------- | --------- | ----------------------------------------------------------------------------------------------------------- | -------- |
| deepgen_consumer | `boolean`           | ✅       | boolean         |            |           | **Mandatory**, true/false to enable/disable consuming seeds from deepgen module.                            |          |
| enabled          | `boolean`           | ✅       | boolean         |            |           | **Mandatory**, true/false to enable/disable this module.                                                    |          |
| keep_seed        | `boolean`           | ✅       | boolean         |            |           | **Mandatory**, true/false to keep the seed file.                                                            |          |
| beepseed_search  | `boolean`           |          | boolean         |            | `false`   | **Optional**, true/false to enable/disable beepseed search.                                                 |          |
| directed_time    | `integer` or `null` |          | integer         |            | `null`    | **Optional**, directed fuzzing directed phase time in seconds (positive integer). Default value is None.    |          |
| exploration_time | `integer` or `null` |          | integer         |            | `null`    | **Optional**, directed fuzzing exploration phase time in seconds (positive integer). Default value is None. |          |
| len_control      | `integer`           |          | integer         |            | `0`       | **Optional**, libfuzzer -len_control param. Default: 0.                                                     |          |
| max_len          | `integer` or `null` |          | integer         |            | `1048576` | **Optional**, libfuzzer -max_len param. If unset, will be 1048576 (1M).                                     |          |
| mem_size         | `integer`           |          | integer         |            | `4096`    | **Optional**, memory size in MB. Default value is 4096, require >= 2048.                                    |          |

## AtlJazzerParams

No description provided for this model.

#### Type: `object`

| Property         | Type                | Required | Possible values | Deprecated | Default   | Description                                                                      | Examples |
| ---------------- | ------------------- | -------- | --------------- | ---------- | --------- | -------------------------------------------------------------------------------- | -------- |
| deepgen_consumer | `boolean`           | ✅       | boolean         |            |           | **Mandatory**, true/false to enable/disable consuming seeds from deepgen module. |          |
| enabled          | `boolean`           | ✅       | boolean         |            |           | **Mandatory**, true/false to enable/disable this module.                         |          |
| keep_seed        | `boolean`           | ✅       | boolean         |            |           | **Mandatory**, true/false to keep the seed file.                                 |          |
| beepseed_search  | `boolean`           |          | boolean         |            | `false`   | **Optional**, true/false to enable/disable beepseed search.                      |          |
| len_control      | `integer`           |          | integer         |            | `0`       | **Optional**, libfuzzer -len_control param. Default: 0.                          |          |
| max_len          | `integer` or `null` |          | integer         |            | `1048576` | **Optional**, libfuzzer -max_len param. If unset, will be 1048576 (1M).          |          |
| mem_size         | `integer`           |          | integer         |            | `4096`    | **Optional**, memory size in MB. Default value is 4096, require >= 2048.         |          |

## AtlLibAFLJazzerParams

No description provided for this model.

#### Type: `object`

| Property        | Type                | Required | Possible values | Deprecated | Default   | Description                                                              | Examples |
| --------------- | ------------------- | -------- | --------------- | ---------- | --------- | ------------------------------------------------------------------------ | -------- |
| enabled         | `boolean`           | ✅       | boolean         |            |           | **Mandatory**, true/false to enable/disable this module.                 |          |
| keep_seed       | `boolean`           | ✅       | boolean         |            |           | **Mandatory**, true/false to keep the seed file.                         |          |
| beepseed_search | `boolean`           |          | boolean         |            | `false`   | **Optional**, true/false to enable/disable beepseed search.              |          |
| len_control     | `integer`           |          | integer         |            | `0`       | **Optional**, libfuzzer -len_control param. Default: 0.                  |          |
| max_len         | `integer` or `null` |          | integer         |            | `1048576` | **Optional**, libfuzzer -max_len param. If unset, will be 1048576 (1M).  |          |
| mem_size        | `integer`           |          | integer         |            | `4096`    | **Optional**, memory size in MB. Default value is 4096, require >= 2048. |          |

## CPUAllocatorParams

No description provided for this model.

#### Type: `object`

| Property         | Type      | Required | Possible values | Deprecated | Default | Description                                                                                                                                                                               | Examples |
| ---------------- | --------- | -------- | --------------- | ---------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| cpubaseno        | `integer` |          | integer         |            | `0`     | **Optional**, a non-negative integer with default value 0, the base index to start allocating CPU cores.                                                                                  |          |
| jazzer_cpu_ratio | `number`  |          | number          |            | `0.8`   | **Optional**, a float in [0, 1] with default value 0.8, the ratio of CPU cores allocated to Jazzer modules, will be override by `jazzer_ncpu` if specified.                               |          |
| jazzer_ncpu      | `integer` |          | integer         |            | `0`     | **Optional**, a non-negative integer with default value 0 which means use the `jazzer_cpu_ratio`. It exactly specifies the number of CPU cores allocated to Jazzer modules.               |          |
| maxncpu          | `integer` |          | integer         |            | `0`     | **Optional**, a non-negative integer with default value 0 specifying the maximum number of CPU cores to allocate. If `maxncpu == 0 or maxncpu > os.cpu_count`, it will be `os.cpu_count`. |          |
| skipped_mods     | `array`   |          | string          |            | `[]`    | **Optional**, a list of module names to skip, default is an empty list. The skipped modules will share all CPU cores. `cpuallocator` module is always skipped.                            |          |
| ttl_core_ids     | `array`   |          | integer         |            | `[]`    | **Optional**, total list of CPU core ids used for this CRS instance. If specified, `cpubaseno` and `maxncpu` will be override. This eaze the evaluation.                                  |          |

## CodeQLParams

No description provided for this model.

#### Type: `object`

| Property | Type      | Required | Possible values | Deprecated | Default | Description                                                 | Examples |
| -------- | --------- | -------- | --------------- | ---------- | ------- | ----------------------------------------------------------- | -------- |
| enabled  | `boolean` | ✅       | boolean         |            |         | **Mandatory**, true/false to enable or disable this module. |          |

## ConcolicExecutorParams

No description provided for this model.

#### Type: `object`

| Property     | Type      | Required | Possible values | Deprecated | Default | Description                                                                                                                     | Examples |
| ------------ | --------- | -------- | --------------- | ---------- | ------- | ------------------------------------------------------------------------------------------------------------------------------- | -------- |
| enabled      | `boolean` | ✅       | boolean         |            |         | **Mandatory**, true/false to enable/disable this module.                                                                        |          |
| generators   | `array`   | ✅       | string          |            |         | **Mandatory**, list of concolic request generators to use. Valid values: 'dummy-seed', 'local_dir', 'new-cov-seed', 'beepseed'. |          |
| debug        | `boolean` |          | boolean         |            | `false` | Enable debugging mode. When enabled, writes requests to debug_dir.                                                              |          |
| exec_timeout | `integer` |          | integer         |            | `1200`  | Timeout for one round execution of the target harness in concolic engine (in seconds).                                          |          |
| max_mem      | `integer` |          | integer         |            | `16384` | Maximum memory for the concolic server (in MB).                                                                                 |          |
| max_xms      | `integer` |          | integer         |            | `8192`  | Maximum heap size for the concolic server (in MB).                                                                              |          |
| num_instance | `integer` |          | integer         |            | `1`     | Number of instances concolic server maintains per harness.                                                                      |          |

## CrashManagerParams

No description provided for this model.

#### Type: `object`

| Property | Type      | Required | Possible values | Deprecated | Default | Description                                              | Examples |
| -------- | --------- | -------- | --------------- | ---------- | ------- | -------------------------------------------------------- | -------- |
| enabled  | `boolean` | ✅       | boolean         |            |         | **Mandatory**, true/false to enable/disable this module. |          |

## DeepGenParams

No description provided for this model.

#### Type: `object`

| Property | Type      | Required | Possible values | Deprecated | Default                                   | Description                                                                                         | Examples |
| -------- | --------- | -------- | --------------- | ---------- | ----------------------------------------- | --------------------------------------------------------------------------------------------------- | -------- |
| enabled  | `boolean` | ✅       | boolean         |            |                                           | **Mandatory**, true/false to enable/disable this module.                                            |          |
| models   | `string`  |          | string          |            | `"claude-3-7-sonnet-20250219:1,gpt-4o:1"` | Comma-separated list of generation models with weights. Format: 'model1:weight1,model2:weight2,...' |          |

## DictgenParams

No description provided for this model.

#### Type: `object`

| Property   | Type      | Required | Possible values | Deprecated | Default                            | Description                                                                                                                                                                                                                                                       | Examples |
| ---------- | --------- | -------- | --------------- | ---------- | ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| enabled    | `boolean` | ✅       | boolean         |            |                                    | **Mandatory**, true/false to enable or disable this module.                                                                                                                                                                                                       |          |
| gen_models | `string`  |          | string          |            | `"gpt-4o:10,claude-3-5-sonnet:10"` | **Optional**, comma-separated list of generation models with weights. Format: 'model1:weight1,model2:weight2,...'. Supported models: gpt-4o, o1, gemini-1.5, claude-3-5-sonnet, claude-3-5-opus, claude-3-5-haiku. Example: 'gpt-4o:10,claude-3-5-sonnet:10,o1:5' |          |

## DiffSchedulerParams

No description provided for this model.

#### Type: `object`

| Property       | Type      | Required | Possible values | Deprecated | Default | Description                                                                                             | Examples |
| -------------- | --------- | -------- | --------------- | ---------- | ------- | ------------------------------------------------------------------------------------------------------- | -------- |
| enabled        | `boolean` | ✅       | boolean         |            |         | **Mandatory**, true/false to enable/disable this module.                                                |          |
| max_sched_time | `integer` |          | integer         |            | `10800` | **Optional**, maximum time in seconds to wait before forcing scheduling. Default is 10800 seconds (3h). |          |
| min_sched_time | `integer` |          | integer         |            | `3600`  | **Optional**, minimum time in seconds to wait before scheduling. Default is 3600 seconds (1h).          |          |

## ExpKitParams

No description provided for this model.

#### Type: `object`

| Property   | Type      | Required | Possible values | Deprecated | Default | Description                                                                                                                                                          | Examples |
| ---------- | --------- | -------- | --------------- | ---------- | ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| enabled    | `boolean` | ✅       | boolean         |            |         | **Mandatory**, true/false to enable/disable this module.                                                                                                             |          |
| gen_models | `string`  | ✅       | string          |            |         | **Mandatory**, comma-separated list of generation models. Format: 'model1:weight1,model2:weight2,...'. Example: 'o1-preview:10,claude-3-7-sonnet-20250219:20,none:5' |          |
| x_models   | `string`  | ✅       | string          |            |         | **Mandatory**, comma-separated list of extraction models. Format: 'model1:weight1,model2:weight2,...'. Example: 'gpt-4o:10,o3-mini:20,none:5'                        |          |
| exp_time   | `integer` |          | integer         |            | `300`   | **Optional**, timeout in seconds for each beepseed exploitation. Default is 300 seconds.                                                                             |          |

## LLMFuzzAugmentorParams

No description provided for this model.

#### Type: `object`

| Property        | Type      | Required | Possible values | Deprecated | Default | Description                                              | Examples |
| --------------- | --------- | -------- | --------------- | ---------- | ------- | -------------------------------------------------------- | -------- |
| enabled         | `boolean` | ✅       | boolean         |            |         | **Mandatory**, true/false to enable/disable this module. |          |
| stuck_detection | `integer` | ✅       | integer         |            |         | **Mandatory**, time in seconds to detect stuck harness.  |          |
| verbose         | `boolean` |          | boolean         |            | `false` | **Optional**, true/false to enable/disable verbose mode. |          |

## LLMPOCGeneratorParams

No description provided for this model.

#### Type: `object`

| Property     | Type      | Required | Possible values | Deprecated | Default | Description                                                                                              | Examples |
| ------------ | --------- | -------- | --------------- | ---------- | ------- | -------------------------------------------------------------------------------------------------------- | -------- |
| enabled      | `boolean` | ✅       | boolean         |            |         | **Mandatory**, true/false to enable/disable this module.                                                 |          |
| mode         | `string`  | ✅       | `crs` `static`  |            |         | **Mandatory**, mode of `llmpocgen` module, one of 'crs' or 'static', static mode is for testing purpose. |          |
| diff_max_len | `integer` |          | integer         |            | `65536` | Maximum length for diff content processing, must be between 16K and 512K.                                |          |
| worker_num   | `integer` |          | integer         |            | `2`     | Number of worker processes to use for parallel processing.                                               |          |

## ModuleParams

No description provided for this model.

#### Type: `object`

| Property          | Type     | Required | Possible values                                     | Deprecated | Default | Description                          | Examples |
| ----------------- | -------- | -------- | --------------------------------------------------- | ---------- | ------- | ------------------------------------ | -------- |
| aixccjazzer       | `object` | ✅       | [AIxCCJazzerParams](#aixccjazzerparams)             |            |         | AIxCCJazzer module parameters.       |          |
| atldirectedjazzer | `object` | ✅       | [AtlDirectedJazzerParams](#atldirectedjazzerparams) |            |         | AtlDirectedJazzer module parameters. |          |
| atljazzer         | `object` | ✅       | [AtlJazzerParams](#atljazzerparams)                 |            |         | AtlJazzer module parameters.         |          |
| atllibafljazzer   | `object` | ✅       | [AtlLibAFLJazzerParams](#atllibafljazzerparams)     |            |         | AtlLibAFLJazzer module parameters.   |          |
| codeql            | `object` | ✅       | [CodeQLParams](#codeqlparams)                       |            |         | CodeQL module parameters.            |          |
| concolic          | `object` | ✅       | [ConcolicExecutorParams](#concolicexecutorparams)   |            |         | ConcolicExecutor module parameters.  |          |
| cpuallocator      | `object` | ✅       | [CPUAllocatorParams](#cpuallocatorparams)           |            |         | CPUAllocator module parameters.      |          |
| crashmanager      | `object` | ✅       | [CrashManagerParams](#crashmanagerparams)           |            |         | CrashManager module parameters.      |          |
| deepgen           | `object` | ✅       | [DeepGenParams](#deepgenparams)                     |            |         | DeepGen module parameters.           |          |
| dictgen           | `object` | ✅       | [DictgenParams](#dictgenparams)                     |            |         | Dictgen module parameters.           |          |
| diff_scheduler    | `object` | ✅       | [DiffSchedulerParams](#diffschedulerparams)         |            |         | DiffScheduler module parameters.     |          |
| expkit            | `object` | ✅       | [ExpKitParams](#expkitparams)                       |            |         | ExpKit module parameters.            |          |
| llmfuzzaug        | `object` | ✅       | [LLMFuzzAugmentorParams](#llmfuzzaugmentorparams)   |            |         | LLMFuzzAugmentor module parameters.  |          |
| llmpocgen         | `object` | ✅       | [LLMPOCGeneratorParams](#llmpocgeneratorparams)     |            |         | LLMPOCGenerator module parameters.   |          |
| sariflistener     | `object` | ✅       | [SARIFListenerParams](#sariflistenerparams)         |            |         | SARIFListener module parameters.     |          |
| seedmerger        | `object` | ✅       | [SeedMergerParams](#seedmergerparams)               |            |         | SeedMerger module parameters.        |          |
| seedsharer        | `object` | ✅       | [SeedSharerParams](#seedsharerparams)               |            |         | SeedSharer module parameters.        |          |
| sinkmanager       | `object` | ✅       | [SinkManagerParams](#sinkmanagerparams)             |            |         | SinkManager module parameters.       |          |
| staticanalysis    | `object` | ✅       | [StaticAnalysisParams](#staticanalysisparams)       |            |         | StaticAnalysis module parameters.    |          |

## SARIFListenerParams

No description provided for this model.

#### Type: `object`

| Property | Type      | Required | Possible values | Deprecated | Default | Description                                              | Examples |
| -------- | --------- | -------- | --------------- | ---------- | ------- | -------------------------------------------------------- | -------- |
| enabled  | `boolean` | ✅       | boolean         |            |         | **Mandatory**, true/false to enable/disable this module. |          |

## SeedMergerParams

No description provided for this model.

#### Type: `object`

| Property         | Type                | Required | Possible values | Deprecated | Default   | Description                                                              | Examples |
| ---------------- | ------------------- | -------- | --------------- | ---------- | --------- | ------------------------------------------------------------------------ | -------- |
| enabled          | `boolean`           | ✅       | boolean         |            |           | **Mandatory**, true/false to enable/disable this module.                 |          |
| keep_seed        | `boolean`           | ✅       | boolean         |            |           | **Mandatory**, true/false to keep the seed file.                         |          |
| beepseed_search  | `boolean`           |          | boolean         |            | `true`    |                                                                          |          |
| deepgen_consumer | `boolean`           |          | boolean         |            | `false`   |                                                                          |          |
| len_control      | `integer`           |          | integer         |            | `0`       | **Optional**, libfuzzer -len_control param. Default: 0.                  |          |
| max_len          | `integer` or `null` |          | integer         |            | `1048576` | **Optional**, libfuzzer -max_len param. If unset, will be 1048576 (1M).  |          |
| mem_size         | `integer`           |          | integer         |            | `4096`    | **Optional**, memory size in MB. Default value is 4096, require >= 2048. |          |
| set_cover_merge  | `boolean`           |          | boolean         |            | `false`   | **Optional**, true/false to enable/disable set_cover_merge.              |          |

## SeedSharerParams

No description provided for this model.

#### Type: `object`

| Property      | Type      | Required | Possible values | Deprecated | Default | Description                                                              | Examples |
| ------------- | --------- | -------- | --------------- | ---------- | ------- | ------------------------------------------------------------------------ | -------- |
| enabled       | `boolean` | ✅       | boolean         |            |         | **Mandatory**, true/false to enable/disable this module.                 |          |
| sync_period   | `integer` | ✅       | integer         |            |         | **Mandatory**, seed sync period in seconds among all Jazzer modules.     |          |
| N_latest_seed | `integer` |          | integer         |            | `5`     | **Optional**, latest N seed sync among all Jazzer modules. Default is 5. |          |

## SinkManagerParams

No description provided for this model.

#### Type: `object`

| Property | Type      | Required | Possible values | Deprecated | Default | Description                                              | Examples |
| -------- | --------- | -------- | --------------- | ---------- | ------- | -------------------------------------------------------- | -------- |
| enabled  | `boolean` | ✅       | boolean         |            |         | **Mandatory**, true/false to enable/disable this module. |          |

## StaticAnalysisParams

No description provided for this model.

#### Type: `object`

| Property                   | Type      | Required | Possible values | Deprecated | Default                          | Description                                                                                                                                                                                        | Examples |
| -------------------------- | --------- | -------- | --------------- | ---------- | -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| enabled                    | `boolean` | ✅       | boolean         |            |                                  | **Mandatory**, true/false to enable/disable this module.                                                                                                                                           |          |
| mock                       | `boolean` |          | boolean         |            | `false`                          | **Optional**, whether to use mock static analysis. Default is False.                                                                                                                               |          |
| mock_static_ana_result_dir | `string`  |          | string          |            | `"/eva/static-analysis/results"` | **Optional**, path to a mock static analysis result dir. Set when using the 'mock' analysis.                                                                                                       |          |
| static_ana_phases          | `array`   |          | string          |            | `["cha-0"]`                      | **Optional**, list of analysis phases to run in order. Valid values: 'cha-[0-2]' (CHA cg algo with cg level 0, 1, or 2), 'rta-[0-2]' (RTA cg algo with cg level 0, 1, or 2). Default is ['cha-0']. |          |

______________________________________________________________________

Markdown generated with [jsonschema-markdown](https://github.com/elisiariocouto/jsonschema-markdown).
