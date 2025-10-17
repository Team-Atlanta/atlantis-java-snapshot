package dealer;

import org.zeromq.SocketType;
import org.zeromq.ZMQ;
import org.zeromq.ZContext;

import java.util.List;
import java.util.UUID;
import java.util.ArrayList;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.logging.Logger;
import java.util.logging.Level;
import java.util.logging.LogManager;
import java.util.logging.ConsoleHandler;
import java.util.logging.SimpleFormatter;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.JsonNode;

/**
 * Seed-Consumer (DEALER)
 * Java implementation of examples/seed-id-0mq-jvm/dealer.py
 */
public class SeedConsumer implements AutoCloseable {
    private static final String ROUTER_ADDR = "tcp://localhost:5555";
    private static final int HB_INTERVAL_SECONDS = 5;
    private static final String HARNESS = "Rdf4jOne";

    private static final Logger logger = Logger.getLogger("dealer");
    private static final ObjectMapper mapper = new ObjectMapper();
    
    private final ZContext context;
    private final ZMQ.Socket dealer;
    private final String dealerId;
    private final AtomicBoolean running = new AtomicBoolean(true);
    private final ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(1);
    
    /**
     * A bundle of seed IDs organized by harness name and seed pool shared memory name.
     */
    public static class SubmitBundle {
        private final int scriptId;
        private final String harnessName;
        private final String shmName;
        private final List<Integer> seedIds;

        public SubmitBundle(int scriptId, String harnessName, String shmName, List<Integer> seedIds) {
            this.scriptId = scriptId;
            this.harnessName = harnessName != null ? harnessName : "";
            this.shmName = shmName != null ? shmName : "";
            this.seedIds = seedIds != null ? seedIds : new ArrayList<>();
        }

        /**
         * Serialize bundle to JSON string
         */
        public static String serialize(SubmitBundle bundle) {
            if (bundle == null) {
                throw new IllegalArgumentException("Bundle cannot be null");
            }
            
            try {
                ObjectNode root = mapper.createObjectNode();
                root.put("script_id", bundle.scriptId);
                root.put("harness_name", bundle.harnessName);
                root.put("shm_name", bundle.shmName);
                
                ArrayNode seedIdsNode = root.putArray("seed_ids");
                for (Integer seedId : bundle.seedIds) {
                    seedIdsNode.add(seedId);
                }
                
                return mapper.writeValueAsString(root);
            } catch (Exception e) {
                logger.log(Level.SEVERE, "Error serializing bundle", e);
                throw new RuntimeException("Failed to serialize bundle", e);
            }
        }

        /**
         * Deserialize JSON string to bundle
         */
        public static SubmitBundle deserialize(String jsonStr) {
            if (jsonStr == null || jsonStr.trim().isEmpty()) {
                throw new IllegalArgumentException("JSON string cannot be null or empty");
            }
            
            try {
                JsonNode root = mapper.readTree(jsonStr);
                
                int scriptId = root.get("script_id").asInt();
                String harnessName = root.get("harness_name").asText();
                String shmName = root.get("shm_name").asText();
                
                JsonNode seedIdsNode = root.get("seed_ids");
                List<Integer> seedIds = new ArrayList<>(seedIdsNode.size());
                for (JsonNode idNode : seedIdsNode) {
                    seedIds.add(idNode.asInt());
                }
                
                return new SubmitBundle(scriptId, harnessName, shmName, seedIds);
            } catch (Exception e) {
                logger.log(Level.SEVERE, "Error deserializing JSON: " + jsonStr, e);
                throw new RuntimeException("Failed to deserialize JSON", e);
            }
        }

        @Override
        public String toString() {
            return "SubmitBundle{" +
                    "scriptId=" + scriptId +
                    ", harnessName='" + harnessName + '\'' +
                    ", shmName='" + shmName + '\'' +
                    ", seedIds.size=" + seedIds.size() +
                    '}';
        }
    }

    /**
     * Initialize the Dealer socket
     */
    public SeedConsumer() {
        // Configure logging
        configureLogging();
        
        // Create ZeroMQ context and socket
        context = new ZContext();
        dealer = context.createSocket(SocketType.DEALER);
        
        // Generate a unique dealer ID
        dealerId = "SC-" + UUID.randomUUID().toString().substring(0, 4);
        dealer.setIdentity(dealerId.getBytes(ZMQ.CHARSET));
        logger.info("Dealer created with identity: " + dealerId);
        
        // Connect to router
        dealer.connect(ROUTER_ADDR);
        logger.info("Connected to router at " + ROUTER_ADDR);
    }

    /**
     * Configure the logging system
     */
    private void configureLogging() {
        // Reset the logging configuration
        LogManager.getLogManager().reset();
        
        // Create and configure console handler
        ConsoleHandler handler = new ConsoleHandler();
        handler.setFormatter(new SimpleFormatter());
        handler.setLevel(Level.INFO);
        
        // Configure logger
        logger.setLevel(Level.INFO);
        logger.addHandler(handler);
        logger.setUseParentHandlers(false);
    }

    /**
     * Start the heartbeat task
     */
    private void startHeartbeatTask() {
        logger.info("Starting heartbeat loop (interval: " + HB_INTERVAL_SECONDS + "s)");
        
        final AtomicInteger heartbeatCount = new AtomicInteger(0);
        
        scheduler.scheduleAtFixedRate(() -> {
            try {
                if (!running.get()) {
                    return;
                }
                
                int count = heartbeatCount.getAndIncrement();
                logger.info("Sending HEARTBEAT " + count);
                
                // Send heartbeat message as multi-part
                dealer.sendMore("HEARTBEAT");
                dealer.send(HARNESS);
                
                if (count > 0 && count % 10 == 0) {
                    logger.info("Sent " + count + " heartbeats so far");
                }
            } catch (Exception e) {
                logger.log(Level.SEVERE, "Error in heartbeat task", e);
            }
        }, 0, HB_INTERVAL_SECONDS, TimeUnit.SECONDS);
    }

    /**
     * Main method to run the dealer
     */
    public void run() {
        logger.info("Starting dealer main loop");
        startHeartbeatTask();
        
        final AtomicInteger seedCount = new AtomicInteger(0);
        int lastPrintedCount = 0;
        
        try {
            // Set up poller once, outside the loop
            ZMQ.Poller poller = context.createPoller(1);
            poller.register(dealer, ZMQ.Poller.POLLIN);
            
            while (running.get()) {
                // Wait for message with timeout (1 second)
                poller.poll(1000);
                
                if (poller.pollin(0)) {
                    // Receive multi-part message
                    String cmd = dealer.recvStr();
                    
                    if ("SEED".equals(cmd)) {
                        byte[] msgId = dealer.recv();
                        byte[] bundleBytes = dealer.recv();
                        
                        String msgIdStr = new String(msgId, ZMQ.CHARSET);
                        String bundleStr = new String(bundleBytes, ZMQ.CHARSET);
                        
                        logger.info("Received SEED BATCH msg: msg_id=" + msgIdStr);
                        logger.fine("Bundle content: " + bundleStr);
                        
                        try {
                            // Deserialize bundle
                            SubmitBundle bundle = SubmitBundle.deserialize(bundleStr);
                            int newCount = seedCount.addAndGet(bundle.seedIds.size());
                            
                            // Send ACK
                            logger.info("Sending ACK for seed " + msgIdStr);
                            dealer.sendMore("ACK");
                            dealer.sendMore(msgId);
                            dealer.send(bundleBytes);
                            logger.info("ACK sent for seed " + msgIdStr);
                            
                            if (newCount - lastPrintedCount >= 1000) {
                                logger.info("Processed " + newCount + " seeds so far");
                                lastPrintedCount = newCount;
                            }
                        } catch (Exception e) {
                            logger.log(Level.SEVERE, "Failed to process seed batch: " + e.getMessage(), e);
                        }
                    } else {
                        logger.warning("Received unknown command: " + cmd);
                    }
                }
            }
        } catch (Exception e) {
            logger.log(Level.SEVERE, "Error in dealer main loop", e);
        } finally {
            close();
        }
    }

    /**
     * Clean up resources
     */
    @Override
    public void close() {
        if (running.compareAndSet(true, false)) {
            logger.info("Cleaning up tasks and connections");
            scheduler.shutdownNow();
            
            try {
                if (!scheduler.awaitTermination(5, TimeUnit.SECONDS)) {
                    logger.warning("Scheduler did not terminate in time");
                }
            } catch (InterruptedException e) {
                logger.log(Level.WARNING, "Interrupted while waiting for scheduler to terminate", e);
                Thread.currentThread().interrupt();
            }
            
            if (dealer != null) {
                dealer.close();
            }
            
            if (context != null) {
                context.close();
            }
            
            logger.info("Dealer shutdown complete");
        }
    }

    /**
     * Main method to start the application
     */
    public static void main(String[] args) {
        logger.info("Starting ZeroMQ dealer example");
        
        try (SeedConsumer consumer = new SeedConsumer()) {
            // Register shutdown hook
            Runtime.getRuntime().addShutdownHook(new Thread(() -> {
                logger.info("Shutdown hook triggered, closing consumer");
                consumer.close();
            }));
            
            consumer.run();
        } catch (Exception e) {
            logger.log(Level.SEVERE, "Dealer failed with error", e);
        }
    }
}