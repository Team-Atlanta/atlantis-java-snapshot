#pragma once

#include <string>
#include <vector>
#include <cstdint>

// Calculate SHA256 hash of data
std::string calculate_sha256(const std::vector<uint8_t>& data);

// Utility function for printing (already defined in dealer.cpp)
void Printf(const char *Fmt, ...);