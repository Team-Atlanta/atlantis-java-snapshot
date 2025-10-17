#include "Dealer.h"
#include "utils.h"
#include <iostream>
#include <csignal>
#include <string>

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
    
    std::cout << "Starting dealer, press Ctrl+C to exit..." << std::endl;
    
    try {
        // Create dealer instance
        Dealer dealer(router_addr, harness, heartbeat_interval);
        
        // Register for signal handling
        g_active_dealer = &dealer;
        
        // Start the dealer but don't wait for completion
        dealer.run(false);

        char seed_content[65536];
        size_t seed_size = 0;
        
        // Process seeds in the main thread
        while (dealer.is_running()) {
            // Try to get a seed from the queue
            bool succ = dealer.try_get_next_seed(seed_content, &seed_size, sizeof(seed_content));
            
            if (succ) {
                // Calculate SHA256 hash
                std::string sha256 = calculate_sha256(std::vector<uint8_t>(seed_content, seed_content + seed_size));
                
                // Print results in the required format
                Printf("MAIN CHECK %s\n", sha256.c_str());
            } else {
                // No seeds available, sleep briefly to avoid busy-waiting
                std::this_thread::sleep_for(std::chrono::milliseconds(10));
            }
        }
        
        // Make sure the dealer is fully stopped before joining 
        dealer.signal_stop();
        dealer.join();
        
        std::cout << "All done! Dealer stopped and joined." << std::endl;
        
        // When we reach here, the dealer has already been cleaned up by join()
        g_active_dealer = nullptr;
    }
    catch (const std::exception& e) {
        std::cerr << "Fatal error: " << e.what() << std::endl;
        return 1;
    }
    
    std::cout << "Dealer exited cleanly" << std::endl;
    return 0;
}