# ICFG Demo

Demo tool for SootUp's JimpleBasedInterproceduralCFG that analyzes Java bytecode and prints the first 100 statements with position information.

## Build

```bash
mvn compile
```

## Test with Sample Class

```bash
mvn compile exec:java
```

## Test with Real-World Project

```bash
mvn exec:java -Dexec.args="--classpath /home/cen/CRS-java/cp_root/build/out/aixcc/jvm/imaging/jars/one/imaging-harness-one.jar:/home/cen/CRS-java/cp_root/build/out/aixcc/jvm/imaging/jars/one/commons-imaging-1.0.0-alpha6-aixcc.jar:/home/cen/CRS-java/cp_root/build/out/aixcc/jvm/imaging/jars/one/jazzer-0.0.0.jar --class com.aixcc.imaging.harnesses.one.ImagingOne --method fuzzerTestOneInput --return void --params byte[]"
```