#include "SeedShmemPoolConsumer.h"
#include <filesystem>
#include <stdexcept>
#include <cstring>

SeedShmemPoolConsumer::SeedShmemPoolConsumer(const std::string& shm_name) 
    : fd_(-1), mapped_memory_(nullptr), file_size_(0), item_size_(0), item_num_(0) {
    
    std::filesystem::path shm_path = std::filesystem::path("/dev/shm") / shm_name;
    
    // Open the shared memory file for reading
    fd_ = open(shm_path.c_str(), O_RDONLY);
    if (fd_ == -1) {
        throw std::runtime_error("Failed to open shared memory: " + std::string(strerror(errno)));
    }
    
    // Get the file size
    struct stat sb;
    if (fstat(fd_, &sb) == -1) {
        close(fd_);
        throw std::runtime_error("Failed to get shared memory size: " + std::string(strerror(errno)));
    }
    file_size_ = sb.st_size;
    
    // Map the shared memory into our address space
    mapped_memory_ = mmap(nullptr, file_size_, PROT_READ, MAP_SHARED, fd_, 0);
    if (mapped_memory_ == MAP_FAILED) {
        close(fd_);
        throw std::runtime_error("Failed to map shared memory: " + std::string(strerror(errno)));
    }
    
    // Read header information (ensuring proper endianness)
    // The shared memory uses little-endian format
    uint32_t item_size_raw, item_num_raw;
    memcpy(&item_size_raw, static_cast<uint8_t*>(mapped_memory_), sizeof(uint32_t));
    memcpy(&item_num_raw, static_cast<uint8_t*>(mapped_memory_) + sizeof(uint32_t), sizeof(uint32_t));
    
    // Convert from little-endian if needed
    item_size_ = item_size_raw;
    item_num_ = item_num_raw;
    
    // Verify size consistency
    size_t expected_size = HEADER_SIZE + static_cast<size_t>(item_size_) * item_num_;
    if (expected_size != file_size_) {
        munmap(mapped_memory_, file_size_);
        close(fd_);
        throw std::runtime_error("Shared memory size mismatch, expected=" + 
                                std::to_string(expected_size) + ", real=" + 
                                std::to_string(file_size_));
    }
}

SeedShmemPoolConsumer::~SeedShmemPoolConsumer() {
    if (mapped_memory_ != nullptr && mapped_memory_ != MAP_FAILED) {
        munmap(mapped_memory_, file_size_);
    }
    if (fd_ != -1) {
        close(fd_);
    }
}

size_t SeedShmemPoolConsumer::itemOffset(int idx) const {
    if (idx < 0 || idx >= static_cast<int>(item_num_)) {
        throw std::out_of_range("Seed index out of range");
    }
    return HEADER_SIZE + idx * item_size_;
}

std::vector<uint8_t> SeedShmemPoolConsumer::getSeedContent(int seed_id) const {
    if (seed_id < 0 || seed_id >= static_cast<int>(item_num_)) {
        return {};  // Return empty vector for invalid seed_id
    }
    
    size_t offset = itemOffset(seed_id);
    
    // Read the data length
    uint32_t data_len;
    memcpy(&data_len, static_cast<const uint8_t*>(mapped_memory_) + offset, sizeof(uint32_t));
    
    // Validate the data length
    if (data_len == 0 || data_len > item_size_ - LEN_FIELD_SIZE) {
        return {};  // Empty or broken data
    }
    
    // Copy the payload data
    std::vector<uint8_t> data(data_len);
    const uint8_t* payload_start = static_cast<const uint8_t*>(mapped_memory_) + 
                                 offset + LEN_FIELD_SIZE;
    std::memcpy(data.data(), payload_start, data_len);
    
    return data;
}