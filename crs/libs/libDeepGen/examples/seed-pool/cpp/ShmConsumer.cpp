#include "SeedShmemPoolConsumer.h"
#include <iostream>
#include <iomanip>
#include <sstream>
#include <openssl/evp.h>

// Compute SHA-256 hash of data using modern EVP interface
std::string sha256Hex(const std::vector<uint8_t>& data) {
    unsigned char hash[EVP_MAX_MD_SIZE];
    unsigned int hash_len;
    
    // Create message digest context
    EVP_MD_CTX* ctx = EVP_MD_CTX_new();
    if (!ctx) {
        throw std::runtime_error("Failed to create EVP_MD_CTX");
    }
    
    // Initialize the hash
    EVP_DigestInit_ex(ctx, EVP_sha256(), nullptr);
    EVP_DigestUpdate(ctx, data.data(), data.size());
    EVP_DigestFinal_ex(ctx, hash, &hash_len);
    EVP_MD_CTX_free(ctx);
    
    // Convert to hex string
    std::stringstream ss;
    for (unsigned int i = 0; i < hash_len; i++) {
        ss << std::hex << std::setw(2) << std::setfill('0') << static_cast<int>(hash[i]);
    }
    return ss.str();
}

// Print hexdump of data
void hexdump(const std::vector<uint8_t>& data) {
    const int perLine = 16;
    
    for (size_t i = 0; i < data.size(); i += perLine) {
        // Print offset
        std::cout << std::hex << std::setw(8) << std::setfill('0') << i << "  ";
        
        // Print hex values
        for (int j = 0; j < perLine; ++j) {
            if (i + j < data.size()) {
                std::cout << std::hex << std::setw(2) << std::setfill('0') 
                          << static_cast<int>(data[i + j]) << " ";
            } else {
                std::cout << "   ";
            }
            if (j == 7) std::cout << " ";
        }
        
        // Print ASCII representation
        std::cout << " |";
        for (int j = 0; j < perLine; ++j) {
            if (i + j < data.size()) {
                unsigned char c = data[i + j];
                if (c >= 32 && c <= 126) {
                    std::cout << static_cast<char>(c);
                } else {
                    std::cout << ".";
                }
            } else {
                std::cout << " ";
            }
        }
        std::cout << "|\n";
    }
}

int main(int argc, char** argv) {
    if (argc != 3) {
        std::cerr << "usage: " << argv[0] << " <shm_name> <seed_id>" << std::endl;
        return 1;
    }
    
    std::string shm_name = argv[1];
    int seed_id = std::stoi(argv[2]);
    
    try {
        SeedShmemPoolConsumer consumer(shm_name);
        std::vector<uint8_t> data = consumer.getSeedContent(seed_id);
        
        if (data.empty()) {
            std::cout << "slot empty or invalid" << std::endl;
            return 1;
        }
        
        std::cout << "length = " << data.size() << " bytes" << std::endl;
        std::cout << "sha256 = " << sha256Hex(data) << std::endl;
        hexdump(data);
        
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
    
    return 0;
}