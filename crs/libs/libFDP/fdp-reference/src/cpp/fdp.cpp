#include "./FuzzedDataProvider.h"

extern "C" {
void deinit(FuzzedDataProvider *fdp) {
  const uint8_t *data = fdp->data_ptr_orig_;
  delete fdp;
  delete[] data;
}

FuzzedDataProvider *init(void *data, size_t size) {
  uint8_t *buffer = new uint8_t[size];
  if (nullptr == buffer) {
    return nullptr;
  }

  memcpy(buffer, data, size);
  return new FuzzedDataProvider(buffer, size);
}

size_t remainingBytes(FuzzedDataProvider *fdp) { return fdp->remaining_bytes(); }
}
