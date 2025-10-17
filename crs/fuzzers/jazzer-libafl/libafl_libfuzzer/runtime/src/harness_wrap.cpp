#include "harness_wrap.h"

extern "C" int libafl_libfuzzer_test_one_input(
    int (*harness)(const uint8_t *, size_t), const uint8_t *data, size_t len) {
  return harness(data, len);
}
