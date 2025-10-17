#include "utils.h"
#include <openssl/evp.h>
#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <cstring> // for memcpy

// Calculate SHA256 hash of data
std::string calculate_sha256(const std::vector<uint8_t>& data) {
    unsigned char hash[EVP_MAX_MD_SIZE];
    unsigned int hash_len;
    
    // Create message digest context
    EVP_MD_CTX* ctx = EVP_MD_CTX_new();
    if (!ctx) {
        throw std::runtime_error("Failed to create EVP_MD_CTX");
    }
    
    // Initialize with SHA256 algorithm
    EVP_DigestInit_ex(ctx, EVP_sha256(), nullptr);
    EVP_DigestUpdate(ctx, data.data(), data.size());
    EVP_DigestFinal_ex(ctx, hash, &hash_len);
    
    // Free the context
    EVP_MD_CTX_free(ctx);
    
    // Convert hash to hex string
    std::stringstream ss;
    for (unsigned int i = 0; i < hash_len; i++) {
        ss << std::hex << std::setw(2) << std::setfill('0') << static_cast<int>(hash[i]);
    }
    return ss.str();
}