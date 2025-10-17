#include <stddef.h>
#include <stdint.h>
#include "target/target.h"

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *Data, size_t Size) {
    size_t offset = 0;
    if (offset + 1 > Size) {
        return 0;
    }

    int picker = (int)Data[offset];
    offset += 1;

    switch (picker) {
        case 50:
            target_1(Data+offset, Size-offset);
            break;
        case 51:
            target_2(Data+offset, Size-offset);
            break;
    }
    return 0;
}
