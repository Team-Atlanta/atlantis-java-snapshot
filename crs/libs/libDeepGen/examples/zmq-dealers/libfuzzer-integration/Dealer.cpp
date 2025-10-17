#include "Dealer.h"
#include "utils.h"
#include <iostream>
#include <cstdarg> // for va_list
#include <cstdlib> // for std::exit
#include <iomanip> // for std::setw, std::setfill

using json = nlohmann::json;

static FILE* OutputFile = stdout;

// Reference to the active dealer for signal handling
Dealer* g_active_dealer = nullptr;

void Printf(const char *Fmt, ...) {
  va_list ap;
  va_start(ap, Fmt);
  vfprintf(OutputFile, Fmt, ap);
  va_end(ap);
  fflush(OutputFile);
}

// Serialization implementation for SubmitBundle
std::string SubmitBundle::serialize(const SubmitBundle& bundle) {
    json j;
    j["script_id"] = bundle.script_id;
    j["harness_name"] = bundle.harness_name;
    j["shm_name"] = bundle.shm_name;
    j["seed_ids"] = bundle.seed_ids;
    return j.dump();
}

// Deserialization implementation for SubmitBundle
SubmitBundle SubmitBundle::deserialize(const std::string& data) {
    json j = json::parse(data);
    return SubmitBundle(
        j["script_id"].get<int>(),
        j["harness_name"].get<std::string>(),
        j["shm_name"].get<std::string>(),
        j["seed_ids"].get<std::vector<int>>()
    );
}

// Dealer constructor
Dealer::Dealer(const std::string& router_addr, 
       const std::string& harness, 
       int heartbeat_interval,
       size_t queue_size)
    : context(1), socket(context, zmq::socket_type::dealer),
      router_addr(router_addr), harness(harness), heartbeat_interval(heartbeat_interval),
      seed_queue(queue_size) {
    
    // Generate unique dealer ID
    std::random_device rd;
    std::mt19937 rng(rd());
    std::uniform_int_distribution<> dist(0, 0xFFFF);
    std::stringstream ss;
    ss << "SC-" << std::hex << dist(rng);
    dealer_id = ss.str();
    
    // Set identity on socket
    socket.set(zmq::sockopt::routing_id, dealer_id);
    Printf("Dealer created with identity: %s\n", dealer_id.c_str());
    
    // Connect to router
    socket.connect(router_addr);
    Printf("Connected to router at %s\n", router_addr.c_str());
}

// Dealer destructor
Dealer::~Dealer() {
    stop();
}

// Signal the dealer to stop
void Dealer::signal_stop() {
    running = false;
    cv.notify_all();
}

// Stop the dealer and clean up resources
void Dealer::stop() {
    // Signal threads to exit
    signal_stop();
    
    // Join threads
    join();
    
    // Close socket
    if (socket) {
        socket.close();
    }
    
    // Clean up shared memory consumers
    shm_consumers.clear();
    
    Printf("Dealer shutdown complete\n");
}

// Join all threads without signaling stop
void Dealer::join() {
    // Join threads without signaling stop
    if (polling_thread.joinable()) {
        polling_thread.join();
    }
    
    if (heartbeat_thread.joinable()) {
        heartbeat_thread.join();
    }
}

// Heartbeat loop implementation
void Dealer::heartbeat_loop() {
    Printf("Starting heartbeat loop (interval: %ds)\n", heartbeat_interval);
    int heartbeat_count = 0;
    
    try {
        while (running) {
            Printf("Sending HEARTBEAT %d\n", heartbeat_count);
            
            std::vector<zmq::message_t> messages;
            messages.emplace_back("HEARTBEAT", 9);
            messages.emplace_back(harness.c_str(), harness.size());
            
            try {
                zmq::send_multipart(socket, messages);
            }
            catch (const zmq::error_t& e) {
                Printf("Error sending heartbeat: %s\n", e.what());
            }
            
            heartbeat_count++;
            if (heartbeat_count % 10 == 0) {
                Printf("Sent %d heartbeats so far\n", heartbeat_count);
            }
            
            // Sleep for the heartbeat interval
            std::unique_lock<std::mutex> lock(mutex);
            cv.wait_for(lock, std::chrono::seconds(heartbeat_interval), 
                       [this]() { return !running; });
        }
    }
    catch (const std::exception& e) {
        Printf("Error in heartbeat loop: %s\n", e.what());
    }
    
    Printf("Heartbeat loop terminated\n");
}


// Get or create a SeedShmemPoolConsumer for the given shared memory name
SeedShmemPoolConsumer& Dealer::get_consumer(const std::string& shm_name) {
    auto it = shm_consumers.find(shm_name);
    if (it == shm_consumers.end()) {
        // Create a new consumer
        Printf("Creating new consumer for shared memory: %s\n", shm_name.c_str());
        auto consumer = std::make_unique<SeedShmemPoolConsumer>(shm_name);
        auto& result = *consumer;
        shm_consumers[shm_name] = std::move(consumer);
        return result;
    }
    return *(it->second);
}

// Process SEED message implementation
void Dealer::process_seed_msg(const std::string& msg_id, const std::string& bundle_data) {
    Printf("Received SEED BATCH msg: msg_id=%s\n", msg_id.c_str());
    
    try {
        // Parse the bundle
        SubmitBundle bundle = SubmitBundle::deserialize(bundle_data);
        seed_count += bundle.seed_ids.size();
        
        // Get or create consumer for this shared memory
        try {
            SeedShmemPoolConsumer& consumer = get_consumer(bundle.shm_name);
            
            // Process each seed ID
            for (int seed_id : bundle.seed_ids) {
                try {
                    // Get seed content
                    std::vector<uint8_t> seed_content = consumer.getSeedContent(seed_id);
                    if (!seed_content.empty()) {
                        // Calculate SHA256 hash for validation
                        // std::string sha256 = calculate_sha256(seed_content);
                        //Printf("CHECK %s, %s, %d, %s\n", msg_id.c_str(), bundle.shm_name.c_str(), seed_id, sha256.c_str());
                        //Printf("CHECK %s\n", sha256.c_str());

                        // Avoid busy waiting & use move semantics to avoid copying
                        while (!seed_queue.try_push(std::move(seed_content))) {
                            std::this_thread::sleep_for(std::chrono::milliseconds(100));
                        }
                    } else {
                        Printf("Empty seed content for %s, %d\n", bundle.shm_name.c_str(), seed_id);
                    }
                } catch (const std::exception& e) {
                    Printf("Error processing seed ID %d: %s\n", seed_id, e.what());
                }
            }
        } catch (const std::exception& e) {
            Printf("Error with shared memory %s: %s\n", bundle.shm_name.c_str(), e.what());
        }
        
        if (seed_count - last_printed_count >= 1000) {
            Printf("Processed %d seeds so far\n", seed_count);
            last_printed_count = seed_count;
        }
    }
    catch (const json::parse_error& e) {
        Printf("JSON parse error: %s\n", e.what());
    }
    catch (const std::exception& e) {
        Printf("Error processing bundle: %s\n", e.what());
    }
}

// Send ACK for a processed message
void Dealer::send_ack_msg(const std::string& msg_id, const std::string& bundle_data) {
    Printf("Sending ACK for seed %s\n", msg_id.c_str());
    
    std::vector<zmq::message_t> ack_frames;
    ack_frames.emplace_back("ACK", 3);
    ack_frames.emplace_back(msg_id.c_str(), msg_id.size());
    ack_frames.emplace_back(bundle_data.c_str(), bundle_data.size());
    
    try {
        zmq::send_multipart(socket, ack_frames);
        Printf("ACK sent for seed %s\n", msg_id.c_str());
    }
    catch (const zmq::error_t& e) {
        Printf("Error sending ACK: %s\n", e.what());
    }
}

// Polling loop implementation
void Dealer::polling_loop() {
    Printf("Starting polling loop\n");
    
    try {
        // Set a polling timeout to regularly check if we need to exit
        zmq::pollitem_t items[] = {
            { socket.handle(), 0, ZMQ_POLLIN, 0 }
        };
        
        while (running) {
            // Use polling with a short timeout to allow checking running
            zmq::poll(items, 1, std::chrono::milliseconds(100)); // 100ms timeout
            
            if (!running) {
                Printf("Shutdown signal received, exiting polling loop\n");
                break;
            }
            
            // Check if we have a message
            if (!(items[0].revents & ZMQ_POLLIN)) {
                continue;
            }
            
            std::vector<zmq::message_t> frames;
            const auto result = zmq::recv_multipart(socket, std::back_inserter(frames), zmq::recv_flags::dontwait);
            
            if (!result || frames.empty()) {
                continue;
            }
            
            // Convert first frame to string for command
            std::string cmd(static_cast<char*>(frames[0].data()), frames[0].size());
            Printf("Received command: %s\n", cmd.c_str());
            
            if (cmd == "SEED" && frames.size() >= 3) {
                std::string msg_id(static_cast<char*>(frames[1].data()), frames[1].size());
                std::string bundle_data(static_cast<char*>(frames[2].data()), frames[2].size());
                
                process_seed_msg(msg_id, bundle_data);
                send_ack_msg(msg_id, bundle_data);
            }
            else {
                Printf("Received unknown command: %s\n", cmd.c_str());
            }
        }
    }
    catch (const zmq::error_t& e) {
        Printf("ZMQ error: %s\n", e.what());
    }
    catch (const std::exception& e) {
        Printf("Error in polling loop: %s\n", e.what());
    }
    
    Printf("Polling loop exited\n");
}

// Run the dealer
void Dealer::run(bool wait_until_stop) {
    Printf("Starting dealer backend\n");
    
    heartbeat_thread = std::thread([this]() {
        heartbeat_loop();
    });
    
    polling_thread = std::thread([this]() {
        polling_loop();
    });
    
    Printf("Dealer backend started\n");
    
    // If wait option is enabled, just wait for threads to complete
    if (wait_until_stop) {
        join();
    }
}

// Try to get the next seed from the queue
bool Dealer::try_get_next_seed(char* seed_content, size_t* size, size_t max_size) {
    std::vector<uint8_t>* seed = seed_queue.front();
    if (seed) {
        // Copy the seed content to the provided buffer
        *size = seed->size();
        size_t copy_size = std::min(*size, max_size);
        for (size_t i = 0; i < copy_size; ++i) {
            seed_content[i] = static_cast<char>((*seed)[i]);
        }
        seed_queue.pop();
        return true;
    }
    return false;
}

// Implementation of the signal handler
void signal_handler(int sig) {
    // Only change state once to avoid double-exit issues
    static std::atomic<bool> already_handled{false};
    bool expected = false;
    if (!already_handled.compare_exchange_strong(expected, true)) {
        // If we've already handled a signal, force exit on second signal
        std::cerr << "\nForced exit due to repeated signals." << std::endl;
        std::exit(128 + sig);
        return;
    }
    
    std::cerr << "\nShutting down gracefully, press Ctrl+C again to force exit..." << std::endl;
    
    // Signal the dealer to stop if it exists
    if (g_active_dealer) {
        g_active_dealer->signal_stop();
    }
}