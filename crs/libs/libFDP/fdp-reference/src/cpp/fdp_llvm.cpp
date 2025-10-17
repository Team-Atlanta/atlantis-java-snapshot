#include <malloc.h>

#include "./FuzzedDataProvider.h"

extern "C" {
uint8_t consumeByteInRange(FuzzedDataProvider *fdp, uint8_t min, uint8_t max) {
  return fdp->ConsumeIntegralInRange(min, max);
}

char consumeCharInRange(FuzzedDataProvider *fdp, char min, char max) {
  return fdp->ConsumeIntegralInRange(min, max);
}

short consumeShortInRange(FuzzedDataProvider *fdp, short min, short max) {
  return fdp->ConsumeIntegralInRange(min, max);
}

unsigned short consumeUnsignedShortInRange(FuzzedDataProvider *fdp,
                                           unsigned short min,
                                           unsigned short max) {
  return fdp->ConsumeIntegralInRange(min, max);
}

int consumeIntInRange(FuzzedDataProvider *fdp, int min, int max) {
  return fdp->ConsumeIntegralInRange(min, max);
}

unsigned int consumeUnsignedIntInRange(FuzzedDataProvider *fdp,
                                       unsigned int min, unsigned int max) {
  return fdp->ConsumeIntegralInRange(min, max);
}

long long consumeLongLongInRange(FuzzedDataProvider *fdp, long long min,
                                 long long max) {
  return fdp->ConsumeIntegralInRange(min, max);
}

unsigned long long consumeUnsignedLongLongInRange(FuzzedDataProvider *fdp,
                                                  unsigned long long min,
                                                  unsigned long long max) {
  return fdp->ConsumeIntegralInRange(min, max);
}

uint8_t consumeByte(FuzzedDataProvider *fdp) {
  return fdp->ConsumeIntegral<uint8_t>();
}

char consumeChar(FuzzedDataProvider *fdp) {
  return fdp->ConsumeIntegral<char>();
}

short consumeShort(FuzzedDataProvider *fdp) {
  return fdp->ConsumeIntegral<short>();
}

unsigned short consumeUnsignedShort(FuzzedDataProvider *fdp) {
  return fdp->ConsumeIntegral<unsigned short>();
}

int consumeInt(FuzzedDataProvider *fdp) { return fdp->ConsumeIntegral<int>(); }

unsigned int consumeUnsignedInt(FuzzedDataProvider *fdp) {
  return fdp->ConsumeIntegral<unsigned int>();
}

long long consumeLongLong(FuzzedDataProvider *fdp) {
  return fdp->ConsumeIntegral<long long>();
}

unsigned long long consumeUnsignedLongLong(FuzzedDataProvider *fdp) {
  return fdp->ConsumeIntegral<unsigned long long>();
}

bool consumeBool(FuzzedDataProvider *fdp) { return fdp->ConsumeBool(); }

float consumeFloatInRange(FuzzedDataProvider *fdp, float min, float max) {
  return fdp->ConsumeFloatingPointInRange(min, max);
}

double consumeDoubleInRange(FuzzedDataProvider *fdp, double min, double max) {
  return fdp->ConsumeFloatingPointInRange(min, max);
}

float consumeFloat(FuzzedDataProvider *fdp) {
  return fdp->ConsumeFloatingPoint<float>();
}

double consumeDouble(FuzzedDataProvider *fdp) {
  return fdp->ConsumeFloatingPoint<double>();
}

float consumeProbabilityFloat(FuzzedDataProvider *fdp) {
  return fdp->ConsumeProbability<float>();
}

double consumeProbabilityDouble(FuzzedDataProvider *fdp) {
  return fdp->ConsumeProbability<double>();
}

unsigned int consumeEnum(FuzzedDataProvider *fdp, unsigned int max_value) {
  return consumeUnsignedIntInRange(fdp, 0, max_value);
}

size_t consumeBytes(FuzzedDataProvider *fdp, uint8_t *output,
                    size_t num_bytes) {
  auto out_vector = fdp->ConsumeBytes<uint8_t>(num_bytes);
  memcpy(output, out_vector.data(), out_vector.size());
  return out_vector.size();
}

size_t consumeBytesWithTerminator(FuzzedDataProvider *fdp, uint8_t *output,
                                  size_t num_bytes, uint8_t terminator = 0) {
  auto out_vector =
      fdp->ConsumeBytesWithTerminator<uint8_t>(num_bytes, terminator);
  memcpy(output, out_vector.data(), out_vector.size());
  return out_vector.size();
}

size_t consumeRemainingBytes(FuzzedDataProvider *fdp, uint8_t *output) {
  auto out_vector = fdp->ConsumeRemainingBytes<uint8_t>();
  memcpy(output, out_vector.data(), out_vector.size());
  return out_vector.size();
}

size_t consumeBytesAsString(FuzzedDataProvider *fdp, uint8_t *output,
                            size_t num_bytes) {
  auto out_string = fdp->ConsumeBytesAsString(num_bytes);
  memcpy(output, out_string.data(), out_string.size());
  return out_string.size();
}

size_t consumeRandomLengthStringWithMaxLength(FuzzedDataProvider *fdp,
                                              uint8_t *output,
                                              size_t max_length) {
  auto out_string = fdp->ConsumeRandomLengthString(max_length);
  memcpy(output, out_string.data(), out_string.size());
  return out_string.size();
}

size_t consumeRandomLengthString(FuzzedDataProvider *fdp, uint8_t *output) {
  auto out_string = fdp->ConsumeRandomLengthString();
  memcpy(output, out_string.data(), out_string.size());
  return out_string.size();
}

size_t consumeRemainingBytesAsString(FuzzedDataProvider *fdp, uint8_t *output) {
  auto out_string = fdp->ConsumeRemainingBytesAsString();
  memcpy(output, out_string.data(), out_string.size());
  return out_string.size();
}

size_t pickValueIndexInArray(FuzzedDataProvider *fdp, size_t size) {
  return fdp->ConsumeIntegralInRange((size_t)0, size - 1);
}
}
