# Static Analyzer

Soot-based static analysis using call graph and control flow graph to calculate distance maps for directed fuzzing.
The CG and iCFG may be used by other modules as well.

## Build

Build the project using Maven:

```
mvn clean package
```

This will create two jar files:

- A "regular" jar with only the project classes (`target/static-analyzer-1.0.jar`)
- A standalone jar with all dependencies included (`target/static-analyzer-1.0-jar-with-dependencies.jar`)

## Usage

```
usage: StaticAnalyzer
 -c,--config <arg>              Config file describing the project to
                                analyze
    --cache-dir <arg>           Directory to store cached analysis results
    --cg-stages <arg>           List of call graph configurations (e.g.,
                                cha-0,cha-1,rta-0; default: cha-0)
    --distance-map-file <arg>   Path to write the distance map file to
                                (contains the list of all target
                                configurations for the directed fuzzer)
 -i,--input-call-graphs <arg>   Paths to JSON files containing call graphs
                                to merge into the analysis
    --include-cfg               Include the results of the CFG analysis in
                                the output
    --include-distance-map      Include the verbose distance map in the
                                output for debugging purposes (default:
                                false)
 -o,--output-call-graph <arg>   Path to a JSON file where the call graph
                                will be stored
    --sarif-sinkpoints <arg>    Path to a .json file with SARIF sinkpoints
    --server                    After processing the stages, keep running
                                and process input-cg updates
 -t,--target-file <arg>         Path to file with target specifications
                                (api and coordinate format)
```

The config file should look like this:

```
{
  "classpath": [
        "/out/mock_java.jar",
        "/out/gson-2.8.6.jar",
        "/out/.",
        "/out"
  ],
  "cp_name": "aixcc/jvm/imaging",
  "harnesses": [
   "ImagingOne": {
     "name": "ImagingOne",
     "target_class": "com.aixcc.imaging.harnesses.one.ImagingOne",
     "target_method": "fuzzerTestOneInput",
     "target_method_desc": "([B)V"
   },
   "ImagingTwo": {
     "name": "ImagingTwo",
     "target_class": "com.aixcc.imaging.harnesses.two.ImagingTwo",
     "target_method": "fuzzerTestOneInput",
     "target_method_desc": "([B)V"
   }
  ],
  "pkg_list": [
    "com.aixcc.imaging.harnesses.one",
    "com.aixcc.imaging.harnesses.two",
    "org.apache.commons.imaging",
    "org.apache.commons.imaging.bytesource",
    "org.apache.commons.imaging.color",
    "org.apache.commons.imaging.common"
    "org.apache.commons.imaging.examples",
    "org.apache.commons.imaging.examples.tiff",
    "org.apache.commons.imaging.formats.bmp",
[...]
    "org.apache.commons.imaging.formats.xpm",
    "org.apache.commons.imaging.icc",
    "org.apache.commons.imaging.internal",
    "org.apache.commons.imaging.mylzw",
    "org.apache.commons.imaging.palette",
    "org.apache.commons.imaging.roundtrip",
    "org.apache.commons.imaging.test",
  ]
}
```

The static analyzer module in `javacrs_modules` will create such a config file.
