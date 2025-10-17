#!/bin/sh

set -eu

SCRIPT="compile-wrapper.sh"
BIN="bear"

nix_dev() {
    nix \
        --extra-experimental-features nix-command \
        --extra-experimental-features flakes \
        develop \
        -c $@
}

BEARELF_RES=$(nix_dev fd libear.so /nix/store)
BEARELF=$(echo "$BEARELF_RES" | head -n1)

nix_dev ./extract-runtime-deps.sh $BEARELF
nix_dev ./extract-runtime-deps.sh $BIN

cat <<EOF > $SCRIPT
#!/bin/sh -e

if [ -f /out/compile_commands.json ]; then
  echo "compile_commands.json already built"
  exit 0
fi
 
FUZZING_LANGUAGE=c $(nix_dev which $BIN) --cdb /out/compile_commands.json compile
/out/expand_preprocessor.py
EOF

chmod 755 $SCRIPT

