#!/usr/bin/env bash

crs_java_repro_cov() {
  echo "Coverage reproduction mode enabled with directory: $CRS_JAVA_COV_REPRO"
  
  # Find all directories matching HarnessRunner/**/fuzz pattern
  fuzz_dirs=()
  cp_names=()
  while IFS= read -r fuzz_dir; do
    # Check if path matches the pattern .*/HarnessRunner/.+/[^/]+/fuzz
    if [[ "$fuzz_dir" =~ .*/HarnessRunner/(.+)/[^/]+/fuzz$ ]]; then
      fuzz_dirs+=("$fuzz_dir")
      cp_name="${BASH_REMATCH[1]}"
      cp_names+=("$cp_name")
    fi
  done < <(find "$CRS_JAVA_COV_REPRO" -type d -name "fuzz" 2>/dev/null)
  
  # Get unique cp names
  unique_cp_names=($(printf '%s\n' "${cp_names[@]}" | sort -u))
  
  if [[ ${#unique_cp_names[@]} -eq 0 ]]; then
    echo "No fuzzing directories found matching pattern .*/HarnessRunner/.*/fuzz in $CRS_JAVA_COV_REPRO"
    exit 1
  fi
  
  echo "Found CP targets: ${unique_cp_names[@]}"
  echo "Found ${#fuzz_dirs[@]} fuzz directories"
  
  # Iterate through each unique CP name
  for cp_name in "${unique_cp_names[@]}"; do
    echo "Processing CP: $cp_name"
    export CRS_TARGET="$cp_name"
    setup_cp_dirs
  done
  
  # Call cov_repro.py with the CRS_JAVA_COV_REPRO directory, parallelism, and all matching fuzz directories
  pushd "${JAVA_CRS_SRC}" > /dev/null
  REPRO_PARA="${CRS_JAVA_COV_REPRO_PARA:-1}"
  python3.12 -u ./cov_repro.py "$CRS_JAVA_COV_REPRO" "$REPRO_PARA" "${fuzz_dirs[@]}" 2>&1 | tee ./cov-repro.log
  popd > /dev/null
  
  exit 0
}

pick_target_cp() {
  dirs=()
  while IFS= read -r -d $'\0'; do
    dirs+=("$REPLY")
  done < <(find /cp_root/projects/aixcc/jvm -mindepth 1 -maxdepth 1 -type d -print0 | \
           sed 's|/cp_root/projects/aixcc/jvm/||g')

  if [[ ${#dirs[@]} -eq 0 ]]; then
    echo "No directories found under /cp_root/projects/aixcc/jvm."
    exit 1
  fi

  echo "CRS_TARGET is not set, select one from the following (only aixcc/jvm/xxx are presented):"
  select dir in "${dirs[@]}"; do
    if [[ -n "$dir" ]]; then
      export CRS_TARGET=aixcc/jvm/`basename "$dir"`
      echo "You have selected: $CRS_TARGET"
      break
    else
      echo "Invalid selection. Please try again."
    fi
  done
}

determine_CRS_TARGET() {
  if [[ -z "$CRS_TARGET" ]]; then
    if [[ -t 0 ]]; then
      # Interactive shell:
      #   - Search CPs at /cp_root and let user pick target CP
      pick_target_cp
    else
      echo "CRS_TARGET is not set. Exiting."
      exit 1
    fi
  fi
}

setup_src_proj() {
    src_proj=/src-`basename $CRS_TARGET`/oss-fuzz/projects/$CRS_TARGET
    rm -rf $src_proj
    mkdir -p $src_proj
    rsync -a --exclude=".aixcc" /cp_root/projects/$CRS_TARGET/ $src_proj
    mkdir -p $src_proj/.aixcc/
    if [[ -z "$DIFF_MODE" ]]; then
      if [[ -f "/cp_root/projects/$CRS_TARGET/.aixcc/ref.diff" ]]; then
        echo "Diff mode enabled"
        rsync -a "/cp_root/projects/$CRS_TARGET/.aixcc/ref.diff" $src_proj/ref.diff
      else
        echo "No ref.diff found, fall back to full mode in benchmark CP"
      fi
    else
      echo "Use full mode in benchmark CP"
    fi
}

setup_src_repo() {
    src_repo=/src-`basename $CRS_TARGET`/repo
    rm -rf $src_repo
    mkdir -p $src_repo
    rsync -a /cp_root/build/repos/$CRS_TARGET/ $src_repo
}

setup_out() {
    out_dir=/out-`basename $CRS_TARGET`
    rm -rf $out_dir
    mkdir -p $out_dir
    rsync -a /cp_root/build/out/$CRS_TARGET/ $out_dir
    find $out_dir -type f | while read f;
    do
      basename=$(basename "$f")
      if [[ "$basename" =~ ^jazzer.*$ ]]; then
        if [[ "$basename" != "jazzer_driver_with_sanitizer" ]]; then
          rm -f "$f"
        fi
      fi
    done
    rsync -a $JAVA_CRS_SRC/jazzer_driver_stub $out_dir/jazzer_driver
}

setup_cp_dirs() {
    setup_src_proj
    setup_src_repo
    setup_out
}

setup_rest_env() {
  export FUZZING_ENGINE=libfuzzer
  # TODO: this should always be the case? (how about coverage, etc)
  export SANITIZER=${SANITIZER:-address}
  export HELPER=True
  export RUN_FUZZER_MODE=interactive
  export SRC="/src-`basename $CRS_TARGET`"
  export OUT="/out-`basename $CRS_TARGET`"
  export SEED_SHARE_DIR="/seed-shared-`basename $CRS_TARGET`"
  export SARIF_SHARE_DIR="/sarif-shared-`basename $CRS_TARGET`"
  export SARIF_ANA_RESULT_DIR="/sarif-ana-result-`basename $CRS_TARGET`"
  export SARIF_REACHABILIY_SHARE_DIR="/sarif-reachability-shared-`basename $CRS_TARGET`"
  export CRS_JAVA_SHARE_DIR="/crs-java-shared-`basename $CRS_TARGET`"
  export CRS_JAVA_TEST_ENV_ROLE="leader"
  export TARBALL_FS_DIR="/tarball-fs"
  unset JAVA_CRS_IN_COMPETITION
}

update_crs_test_cfg() {
  if ! python3.12 -u ./tests/gen_test_cfg.py; then
    echo ERROR: Failed to gen crs test config
    exit 1
  fi
  if ! python3.12 -u javacrscfg.py merge-crs-cfg ./crs-java.config /tmp/test.config; then
    echo ERROR: Failed to update crs test config
    exit 1
  fi
}

run_crs() {
  pushd "${JAVA_CRS_SRC}" > /dev/null

  DEFAULT_CFG="${JAVA_CRS_SRC}/crs-java.config"
  : "${JAVACRS_CFG:=${1:-${DEFAULT_CFG}}}"
  setup_rest_env

  if [[ -z "$CRS_JAVA_TEST" ]]; then
    echo ">> CRS NORMAL RUN <<"
    python3.12 -u ./main.py "${JAVACRS_CFG}" 2>&1 | tee ./crs-java.log
  else
    echo ">> CRS TEST RUN <<"
    update_crs_test_cfg
    if ! python3.12 -u ./main.py "${JAVACRS_CFG}" 2>&1 | tee ./crs-java.log; then
      echo ERROR: crs-java run failed with ret $?
      exit 1
    fi
    python3.12 -u ./tests/e2e_result_checker.py | tee ./e2e-check.log
    rc=$?
    cp ./crs-java.log /crs-workdir/worker-0/
    cp ./e2e-check.log /crs-workdir/worker-0/
    mv /crs-workdir/worker-0 /crs-workdir/`basename $CRS_TARGET`
    if [ $rc -eq 0 ]; then
      echo ERROR: e2e result check failed
      if [[ -z "${CRS_JAVA_TEST_DEBUG}" ]]; then
        echo "E2E test debugging mode not enabled, exiting."
        exit 1
      else
        echo "E2E test debugging mode enabled, will NOT exit."
        sleep infinity
      fi
    fi
  fi

  popd > /dev/null
}

setup_sys() {
  ulimit -c 0
  sysctl -w fs.file-max=2097152
  sysctl -w fs.inotify.max_user_instances=512
}

# Check if CRS_JAVA_COV_REPRO is set for coverage reproduction mode
if [[ -n "$CRS_JAVA_COV_REPRO" ]]; then
  crs_java_repro_cov
else
  determine_CRS_TARGET
  setup_cp_dirs
  setup_sys
  run_crs "$1"
fi
