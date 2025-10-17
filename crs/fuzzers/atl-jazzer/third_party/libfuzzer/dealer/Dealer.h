#pragma once

#include <zmq.hpp>
#include <zmq_addon.hpp>
#include <string>
#include <vector>
#include <thread>
#include <chrono>
#include <random>
#include <sstream>
#include <mutex>
#include <condition_variable>
#include <atomic>
#include <unordered_map>
#include <memory>
#include <openssl/evp.h>
#include <nlohmann/json.hpp>
#include "SeedShmemPoolConsumer.h"
#include "SPSCQueue.h"

// Forward declaration
class Dealer;
extern Dealer* g_active_dealer;

// SubmitBundle class equivalent to Python dataclass
class SubmitBundle {
public:
    int script_id;
    std::string harness_name;
    std::string shm_name;
    std::vector<int> seed_ids;

    // Constructor
    SubmitBundle(int script_id, std::string harness_name, std::string shm_name, std::vector<int> seed_ids)
        : script_id(script_id), harness_name(std::move(harness_name)), shm_name(std::move(shm_name)), seed_ids(std::move(seed_ids)) {}

    // Serialization
    static std::string serialize(const SubmitBundle& bundle);

    // Deserialization
    static SubmitBundle deserialize(const std::string& data);
};

// Dealer class
class Dealer {
private:
    zmq::context_t context;
    zmq::socket_t socket;
    std::string dealer_id;
    std::string router_addr;
    std::string harness;
    int heartbeat_interval;
    int seed_count{0};
    int last_printed_count{0};
    
    // Output file for logging
    FILE* output_file{nullptr};
    
    // Queue for seed content
    rigtorp::SPSCQueue<std::vector<uint8_t>> seed_queue;
    
    // Map from shm_name to SeedShmemPoolConsumer
    std::unordered_map<std::string, std::unique_ptr<SeedShmemPoolConsumer>> shm_consumers;
    
    // Thread management
    std::thread heartbeat_thread;
    std::thread polling_thread;
    
    // Synchronization primitives
    std::atomic<bool> running{true};
    std::mutex mutex;
    std::condition_variable cv;
    
    // Internal thread loops
    void heartbeat_loop();
    void polling_loop();
    void process_seed_msg(const std::string& msg_id, const std::string& bundle_data);
    void send_ack_msg(const std::string& msg_id, const std::string& bundle_data);
    
    // Get or create a SeedShmemPoolConsumer for the given shared memory name
    SeedShmemPoolConsumer& get_consumer(const std::string& shm_name);

public:
    // Printf method for logging
    void Printf(const char *Fmt, ...);
    
    // Signal the dealer to stop
    void signal_stop();
    
    // Check if dealer is still running
    bool is_running() const { return running.load(); }
    
    Dealer(const std::string& router_addr = "ipc:///tmp/haha", 
           const std::string& harness = "Rdf4jOne",
           int heartbeat_interval = 5,
           size_t queue_size = 1000,
           const std::string& log_file_path = "",
           const std::string& custom_dealer_id = "");
    
    ~Dealer();
    
    void stop();
    
    void run(bool wait_until_stop = false);
    
    // Wait for all threads to complete
    void join();
    
    bool try_get_next_seed(uint8_t* seed_content, size_t* size, size_t max_size);
};
