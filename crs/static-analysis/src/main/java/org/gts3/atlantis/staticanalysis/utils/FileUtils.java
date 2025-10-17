package org.gts3.atlantis.staticanalysis.utils;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.function.Consumer;

import static org.gts3.atlantis.staticanalysis.utils.LogLabel.LOG_ERROR;

/**
 * Utility class for file operations.
 *
 * This class provides methods for safe and atomic file operations,
 * including atomic file writing to prevent data corruption.
 */
public class FileUtils {

    /**
     * Writes content to a file atomically using a temporary file approach.
     * This method creates a temporary file, writes the content to it, and then
     * atomically moves it to the target location to prevent partial writes and data corruption.
     *
     * @param targetPath The path where the file should be created
     * @param contentWriter A consumer that writes the content to the provided path
     * @throws IOException If an I/O error occurs during the operation
     */
    public static void writeFileAtomically(Path targetPath, Consumer<Path> contentWriter) throws IOException {
        // Ensure parent directory exists
        ensureParentDirectoryExists(targetPath);

        // Create a temporary file in the same directory as the target file
        Path tempFile = null;
        try {
            tempFile = Files.createTempFile(targetPath.getParent(), ".hidden." + targetPath.getFileName().toString(), "");

            // Write content to the temporary file
            contentWriter.accept(tempFile);

            // Atomically move the temporary file to the target location
            Files.move(tempFile, targetPath, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
            tempFile = null; // Mark as successfully moved

        } catch (IOException e) {
            // Clean up temporary file if it still exists
            if (tempFile != null) {
                try {
                    Files.deleteIfExists(tempFile);
                } catch (IOException cleanupException) {
                    System.err.println(LOG_ERROR + "Error cleaning up temporary file: " + cleanupException.getMessage());
                }
            }
            throw e; // Re-throw the original exception
        }
    }

    /**
     * Ensures the parent directory of a file exists, creating it if necessary.
     *
     * @param path The file whose parent directory should exist
     * @throws RuntimeException If the parent directory cannot be created due to security restrictions
     */
    private static void ensureParentDirectoryExists(Path path) {
        Path parent = path.getParent();
        if (parent != null && !Files.exists(parent)) {
            try {
                Files.createDirectories(parent);
            } catch (IOException e) {
                System.err.println(LOG_ERROR + "Error creating parent directory: " + e.getMessage());
                throw new RuntimeException("Failed to create parent directory", e);
            }
        }
    }
}
