if [ $# -ge 1 ]; then
  # each arg is a corpus directory, call find-sink.sh separately to reduce disk pressue
  n=0
  for corpus_dir in "$@"; do
    echo "Run find-sink.sh for $corpus_dir"
    bash ./find-sink.sh $corpus_dir
    mv log-find-sink log-find-sink-corpus-dir-${n}
    mv json-result-sink json-result-sink-corpus-dir-${n}
    mv artifact-sink artifact-sink-corpus-dir-${n}
    n=$((n+1))
    echo "Done find-sink.sh for $corpus_dir"
  done
fi
