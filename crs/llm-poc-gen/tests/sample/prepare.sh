apt update -y
apt install -y clang gdb

curdir=$(realpath $(dirname $0))
javadir=$curdir/java
cd $javadir/src/sample && mvn install
cd $javadir/src/sample-harnesses && mvn package
mkdir -p $javadir/out/harnesses/one
cp -rf $javadir/src/sample-harnesses/sample-harness-one/target/sample-harness-one-1.0.0-SNAPSHOT.jar $javadir/out/harnesses/one
cp -rf $javadir/src/sample-harnesses/sample-harness-one/target/lib/*.jar $javadir/out/harnesses/one

cdir=$curdir/c
cd $cdir && cmake -B build && make -C build
