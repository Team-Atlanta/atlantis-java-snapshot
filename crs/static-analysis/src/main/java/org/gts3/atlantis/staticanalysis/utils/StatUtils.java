package org.gts3.atlantis.staticanalysis.utils;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;

/**
 * Utility class for retrieving system statistics and resource usage information.
 */
public class StatUtils {

    /**
     * Gets the maximum resident set size (VmHWM) for the current process in kilobytes.
     * This represents the peak physical memory usage of the process.
     *
     * @return The maximum RSS in kilobytes, or -1 if unable to retrieve the value
     */
    public static long getMaxRssKB() {
        return getMaxRssKB(getCurrentPid());
    }

    /**
     * Gets the maximum resident set size (VmHWM) for a specific process ID in kilobytes.
     * This represents the peak physical memory usage of the process.
     *
     * @param pid The process ID to query
     * @return The maximum RSS in kilobytes, or -1 if unable to retrieve the value
     */
    public static long getMaxRssKB(long pid) {
        try {
            ProcessBuilder pb = new ProcessBuilder("grep", "VmHWM", "/proc/" + pid + "/status");
            Process process = pb.start();

            try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()))) {
                String line = reader.readLine();
                if (line != null && line.startsWith("VmHWM:")) {
                    // Parse the line format: "VmHWM:    12345 kB"
                    String[] parts = line.trim().split("\\s+");
                    if (parts.length >= 2) {
                        return Long.parseLong(parts[1]);
                    }
                }
            }

            int exitCode = process.waitFor();
            if (exitCode != 0) {
                System.err.println("Failed to read VmHWM for PID " + pid + ", exit code: " + exitCode);
            }
        } catch (IOException | InterruptedException | NumberFormatException e) {
            System.err.println("Error retrieving max RSS for PID " + pid + ": " + e.getMessage());
        }

        return -1;
    }

    /**
     * Gets the current process ID.
     *
     * @return The current process ID
     */
    private static long getCurrentPid() {
        return ProcessHandle.current().pid();
    }

    /**
     * Formats memory size in kilobytes to a human-readable string.
     *
     * @param sizeKB Size in kilobytes
     * @return Formatted string (e.g., "1.5 MB", "512 KB")
     */
    public static String formatMemorySize(long sizeKB) {
        if (sizeKB < 0) {
            return "unknown";
        }

        if (sizeKB < 1024) {
            return sizeKB + " KB";
        } else if (sizeKB < 1024 * 1024) {
            return String.format("%.1f MB", sizeKB / 1024.0);
        } else {
            return String.format("%.1f GB", sizeKB / (1024.0 * 1024.0));
        }
    }
}
