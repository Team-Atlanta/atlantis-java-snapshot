package org.gts3.atlantis.staticanalysis;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

import org.gts3.atlantis.staticanalysis.utils.FileUtils;

import static org.gts3.atlantis.staticanalysis.utils.LogLabel.LOG_ERROR;
import static org.gts3.atlantis.staticanalysis.utils.LogLabel.LOG_WARN;

/**
 * Utility class for caching analysis results.
 *
 * This class provides methods to cache distance map results and restore them
 * to make output available early while the analysis continues to run.
 * The cache stores two files: the cached result and its hash for integrity verification.
 */
public class ResultCache {
    private static final String CACHE_RESULT_FILE = "result.json";
    private static final String CACHE_HASH_FILE = "result.sha256";

    /**
     * Attempts to restore a cached result to the output file if a valid cache exists.
     * This makes the output available early while analysis continues.
     *
     * @param cacheDir The cache directory to check for cached results
     * @param outputFile The output file where the cached result should be copied
     * @return true if cache was successfully restored, false otherwise
     */
    public static boolean tryRestoreFromCache(Path cacheDir, Path outputFile) {
        if (cacheDir == null || outputFile == null) {
            return false;
        }

        try {
            Path cachedResultFile = cacheDir.resolve(CACHE_RESULT_FILE);
            Path cachedHashFile = cacheDir.resolve(CACHE_HASH_FILE);

            // Check if both cache files exist
            if (!Files.exists(cachedResultFile) || !Files.exists(cachedHashFile)) {
                System.out.println("Cache miss: cached files not found");
                return false;
            }

            // Load both files once
            byte[] cachedContent;
            String storedHash;
            try {
                cachedContent = Files.readAllBytes(cachedResultFile);
                storedHash = Files.readString(cachedHashFile).trim();
            } catch (IOException e) {
                System.out.println(LOG_WARN + "Error reading cache files: " + e.getMessage());
                return false;
            }

            // Verify cache integrity by computing hash of loaded content
            String computedHash = computeHash(cachedContent);
            if (computedHash == null || !computedHash.equals(storedHash)) {
                System.out.println(LOG_WARN + "Cache integrity check failed, ignoring cached result");
                return false;
            }

            // Copy cached content to output file atomically
            FileUtils.writeFileAtomically(outputFile, tempPath -> {
                try {
                    Files.write(tempPath, cachedContent);
                } catch (IOException e) {
                    throw new RuntimeException("Error writing cached result", e);
                }
            });

            System.out.println("Successfully restored cached result to " + outputFile);
            return true;

        } catch (Exception e) {
            System.out.println(LOG_WARN + "Error restoring from cache: " + e.getMessage());
            return false;
        }
    }

    /**
     * Saves the given content to the cache.
     * Computes the hash of the content and saves both the content and hash atomically.
     *
     * @param cacheDir The cache directory where results should be saved
     * @param content The content to cache (already serialized JSON)
     */
    public static void saveToCache(Path cacheDir, String content) {
        if (cacheDir == null || content == null) {
            return;
        }

        try {
            // Ensure cache directory exists
            if (!Files.exists(cacheDir)) {
                Files.createDirectories(cacheDir);
            }

            // Convert content to bytes and compute hash
            byte[] contentBytes = content.getBytes();
            String fileHash = computeHash(contentBytes);
            if (fileHash == null) {
                System.out.println(LOG_WARN + "Failed to compute hash for caching");
                return;
            }

            Path cachedResultFile = cacheDir.resolve(CACHE_RESULT_FILE);
            Path cachedHashFile = cacheDir.resolve(CACHE_HASH_FILE);

            // Atomically save the result file
            FileUtils.writeFileAtomically(cachedResultFile, tempPath -> {
                try {
                    Files.write(tempPath, contentBytes);
                } catch (IOException e) {
                    throw new RuntimeException("Error writing result to cache", e);
                }
            });

            // Atomically save the hash file
            FileUtils.writeFileAtomically(cachedHashFile, tempPath -> {
                try {
                    Files.writeString(tempPath, fileHash);
                } catch (IOException e) {
                    throw new RuntimeException("Error writing hash to cache", e);
                }
            });

            System.out.println("Successfully cached result to " + cacheDir);

        } catch (Exception e) {
            System.out.println(LOG_WARN + "Error saving to cache: " + e.getMessage());
        }
    }

    /**
     * Computes the SHA-256 hash of the given byte array.
     *
     * @param content The content to compute the hash for
     * @return The hexadecimal representation of the SHA-256 hash, or null if an error occurred
     */
    private static String computeHash(byte[] content) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hashBytes = digest.digest(content);

            // Convert to hexadecimal string
            StringBuilder hexString = new StringBuilder();
            for (byte b : hashBytes) {
                String hex = Integer.toHexString(0xff & b);
                if (hex.length() == 1) {
                    hexString.append('0');
                }
                hexString.append(hex);
            }
            return hexString.toString();

        } catch (NoSuchAlgorithmException e) {
            System.out.println(LOG_ERROR + "Error computing hash: " + e.getMessage());
            return null;
        }
    }
}
