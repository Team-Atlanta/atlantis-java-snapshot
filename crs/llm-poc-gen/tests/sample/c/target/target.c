#include "target.h"

void target_1(const uint8_t *Data, size_t Size) {
    size_t offset = 0;
    if (offset + 1 > Size) {
        return;
    }
    uint8_t one_byte = Data[offset];
    offset += 1;

    uint8_t *a = (uint8_t*)malloc(1);
    free(a);
    a[0] = one_byte;
}

void target_2(const uint8_t *Data, size_t Size) {
    size_t offset = 0;
    if (offset + 1 > Size) {
        return;
    }
    while(1);
}
