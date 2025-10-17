#pragma once

#include <cstdint>
#include <string>
#include <vector>
#include <stdexcept>
#include <memory>
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>

/**
 *  ★ Memory layout *
 *    Header(8B) : <item_size:uint32><item_num:uint32>   (Little-Endian)
 *    Item[n]    : <data_len:uint32><payload Bytes …>
 */
class SeedShmemPoolConsumer {
private:
    static constexpr int HEADER_SIZE = 8;
    static constexpr int LEN_FIELD_SIZE = 4;

    int fd_;                  // File descriptor for shared memory
    void* mapped_memory_;     // Pointer to mapped memory
    size_t file_size_;        // Size of the shared memory file
    uint32_t item_size_;      // Size of each item in bytes
    uint32_t item_num_;       // Number of items

public:
    /**
     * @param shm_name /dev/shm/<shm_name>
     */
    explicit SeedShmemPoolConsumer(const std::string& shm_name);
    ~SeedShmemPoolConsumer();

    // Prevent copying
    SeedShmemPoolConsumer(const SeedShmemPoolConsumer&) = delete;
    SeedShmemPoolConsumer& operator=(const SeedShmemPoolConsumer&) = delete;

    /**
     * Read the payload of the specified seedId.
     * @return empty vector if data_len == 0; otherwise, return the copied byte vector.
     */
    std::vector<uint8_t> getSeedContent(int seed_id) const;

    uint32_t getItemNum() const { return item_num_; }
    uint32_t getItemSize() const { return item_size_; }

private:
    size_t itemOffset(int idx) const;
};