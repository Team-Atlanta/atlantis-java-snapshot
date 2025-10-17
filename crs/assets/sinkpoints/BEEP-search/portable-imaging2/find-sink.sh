die () {
    echo >&2 "$@"
    exit 1
}

if ! command -v jq &> /dev/null; then
    echo "jq not found, installing"
    sudo apt update
    sudo apt install -y jq || die "Failed to install jq"
fi
sudo apt install -y parallel || die "Failed to install parallel"
if ! command -v ts &> /dev/null; then
    sudo apt update
    sudo apt install -y moreutils || die "Failed to install ts"
fi
if ! command -v java &> /dev/null; then
  sudo apt update
  sudo apt install -y curl || die "Failed to install curl"
  export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
  export JVM_LD_LIBRARY_PATH=$JAVA_HOME/lib/server
  export PATH=$PATH:$JAVA_HOME/bin
  echo "Installing Modified JAVA" && \
    if ! test -f /openlogic-openjdk-17.0.11+9-linux-x64.tar.gz; then echo "from the internet...";curl -L -O https://builds.openlogic.com/downloadJDK/openlogic-openjdk/17.0.11+9/openlogic-openjdk-17.0.11+9-linux-x64.tar.gz;else echo "from cache";cp /openlogic-openjdk-17.0.11+9-linux-x64.tar.gz .;fi && \
      mkdir -p $JAVA_HOME && \
      tar -xz --strip-components=1 -f openlogic-openjdk-17.0.11+9-linux-x64.tar.gz --directory $JAVA_HOME && \
      update-alternatives --install /usr/bin/java java ${JAVA_HOME}/bin/java 1 && \
      update-alternatives --set java ${JAVA_HOME}/bin/java && \
      rm -f openlogic-openjdk-17.0.11+9-linux-x64.tar.gz && \
      rm -rf $JAVA_HOME/lib/src.zip || die "Failed to install JAVA"
fi

WORKDIR=`realpath ./fuzz`
rm -rf $WORKDIR
mkdir -p $WORKDIR

rm -rf log-find-sink json-result-sink
mkdir -p log-find-sink json-result-sink
rm -rf artifact-sink
mkdir -p artifact-sink
mkdir -p ${WORKDIR}/artifacts/
mkdir -p ${WORKDIR}/reproducer/
mkdir -p ${WORKDIR}/corpus_dir/

if [ $# -ge 1 ]; then
  # each arg is a corpus directory
  for corpus_dir in "$@"; do
    echo "Copying $corpus_dir to corpus_dir"
    [ -d "$corpus_dir" ] || die "Corpus directory not found"
    cp -r $corpus_dir ${WORKDIR}/corpus_dir/
    if [[ "$corpus_dir" == *"fuzz/oldjazzer-"* || "$corpus_dir" == *"fuzz/olddirectedjazzer-"* || "$corpus_dir" == *"fuzz/aixccjazzer-"* ]]; then
      echo Transforming corpus for $corpus_dir
      #find ${WORKDIR}/corpus_dir/ -type f -exec sh -c "tail -c +6 {} > {}.tmp && mv {}.tmp {}" \;
      find ${WORKDIR}/corpus_dir/ -type f | parallel --progress 'tail -c +6 {} > {}.tmp && mv {}.tmp {}'
    fi
  done
fi

# beep cpv1
hex_data="ffd8fffd0011d8d8d8fffd0008ff080000d8d8d8fffd0008db0011111111d8d8d8fffd0008ff0011111111d8d8d8fffd0008ff080000d8d80000d8d8d8fffd00080011111111d8fffd0008ff080000d80011111111fffd00080011111111d8d8d8fffd0008ff0011111111d8d8d8fffd0008ff080000d8d8fffd000800d8fffd00fffd000800d8fffd0008000011111111d8d8d8fffd0008ff080000d8d8d8fffd0008db0011111111d8d8d8fffd0008ff0011111111d8d8d8fffd0008ff080000d8d80000070011111111d8d8d8fffd0008ff001111d8fffd0008000011111111d8d8d8fffd0008ff080000d8d8d8fffd0008db0011111111d8d8d8fffd0008ff00110e1111d8d8d8fffd0008ff080000d8d80000d8d8d8fffd000800111111d8d8d8fffd0008ff0011111111d8d800d8d8d8fffd000800111111d8d8d8fffd0008ff0011111111d8d8d8fffd0008ff080000d8d8fffd000800d8fffd00fffd000800d8fffd0008000011111111d8d8d8ff0d0008ff080000dad8d8fffd0008db0011111111d8d8d8fffd0008ff0011111111d8d8d8fffd00080011111111d8d8d8fffd0008ff080000d8d8d8fffd0008db0011111111d8d8d8fffd0008ff0011111111d8d8d8fffd0008ff080000d8d80000d8d8d8fffd00080011111111d8fffd0008ff080000d80011111111fffd00080011111111d8d8d8fffd0008ff0011111111d8d8d8fffd0008ffffd8ffcb0008080000d8d8fffd0008ffd8fffd0011d8d8d8fffd0008ff080000d8d8d8fffd0008db0011111111d8d8d8fffd0008ff0011111111d8d8d8fffd0008ff080000d8d80000d8d8d8fffd00080011111111d8fffd0008ff080000d80011111111fffd00080011111111d8d8d8fffd0008ff0011111111d8d8d8fffd0008ff080000d8d8fffd000800d8fffd00fffd000800d8fffd0008000011111111d8d8d8fffd0008ff080000d8d8d8fffd0008db0011111111d8d8d8fffd0008ff0011111111d8d8d8fffd0008ff080000d8d80000070011111111d8d8d8fffd0008ff001111d8fffd0008000011111111d8d8d8fffd0008ff080000d8d8d8fffd0008db0011111111d8d8d8fffd0008ff0011111111d8d8d8fffd0008ff080000d8d80000d8d8d8fffd000800111111d8d8d8fffd0008ff0011111111d8d800d8d8d8fffd000800111111d8d8d8fffd0008ff0011111111d8d8d8fffd0008ff080000d8d8fffd000800d8fffd00fffd000800d8fffd0008000011111111d8d8d8ff0d0008ff080000dad8d8fffd0008db0011111111d8d8d8fffd0008ff0011111111d8d8d8fffd00080011111111d8d8d8fffd0008ff080000d8d8d8fffd0008db0011111111d8d8d8fffd0008ff0011111111d8d8d8fffd0008ff080000d8d80000d8d8d8fffd00080011111111d8fffd0008ff080000d80011111111fffd00080011111111d8d8d8fffd0008ff0011111111d8d8d8fffd0008ffffd8ffcb0008080000d8d8fffd000800d8fffd00fffd000800d8fffd0008000011111111d8d8d8fffd0008ff080000d8d8d8fffd0008db0011111111d8d8d8fffd0008ff0011111111d8d8d8fffd0008ff080000fffd000800111111d8d8d8fffd0008ff0011111111d8d800d8d8d80000d8d8d8fffd000800111111d8d8d8fffd0008ff0011111111d8d8d8fffd0008ff080000d8d8fffd000800d8fffd00fffd000800d8fffd0008000011111111d8d8d8fffd0008ff080000d8d8d8fffd0008db0011111111d8d8d8fffd0008ffffffff080000d8d80000d8d8d8fffd00080011111111d8d8d8fffd0008ff080000d80011111111fffd00080011111111d8d8d8fffd0008ff0011111111d8d8d8fffd0008ff080000d8d8fffd000800d8fffd00fffd000800d8fffd0008000011111111d8d8d8fffd0008ff080000d8d8d8fffd0008db0011111111d8d8d8fffd0008ff080000d8d8fffd000800d8fffd00fffd000800d8fffd0008000011111111d8d8d8fffd0008ff080000d8d8d8fffd0008db001111111100d8d80000d8d8d8fffd00080011111111d8d8d8fffd0008ff0011111111d8d8d8fffd0008ff0011111111d8d8d8fffd0008ff080000d8d80000d8d8d8fffd00fd4141003c3f786d6c2076657273696f6e3d22312e302220656e636f64696e673d225554462d38223f3e203c6e6f64653e203c2f6e6f64653e2020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020202020200800d8fffd0008000011111111d8d8d8fffd0008ffdbff080000d8d8d8fffd0008db0011111111d8d8d8fffd0008ffff5dfffffffffffffffd0008ff080000d8d80000d8d8d8fffd00080011111111d8d8d8fffd0008ff080000d80011111111fffd00080011111111d8d8d8fffd0008ff0011111111d8d8d8fffd0008ff080000d8d8fffd000800d8fffd00fffd000800d8fffd0008000011111111d8d8d8fffd0008ff080000d8d8d8fffd0008db0011111111d8d8d8fffd0008ff0011111111d8d8d8fffd0008ff080000d8d80000d8d8d8fffd000800111111d8d8d8fffd0008ff0011111111d8d8d8fffd0008ff080000d8d8fffd000800d8fffd00fffd000800d8fffd0008000011111111d8d8d8fffd0008ff080000d8d8d8fffd0008db0011111111d8d8d8fffd0008ff0011111111d8d8d8fffd0008ff080000d8d80000d80000111100fdd8d8fffd000800111111cb110000"
echo $hex_data | xxd -r -p > ${WORKDIR}/corpus_dir/initial_seed

#  --instrumentation_includes="org.apache.activemq.openwire.v10.**" \
#  --instrumentation_includes="org.apache.activemq.openwire.v10.**" \
#  --instrumentation_excludes="com.jprofiler.**" \
#  --instrumentation_excludes="**" \

#-dict=${WORKDIR}/fuzz.dict 

JAZZER_PATH=./classpath/jazzer
#JAZZER_PATH=./classpath/atl-jazzer
#JAZZER_PATH=./classpath/atl-jazzer-directed
#JAZZER_PATH=./classpath/atl-jazzer-new
#JAZZER_PATH=./classpath/atl-jazzer-directed-new

TARGET_CLASS=com.aixcc.imaging.harnesses.two.ImagingTwo

#  -max_total_time=300 \

# N.B. powermock and mockito-all are excluded from the classpath to make Jazzer happy
#   This conflict is found by fuzzing cp-java-geonetwork
TARGET_CLASSPATH=${JAZZER_PATH}:$(find "./cp" -name "*.jar" | grep -v -e 'powermock' -e 'mockito-all' | tr '\n' ':'; find "${JAZZER_PATH}" -name "*.jar" | tr '\n' ':')

for CPV in ImagingTwoCPVOne
do

  export JAZZER_SINK_MODE=${CPV}

  sink_json=json-result-sink/${CPV}.json

  ${JAZZER_PATH}/jazzer \
    --trace=none \
    --custom_hook_includes="some.package.names.never.exist" \
    --instrumentation_includes="some.package.names.never.exist" \
  	--reproducer_path=${WORKDIR}/reproducer \
  	--agent_path=${JAZZER_PATH}/jazzer_standalone_deploy.jar \
  	--cp=${TARGET_CLASSPATH} \
  	--target_class=${TARGET_CLASS} \
  	--jvm_args=-Djdk.attach.allowAttachSelf=true:-XX\:+StartAttachListener:-Xmx20000m:-XX\:MaxPermSize --keep_going=1000 --disabled_hooks=com.code_intelligence.jazzer.sanitizers.IntegerOverflow \
  	-use_value_profile=1 -rss_limit_mb=20000 -artifact_prefix=${WORKDIR}/artifacts/ -reload=1 -dict=./fuzz.dict -close_fd_mask=1 -timeout=300 -keep_seed=1 ${WORKDIR}/corpus_dir \
    -runs=0 \
    2>&1 | \
    stdbuf -e 0 -o 0 ts "%s" | \
    python3 -u ./jazzer_postprocessing.py -o $sink_json 2>&1 | tee log-find-sink/${CPV}.log
  
  echo Jazzer ret code is ${PIPESTATUS[0]}

  n=0
  jq -r '.fuzz_data.log_triage_crash_over_time[] | select(.[1]=="SINKPOINT" and (.[2] | type == "string" and contains("'${CPV}'"))) | .[3]' $sink_json | while read f;
  do
    cp ${WORKDIR}/artifacts/$f artifact-sink/sink-${CPV}-${n}
    n=$((n+1))
  done
done
