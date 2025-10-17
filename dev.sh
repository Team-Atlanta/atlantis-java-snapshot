#!/usr/bin/env bash

set -e
#set -x

#################################
## Script Variables
#################################

# script paths
SCRIPT_DIR="$(dirname "$(realpath "${BASH_SOURCE[0]}")")"
SCRIPT_FILE="$(basename "${BASH_SOURCE[0]}")"

# host paths
CP_ROOT="${SCRIPT_DIR}/cp_root"
CRS_SRC="${SCRIPT_DIR}/crs"
CRS_DOC_PATH="${SCRIPT_DIR}/docs"

# container paths
AIXCC_CRS_SRC=/app/crs-cp-java

DOCKER_COMPOSE_FILE=${SCRIPT_DIR}/compose.dev.yaml

# additional docker arguments from user or default
set_competition_profile() {
  DOCKER_USER_ARGS+=" --profile competition"
  COMPOSE_SERVICE_NAME="crs-java-runner"
}
set_development_profile() {
  DOCKER_USER_ARGS+=" --profile development"
  COMPOSE_SERVICE_NAME="dev-crs-java-runner"
}
set_evaluation_profile() {
  DOCKER_USER_ARGS+=" --profile evaluation"
  COMPOSE_SERVICE_NAME="eva-crs-java-runner"
}
: "${DOCKER_USER_ARGS:="-f ${DOCKER_COMPOSE_FILE}"}"
if [[ ! -z "$EVA" ]]; then
  set_evaluation_profile
  CRS_DOCKER_IMAGE=${EVA_JAVACRS_IMG}
elif [[ ! -z "$DEV" ]]; then
  set_development_profile
  CRS_DOCKER_IMAGE=$(yq -r ".services.\"${COMPOSE_SERVICE_NAME}\".image" "${SCRIPT_DIR}/compose.dev.yaml" 2>/dev/null || echo "")
else
  set_competition_profile
  CRS_DOCKER_IMAGE=$(yq -r ".services.\"${COMPOSE_SERVICE_NAME}\".image" "${SCRIPT_DIR}/compose.dev.yaml" 2>/dev/null || echo "")
fi

[[ -n "${CRS_DOCKER_IMAGE}" ]] || echo "WARNING: environment variable CRS_DOCKER_IMAGE is not set" >&2

#################################
## Utility Functions
#################################

# print warning/error
warn() {
  echo "$*" >&2
}

# kill the script with an error message
die() {
  warn "$*"
  exit 1
}

check_docker_image() {
  docker inspect "${CRS_DOCKER_IMAGE}" &>/dev/null ||
    die "Requested docker image not found: ${CRS_DOCKER_IMAGE}; see README.md to obtain or build a docker container."
}

# generic wrapper/handler for all calls to "docker run", script exits here
docker_run_generic() {
  local _status
  local _cid
  local wait_for_container=true

  # Parse options
  while [[ "$1" == --* ]]; do
    case "$1" in
      --no-wait)
        wait_for_container=false
        shift
        ;;
      *)
        break
        ;;
    esac
  done

  # call "docker run" with the set environment variables and passed args
  # shellcheck disable=SC2086
  container_id=$(docker compose \
    ${DOCKER_USER_ARGS} \
    run \
    ${CONTAINER_USER_ARGS} \
    -d ${COMPOSE_SERVICE_NAME} \
    "$@")

  # preserve exit code from "docker run"
  _status=$?

  echo "$_status"

  # obtain container ID
  _cid="$container_id"

  if [ "$wait_for_container" = true ]; then
    while [[ $(docker inspect -f '{{.State.Running}}' "${_cid}") == "true" ]]; do
      docker logs -f "${_cid}"
      sleep 1
    done

    # if the container is still running, then don't look for an exit code
    # and leave it alone
    if [[ $(docker inspect -f '{{.State.Running}}' "${_cid}") == "true" ]]; then
      echo "Container is still running: ${_cid}"
    else # container is not running
      # record the exit code if the output directory exists
      exitcode=$(docker inspect -f '{{.State.ExitCode}}' "${_cid}")
      echo "docker run exit code: ${exitcode}"
      # cleanup the anonymous volumes of the stopped container
      docker rm -v "${_cid}" >/dev/null 2>&1 || true
    fi
  else
    echo "Container started in detached mode: ${_cid}"
  fi
}

#################################
## dev.sh Command Handlers
#################################

print_usage() {
  warn "A helper script for CP interactions."
  warn
  warn "Usage: ${SCRIPT_FILE} <subcommand> [options]"
  warn
  warn "Subcommands:"
  warn "  install-yq                Install yq if not already installed"
  warn "  build-cp <regex>          Build the CPs matching the regex pattern"
  warn "  build-crs                 Build the CRS and related Docker images"
  warn "  upload-base <version>      Build and push the common-deps base image to ghcr.io"
  warn "  run                       Run CRS"
  warn "  gen-doc                   Generate CRS config parameters documentation"
  warn "  custom [commands...]      Run custom commands inside the Docker container"
  warn "                            Use '-d' to run in detached mode"
  warn "  test [opts]               Run e2e functionality tests, envs (* -> required):"
  warn "                             opts:    opt1*,      opt2*,       opt3,         opt4"
  warn "                             meaning: CRS_TARGET, CRS_HARNESS, CRS_TTL_TIME, USE_LLM"
  warn "  help                      Display this help message"
  die
}

upload_base() {
  shift

  # Check if version argument is provided
  if [ -z "$1" ]; then
    echo "ERROR: Version argument is required for upload-base command" >&2
    echo "Usage: ${SCRIPT_FILE} upload-base <version>" >&2
    exit 1
  fi

  VERSION=$1

  echo "Building common-deps base image with version ${VERSION}..."
  cd "${CRS_SRC}"
  docker build -t ghcr.io/occia/common-deps:${VERSION} -f Dockerfile.public_base .

  echo "Pushing common-deps base image to ghcr.io..."
  docker push ghcr.io/occia/common-deps:${VERSION}
}

build_crs() {
  shift

  docker compose -f compose.dev.yaml build ${COMPOSE_SERVICE_NAME}
}

build_cp() {
  shift

  TARGET_LIST=$1
  TARGET_CP=$2
  if [ $# -ne 2 ]; then
    echo "Usage: build-cp <target_list> <target_cp>"
    exit 1
  fi

  # Extract the list of CPs from cp-config.yaml using yq
  CP_LIST=$(yq e '.'$TARGET_LIST' | keys | join("\n")' "$SCRIPT_DIR/targets.yaml")

  # Use TARGET_CP as a regex to match CP names
  CP_TO_BUILD=()
  for cp in $CP_LIST; do
    if [[ "$cp" =~ $TARGET_CP ]]; then
      CP_TO_BUILD+=("$cp")
    fi
  done

  if [ ${#CP_TO_BUILD[@]} -eq 0 ]; then
    echo "Error: No CPs matched the regex '$TARGET_CP' in $TARGET_LIST"
    exit 1
  fi

  # if cp_root does not exist, git clone git@github.com:Team-Atlanta/oss-fuzz.git as cp_root
  if [ ! -d "$CP_ROOT" ]; then
    echo "Cloning our oss-fuzz repo for building CPs..."
    git clone git@github.com:Team-Atlanta/oss-fuzz.git "$CP_ROOT" || die "Failed to clone CPs"
  else
    echo "$CP_ROOT already exists, skipping cloning... (this can cause error if $CP_ROOT is not the correct repo, pls be aware of this)"
  fi

  # Output the regex and the matched CP list to user
  echo "Regex pattern: '$TARGET_CP'"
  echo "Matched CPs: ${CP_TO_BUILD[*]}"

  for cp in "${CP_TO_BUILD[@]}"; do
    cd "$CP_ROOT"

    echo "Cleaning ${cp}..."

    CP_IMG="aixcc-afc/${cp}:latest"

    if [[ -d build/DONE/${cp} ]]; then
      echo "Skipping ${cp} as it is already built."
      cd "$SCRIPT_DIR"
      continue
    fi

    docker rmi ${CP_IMG} >/dev/null 2>&1 || true
    #docker builder prune -f >/dev/null 2>&1
    # make sure parent dir exists while the src dir itself not
    sudo mkdir -p build/out/${cp} && rm -rf build/out/${cp}
    sudo mkdir -p build/repos/${cp} && rm -rf build/repos/${cp}
    sudo mkdir -p build/raw-repos/${cp} && rm -rf build/raw-repos/${cp}

    if [[ "$TARGET_LIST" == cps ]]; then
      url=`yq e ".main_repo" projects/${cp}/project.yaml`
      commit=`yq e ".full_mode.base_commit" projects/${cp}/.aixcc/config.yaml`
      git clone $url build/repos/${cp}
      cd build/repos/${cp} && git checkout ${commit} && cd -
      cp -r build/repos/${cp} build/raw-repos/${cp}

      echo "Building docker image for ${cp}"
      python3 infra/helper.py build_image --pull ${cp} >/dev/null 2>&1 || die "Failed to build docker image for ${cp}"

      echo "Building fuzzers for ${cp}"
      python3 infra/helper.py build_fuzzers --sanitizer address ${cp} build/repos/${cp} >/dev/null 2>&1 || die "Failed to build fuzzers for ${cp}"

      echo "Removing .aixcc except ref.diff for evaluation"
      find $CP_ROOT/projects/${cp}/.aixcc -mindepth 1 -not -name "ref.diff" -exec rm -rf {} \; || true
    else
      echo "Building docker image for ${cp}"
      python3 infra/helper.py build_image --pull ${cp} >/dev/null 2>&1 || die "Failed to build docker image for ${cp}"

      echo "Cloning ${cp} source from the built image ;)"
      src_path_in_container=`yq e ".oss.${cp}.src_path" ${SCRIPT_DIR}/targets.yaml`
      docker run -v $PWD/build/repos:/repos --rm ${CP_IMG} bash -c "cp -r ${src_path_in_container} /repos/${cp}" >/dev/null 2>&1 || die "Failed to clone source code for ${cp}"
      cp -r build/repos/${cp} build/raw-repos/${cp}

      echo "Building fuzzers for ${cp}"
      if `yq e ".oss.${cp}.default" ${SCRIPT_DIR}/targets.yaml` ; then
        # .oss.${cp}.default is true
        python3 infra/helper.py build_fuzzers --sanitizer address ${cp} build/repos/${cp} >/dev/null 2>&1 || die "Failed to build fuzzers for ${cp}"
      else
        # .oss.${cp}.default is false
        python3 infra/helper.py build_fuzzers --sanitizer address --mount_path $PWD/build/repos/${cp}:${src_path_in_container} ${cp} >/dev/null 2>&1 || die "Failed to build fuzzers for ${cp}"
      fi
    fi

    mkdir -p build/DONE/${cp}

    cd "$SCRIPT_DIR"
  done
}

run() {
  shift

  # Handle REPRO environment variable
  if [[ -n "$REPRO" ]]; then
    if [[ ! -d "$REPRO" ]]; then
      die "REPRO is set but '$REPRO' is not a valid directory"
    fi
    # Mount the REPRO directory and set CRS_JAVA_COV_REPRO to the mounted path
    REPRO_MOUNT="/repro/$(realpath "$REPRO")"
    export CRS_JAVA_COV_REPRO="$REPRO_MOUNT"
    CONTAINER_USER_ARGS+=" -v $(realpath "$REPRO"):$REPRO_MOUNT"
    
    # Pass through REPRO_PARA for parallel processing (default to 1)
    export CRS_JAVA_COV_REPRO_PARA="${REPRO_PARA:-1}"
  fi

  docker compose -f compose.dev.yaml build ${COMPOSE_SERVICE_NAME}

  check_docker_image

  docker_run_generic

  docker compose ${DOCKER_USER_ARGS} down
}

test() {
  shift

  # Check for required arguments
  if [ $# -lt 2 ]; then
    warn "Missing required arguments for test"
    warn "Usage: ${SCRIPT_FILE} test <CRS_TARGET> <CRS_HARNESS> [CRS_TTL_TIME] [USE_LLM]"
    die
  fi

  # Parse arguments
  export CRS_TARGET="$1"
  export CRS_HARNESS="$2"

  # Optional arguments
  if [ $# -ge 3 ]; then
    export CRS_TTL_TIME="$3"
  fi

  if [ $# -ge 4 ] && [ "$4" = "true" ]; then
    export USE_LLM=1
  fi

  docker compose -f compose.dev.yaml build ${COMPOSE_SERVICE_NAME}

  check_docker_image

  if [[ -n "$USE_LLM" ]]; then
    echo "USE_LLM is set, running tests with LLM"
  else
    echo "USE_LLM is not set, not running tests with LLM"
    export LITELLM_KEY=fake-key
  fi
  export CRS_JAVA_TEST=1

  docker_run_generic

  docker compose ${DOCKER_USER_ARGS} down
}

custom() {
  shift

  # Parse options
  local detach_mode=false
  while [ "$#" -gt 0 ]; do
    case "$1" in
      -d)
        detach_mode=true
        shift
        ;;
      *)
        break
        ;;
    esac
  done

  check_docker_image

  if [ "$detach_mode" = true ]; then
    docker_run_generic --no-wait "$@"
  else
    docker_run_generic "$@"
    docker compose -f compose.dev.yaml down --remove-orphans
  fi
}

install_yq() {
  shift

  if ! command -v yq &>/dev/null; then
    echo "Installing yq..."
    wget https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 -O /usr/bin/yq && chmod +x /usr/bin/yq || die "Failed to install yq"
  else
    echo "yq is already installed"
  fi
}

gen_doc() {
  shift

  if ! command -v jsonschema-markdown &> /dev/null; then
    die "jsonschema-markdown could not be found, try 'pip3 install jsonschema-markdown'"
  fi

  echo "Generating documentation..."

  check_docker_image

  SCHEMA_FILE=javacrscfg.schema.json
  MARKDOWN_FILE=${CRS_DOC_PATH}/javacrscfg.schema.md
  TEMP_DIR=$(mktemp -d)

  # A trick to immediately update gen doc content after crs code changes (no image rebuild required)
  set_development_profile

  CONTAINER_USER_ARGS="-v ${TEMP_DIR}:/out"
  docker_run_generic \
    python3.12 javacrscfg.py gen-schema /out/${SCHEMA_FILE}

  docker compose -f compose.dev.yaml down --remove-orphans

  if [ ! -f "${TEMP_DIR}/${SCHEMA_FILE}" ]; then
    rm -rf "${TEMP_DIR}"
    die "Error: Schema file is not successfully generated at ${TEMP_DIR}/${SCHEMA_FILE}"
  fi

  mv ${TEMP_DIR}/${SCHEMA_FILE} ${CRS_DOC_PATH}/${SCHEMA_FILE}
  echo "Schema file is generated and placed at ${CRS_DOC_PATH}/${SCHEMA_FILE}"

  jsonschema-markdown ${CRS_DOC_PATH}/${SCHEMA_FILE} > ${MARKDOWN_FILE}
  echo "Markdown file is generated and placed at ${MARKDOWN_FILE}"

  rm -rf "${TEMP_DIR}"
}

cleanup() {
  if [[ -n "$container_id" ]]; then
    echo "Interrupt received, stopping Docker container..."
    docker rm -f "$container_id"
    docker compose ${DOCKER_USER_ARGS} down
  else
    echo "Interrupt received, but no container ID found."
  fi
}

trap cleanup SIGINT

# array of top-level command handlers
declare -A MAIN_COMMANDS=(
  [help]=print_usage
  [install-yq]=install_yq
  [build-cp]=build_cp
  [build-crs]=build_crs
  [upload-base]=upload_base
  [run]=run
  [gen-doc]=gen_doc
  [custom]=custom
  [test]=test
)

#################################
## Main script code
#################################

# look for needed commands/dependencies
REQUIRED_COMMANDS="docker git yq jsonschema2md"
for c in ${REQUIRED_COMMANDS}; do
  command -v "${c}" >/dev/null || warn "WARNING: needed executable (${c}) not found in PATH"
done

# call subcommand function from declared array of handlers (default to help)
"${MAIN_COMMANDS[${1:-help}]:-${MAIN_COMMANDS[help]}}" "$@"
