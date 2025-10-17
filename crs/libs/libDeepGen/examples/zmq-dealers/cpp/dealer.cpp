#include <zmq.hpp>
#include <zmq_addon.hpp>
#include <iostream>
#include <string>
#include <vector>
#include <thread>
#include <chrono>
#include <random>
#include <sstream>
#include <mutex>
#include <condition_variable>
#include <atomic>
#include <csignal>
#include <cstdlib> // for std::exit

#include <nlohmann/json.hpp>
using json = nlohmann::json;

// Global signal handler variables
std::atomic<bool> g_running{true};
std::mutex g_mutex;
std::condition_variable g_cv;

// Signal handler to gracefully exit
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
    g_running = false;
    g_cv.notify_all();
}

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
    static std::string serialize(const SubmitBundle& bundle) {
        json j;
        j["script_id"] = bundle.script_id;
        j["harness_name"] = bundle.harness_name;
        j["shm_name"] = bundle.shm_name;
        j["seed_ids"] = bundle.seed_ids;
        return j.dump();
    }

    // Deserialization
    static SubmitBundle deserialize(const std::string& data) {
        json j = json::parse(data);
        return SubmitBundle(
            j["script_id"].get<int>(),
            j["harness_name"].get<std::string>(),
            j["shm_name"].get<std::string>(),
            j["seed_ids"].get<std::vector<int>>()
        );
    }
};

// Logger class
class Logger {
private:
    std::string name;
    std::mutex log_mutex;

public:
    enum Level { DEBUG, INFO, WARNING, ERROR };
    Level level = INFO;

    explicit Logger(std::string name) : name(std::move(name)) {}

    void debug(const std::string& message) {
        if (level <= DEBUG) log(DEBUG, message);
    }

    void info(const std::string& message) {
        if (level <= INFO) log(INFO, message);
    }

    void warning(const std::string& message) {
        if (level <= WARNING) log(WARNING, message);
    }

    void error(const std::string& message) {
        if (level <= ERROR) log(ERROR, message);
    }

private:
    void log(Level msg_level, const std::string& message) {
        std::lock_guard<std::mutex> lock(log_mutex);
        
        auto now = std::chrono::system_clock::now();
        auto time = std::chrono::system_clock::to_time_t(now);
        std::tm tm_buf{};
        
#ifdef _WIN32
        localtime_s(&tm_buf, &time);
#else
        localtime_r(&time, &tm_buf);
#endif
        
        char time_buf[20];
        std::strftime(time_buf, sizeof(time_buf), "%Y-%m-%d %H:%M:%S", &tm_buf);
        
        const char* level_str;
        switch (msg_level) {
            case DEBUG: level_str = "DEBUG"; break;
            case INFO: level_str = "INFO"; break;
            case WARNING: level_str = "WARNING"; break;
            case ERROR: level_str = "ERROR"; break;
            default: level_str = "UNKNOWN";
        }
        
        std::cout << time_buf << " - " << name << " - " << level_str << " - " << message << std::endl;
    }
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
    std::shared_ptr<Logger> logger;
    
    std::thread heartbeat_thread;
    std::atomic<bool> heartbeat_running{true};

public:
    Dealer(const std::string& router_addr = "ipc:///tmp/haha", 
           const std::string& harness = "Rdf4jOne",
           int heartbeat_interval = 5)
        : context(1), socket(context, zmq::socket_type::dealer),
          router_addr(router_addr), harness(harness), heartbeat_interval(heartbeat_interval),
          logger(std::make_shared<Logger>("dealer")) {
        
        // Generate unique dealer ID
        std::random_device rd;
        std::mt19937 rng(rd());
        std::uniform_int_distribution<> dist(0, 0xFFFF);
        std::stringstream ss;
        ss << "SC-" << std::hex << dist(rng);
        dealer_id = ss.str();
        
        // Set identity on socket
        socket.set(zmq::sockopt::routing_id, dealer_id);
        logger->info("Dealer created with identity: " + dealer_id);
        
        // Connect to router
        socket.connect(router_addr);
        logger->info("Connected to router at " + router_addr);
    }
    
    ~Dealer() {
        stop();
    }
    
    void stop() {
        heartbeat_running = false;
        
        if (heartbeat_thread.joinable()) {
            heartbeat_thread.join();
        }
        
        if (socket) {
            socket.close();
        }
        
        logger->info("Dealer shutdown complete");
    }
    
    void start_heartbeat() {
        heartbeat_thread = std::thread([this]() {
            heartbeat_loop();
        });
    }
    
    void heartbeat_loop() {
        logger->info("Starting heartbeat loop (interval: " + std::to_string(heartbeat_interval) + "s)");
        int heartbeat_count = 0;
        
        try {
            while (heartbeat_running && g_running) {
                logger->info("Sending HEARTBEAT " + std::to_string(heartbeat_count));
                
                std::vector<zmq::message_t> messages;
                messages.emplace_back("HEARTBEAT", 9);
                messages.emplace_back(harness.c_str(), harness.size());
                
                try {
                    zmq::send_multipart(socket, messages);
                }
                catch (const zmq::error_t& e) {
                    logger->error("Error sending heartbeat: " + std::string(e.what()));
                }
                
                heartbeat_count++;
                if (heartbeat_count % 10 == 0) {
                    logger->info("Sent " + std::to_string(heartbeat_count) + " heartbeats so far");
                }
                
                // Sleep for the heartbeat interval
                std::unique_lock<std::mutex> lock(g_mutex);
                g_cv.wait_for(lock, std::chrono::seconds(heartbeat_interval), 
                             [this]() { return !heartbeat_running || !g_running; });
            }
        }
        catch (const std::exception& e) {
            logger->error("Error in heartbeat loop: " + std::string(e.what()));
        }
        
        logger->info("Heartbeat loop terminated");
    }
    
    void run() {
        logger->info("Starting dealer main loop");
        start_heartbeat();
        
        int seed_count = 0;
        int last_printed_count = 0;
        
        try {
            // Set a polling timeout to regularly check if we need to exit
            zmq::pollitem_t items[] = {
                { socket.handle(), 0, ZMQ_POLLIN, 0 }
            };
            
            while (g_running) {
                // Use polling with a short timeout to allow checking g_running
                zmq::poll(items, 1, std::chrono::milliseconds(100)); // 100ms timeout
                
                if (!g_running) {
                    logger->info("Shutdown signal received, exiting main loop");
                    break;
                }
                
                // Check if we have a message
                if (!(items[0].revents & ZMQ_POLLIN)) {
                    continue;
                }
                
                std::vector<zmq::message_t> frames;
                const auto result = zmq::recv_multipart(socket, std::back_inserter(frames), zmq::recv_flags::dontwait);
                
                if (!result) {
                    continue;
                }
                
                if (frames.empty()) {
                    continue;
                }
                
                // Convert first frame to string for command
                std::string cmd(static_cast<char*>(frames[0].data()), frames[0].size());
                logger->debug("Received command: " + cmd);
                
                if (cmd == "SEED" && frames.size() >= 3) {
                    // Extract message ID and bundle data
                    std::string msg_id(static_cast<char*>(frames[1].data()), frames[1].size());
                    std::string bundle_data(static_cast<char*>(frames[2].data()), frames[2].size());
                    
                    logger->debug("Received SEED BATCH msg: msg_id=" + msg_id);
                    
                    try {
                        // Parse the bundle
                        SubmitBundle bundle = SubmitBundle::deserialize(bundle_data);
                        seed_count += bundle.seed_ids.size();
                        
                        // Send ACK
                        logger->debug("Sending ACK for seed " + msg_id);
                        std::vector<zmq::message_t> ack_frames;
                        ack_frames.emplace_back("ACK", 3);
                        ack_frames.emplace_back(msg_id.c_str(), msg_id.size());
                        ack_frames.emplace_back(bundle_data.c_str(), bundle_data.size());
                        
                        zmq::send_multipart(socket, ack_frames);
                        logger->debug("ACK sent for seed " + msg_id);
                        
                        if (seed_count - last_printed_count >= 1000) {
                            logger->info("Processed " + std::to_string(seed_count) + " seeds so far");
                            last_printed_count = seed_count;
                        }
                    }
                    catch (const json::parse_error& e) {
                        logger->error("JSON parse error: " + std::string(e.what()));
                    }
                    catch (const std::exception& e) {
                        logger->error("Error processing bundle: " + std::string(e.what()));
                    }
                }
                else {
                    logger->warning("Received unknown command: " + cmd);
                }
            }
        }
        catch (const zmq::error_t& e) {
            logger->error("ZMQ error: " + std::string(e.what()));
        }
        catch (const std::exception& e) {
            logger->error("Error in dealer main loop: " + std::string(e.what()));
        }
        
        stop();
        logger->info("Main loop exited");
    }
};

int main(int argc, char* argv[]) {
    // Set up signal handlers
    std::signal(SIGINT, signal_handler);
    std::signal(SIGTERM, signal_handler);
    
    // Default parameters
    std::string router_addr = "ipc:///tmp/haha";
    std::string harness = "Rdf4jOne";
    int heartbeat_interval = 5;
    
    // Parse command line arguments
    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];
        if (arg == "--router" && i + 1 < argc) {
            router_addr = argv[++i];
        }
        else if (arg == "--harness" && i + 1 < argc) {
            harness = argv[++i];
        }
        else if (arg == "--heartbeat" && i + 1 < argc) {
            heartbeat_interval = std::stoi(argv[++i]);
        }
        else if (arg == "--help") {
            std::cout << "Usage: " << argv[0] << " [--router ADDR] [--harness NAME] [--heartbeat SECONDS]" << std::endl;
            return 0;
        }
    }
    
    try {
        Dealer dealer(router_addr, harness, heartbeat_interval);
        dealer.run();
    }
    catch (const std::exception& e) {
        std::cerr << "Fatal error: " << e.what() << std::endl;
        return 1;
    }
    
    std::cout << "Dealer exited cleanly" << std::endl;
    return 0;
}
