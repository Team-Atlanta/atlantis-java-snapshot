/*
 * Copyright 2025 Code Intelligence GmbH
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.code_intelligence.jazzer.driver;

import com.code_intelligence.jazzer.instrumentor.CodeMarkerInstrumentor;
import com.code_intelligence.jazzer.runtime.CodeMarkerHitEvent;
import com.code_intelligence.jazzer.utils.Log;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Map;

// Json spec used in this implementation: https://www.json.org/json-en.html

class CodeMarkerUtils {

  private static int lastMarkedNodesNum = 0;

  static String getSystemEnv(String key) {
    try {
      return System.getenv(key);
    } catch (SecurityException e) {
      Log.error("Failed to get system environment variable: " + key);
      e.printStackTrace();
      return "";
    }
  }

  /**
   * Dump a new hit info as a json file
   *
   * @param saveDir The directory to save the hit information.
   * @param event The code marker hit event.
   * @param data Fuzzing input triggering that hit.
   */
  static void saveNewHit(
      File saveDir, CodeMarkerHitEvent event, Throwable ppEvent, long stackHash, byte[] data) {
    /*
     * Save as {prefix}-{coordSha256First16}-{stackHash}.json:
     * Where:
     * - prefix: "sink", "cpmeta", or "unknown" based on markDesc
     * - coordSha256First16: First 16 chars of coordinate's SHA-256 hash (unique per code location)
     * - stackHash: Hash of the stack trace (unique per execution path)
     *
     * File content:
     * {
     *   "mark_id": event.getMarkId(),
     *   "target_cp": cp_name,
     *   "target_harness": harness_class_name,
     *   "data_sha1": sha-1(data),
     *   "data": hexStringData,
     *   "coordinate": {
     *     "class_name": ...,
     *     "method_name": ...,
     *     "method_desc": ...,
     *     "bytecode_offset": ...,
     *     "mark_desc": ..., // Should never be null, now is "sink-VULN-DESC"
     *     "file_name": ..., // Optional, can be null
     *     "line_num": ..., // Optional, can be null
     *     "sha256": ... // SHA-256 hash of coordinates (machine-independent)
     *   },
     *   "stack_hash": hashString,
     *   "stack_trace": [
     *     {
     *       "class_name": ...,
     *       "method_name": ...,
     *       "file_name": ...,
     *       "line_num": ...,
     *       "frame_str": ...
     *     },
     *     ...
     *   ]
     * }
     */

    // Get coordinate info for this markId
    Map<String, Object> coordinateInfo =
        CodeMarkerInstrumentor.getCoordinateInfoForMarkId(event.getMarkId());

    // Determine the file prefix based on markDesc
    String markDesc = (String) coordinateInfo.get("mark_desc");
    String prefix = "unknown";

    if (markDesc != null) {
      if (markDesc.startsWith("sink-")) {
        prefix = "sink";
      } else if (markDesc.startsWith("cpmeta-")) {
        prefix = "cpmeta";
      }
    }

    // Get the coordinate sha256 hash and use first 16 chars
    String coordSha256 = (String) coordinateInfo.get("sha256");
    String coordSha256Short = coordSha256.substring(0, 16);
    String stackHashStr = Long.toUnsignedString(stackHash);

    Log.info(
        "BEEP COORDINATE HIT @ "
            + coordinateInfo.get("class_name")
            + ","
            + coordinateInfo.get("method_name")
            + ","
            + coordinateInfo.get("method_desc")
            + ","
            + coordinateInfo.get("bytecode_offset")
            + ","
            + coordinateInfo.get("file_name")
            + ","
            + coordinateInfo.get("line_num")
            + ","
            + coordSha256);

    if (saveDir == null) {
      Log.info("BEEP: new hit on code marker id " + event.getMarkId() + ", no hit info saved");
      return;
    }

    // Use format: sink-{coordSha256First16}-{stackHash}.json
    String filename = String.format("%s-%s-%s.json", prefix, coordSha256Short, stackHashStr);
    File file = new File(saveDir, filename);

    Log.info(
        "BEEP: new hit on code marker id "
            + event.getMarkId()
            + ", hit info saved to "
            + file.getAbsolutePath());

    // Calculate SHA-1 of input data (needed for JSON content)
    String dataSha1;
    try {
      dataSha1 = sha1Hex(data);
    } catch (NoSuchAlgorithmException e) {
      throw new RuntimeException("SHA-1 algorithm not available", e);
    }

    // Hit info json content
    String hexStringData = bytesToHex(data);

    String jsonContent =
        "{\n"
            + "  \"mark_id\": "
            + event.getMarkId()
            + ",\n"
            + "  \"target_cp\": "
            + "\""
            + escapeJsonString(getSystemEnv("FUZZ_TARGET_CP"))
            + "\""
            + ",\n"
            + "  \"target_harness\": "
            + "\""
            + escapeJsonString(getSystemEnv("FUZZ_TARGET_HARNESS"))
            + "\""
            + ",\n"
            + "  \"data_sha1\": "
            + "\""
            + dataSha1
            + "\""
            + ",\n"
            + "  \"data\": \""
            + escapeJsonString(hexStringData)
            + "\",\n"
            + "  \"coordinate\": "
            + buildJsonFromMap(coordinateInfo, 2)
            + ",\n"
            + "  \"stack_hash\": "
            + "\""
            + Long.toUnsignedString(stackHash)
            + "\""
            + ",\n"
            + "  \"stack_trace\": "
            + buildStackTraceJson(ppEvent.getStackTrace())
            + "\n"
            + "}\n";

    writeFileAtomically(file, jsonContent);
  }

  /**
   * Dumps code marker info if updated and undumped.
   *
   * @param saveDir The directory to save 'xcode.json'.
   */
  public static void dumpCodeMarkersIfUpdated(File saveDir) {
    if (saveDir == null) {
      Log.info("Skip dumping code marker info.");
      return;
    }

    int currentMarkedNodesNum = CodeMarkerInstrumentor.getMarkedNodesNum();
    if (currentMarkedNodesNum == lastMarkedNodesNum) {
      return;
    }

    Map<Integer, Map<String, Object>> markedNodesInfo =
        CodeMarkerInstrumentor.dumpMarkedNodesInfo();
    File file = new File(saveDir, "xcode.json");

    // Build json content
    StringBuilder jsonContent = new StringBuilder();
    jsonContent.append("{\n");

    int entryCount = 0;
    int totalEntries = markedNodesInfo.size();
    for (Map.Entry<Integer, Map<String, Object>> entry : markedNodesInfo.entrySet()) {
      Integer markId = entry.getKey();
      Map<String, Object> info = entry.getValue();

      jsonContent.append("  \"").append(markId).append("\": ");
      jsonContent.append(buildJsonFromMap(info, 2));

      entryCount++;
      if (entryCount < totalEntries) {
        jsonContent.append(",");
      }
      jsonContent.append("\n");
    }

    jsonContent.append("}\n");

    writeFileAtomically(file, jsonContent.toString());
    lastMarkedNodesNum = currentMarkedNodesNum; // Update the previous count
    Log.info("Dumped marked nodes info to file: " + file.getAbsolutePath());
  }

  /**
   * Builds a JSON string from a Map<String, Object>.
   *
   * @param map The map containing JSON fields.
   * @param indentLevel The current indentation level for formatting.
   * @return A formatted JSON string representation of the map.
   */
  private static String buildJsonFromMap(Map<String, Object> map, int indentLevel) {
    String indent = "  ".repeat(indentLevel);
    StringBuilder jsonBuilder = new StringBuilder();
    jsonBuilder.append("{\n");

    int fieldCount = 0;
    int totalFields = map.size();
    for (Map.Entry<String, Object> fieldEntry : map.entrySet()) {
      String key = fieldEntry.getKey();
      Object value = fieldEntry.getValue();

      jsonBuilder.append(indent).append("\"").append(escapeJsonString(key)).append("\": ");

      if (value instanceof Map) {
        // Recursively build JSON for nested maps
        jsonBuilder.append(buildJsonFromMap((Map<String, Object>) value, indentLevel + 1));
      } else if (value instanceof Iterable) {
        // Handle iterable types (e.g., lists)
        jsonBuilder.append(buildJsonFromIterable((Iterable<?>) value, indentLevel + 1));
      } else if (value instanceof String) {
        jsonBuilder.append("\"").append(escapeJsonString((String) value)).append("\"");
      } else if (value instanceof Number || value instanceof Boolean) {
        jsonBuilder.append(value.toString());
      } else if (value == null) {
        jsonBuilder.append("null");
      } else {
        // For other object types, use toString() representation
        jsonBuilder.append("\"").append(escapeJsonString(value.toString())).append("\"");
      }

      fieldCount++;
      if (fieldCount < totalFields) {
        jsonBuilder.append(",");
      }
      jsonBuilder.append("\n");
    }

    jsonBuilder.append(indent.substring(2)).append("}");
    return jsonBuilder.toString();
  }

  /**
   * Builds a JSON array string from an Iterable<?>.
   *
   * @param iterable The iterable containing elements.
   * @param indentLevel The current indentation level for formatting.
   * @return A formatted JSON array string.
   */
  private static String buildJsonFromIterable(Iterable<?> iterable, int indentLevel) {
    String indent = "  ".repeat(indentLevel);
    StringBuilder jsonBuilder = new StringBuilder();
    jsonBuilder.append("[\n");

    int itemCount = 0;
    for (Object item : iterable) {
      jsonBuilder.append(indent);

      if (item instanceof Map) {
        jsonBuilder.append(buildJsonFromMap((Map<String, Object>) item, indentLevel + 1));
      } else if (item instanceof Iterable) {
        jsonBuilder.append(buildJsonFromIterable((Iterable<?>) item, indentLevel + 1));
      } else if (item instanceof String) {
        jsonBuilder.append("\"").append(escapeJsonString((String) item)).append("\"");
      } else if (item instanceof Number || item instanceof Boolean) {
        jsonBuilder.append(item.toString());
      } else if (item == null) {
        jsonBuilder.append("null");
      } else {
        jsonBuilder.append("\"").append(escapeJsonString(item.toString())).append("\"");
      }

      itemCount++;
      jsonBuilder.append(",");
      jsonBuilder.append("\n");
    }

    if (itemCount > 0) {
      // Remove the trailing comma and newline
      int lastIndex = jsonBuilder.lastIndexOf(",");
      jsonBuilder.delete(lastIndex, lastIndex + 1);
    }

    jsonBuilder.append(indent.substring(2)).append("]");
    return jsonBuilder.toString();
  }

  /**
   * Builds a JSON array string representing the stack trace.
   *
   * @param stackTraceElements The array of StackTraceElement objects from the event.
   * @return A formatted JSON array string of stack trace elements.
   */
  private static String buildStackTraceJson(StackTraceElement[] stackTraceElements) {
    StringBuilder stackTraceJson = new StringBuilder();
    stackTraceJson.append("[\n");
    for (int i = 0; i < stackTraceElements.length; i++) {
      StackTraceElement element = stackTraceElements[i];
      String className = escapeJsonString(element.getClassName());
      String methodName = escapeJsonString(element.getMethodName());
      String fileName = escapeJsonString(element.getFileName());
      int lineNumber = element.getLineNumber();
      String frameString = escapeJsonString(element.toString());

      stackTraceJson.append("    {\n");
      stackTraceJson.append("      \"class_name\": \"").append(className).append("\",\n");
      stackTraceJson.append("      \"method_name\": \"").append(methodName).append("\",\n");
      stackTraceJson.append("      \"file_name\": \"").append(fileName).append("\",\n");
      stackTraceJson.append("      \"line_num\": ").append(lineNumber).append(",\n");
      stackTraceJson.append("      \"frame_str\": \"").append(frameString).append("\"\n");
      stackTraceJson.append("    }");

      if (i < stackTraceElements.length - 1) {
        stackTraceJson.append(",");
      }
      stackTraceJson.append("\n");
    }
    stackTraceJson.append("  ]");
    return stackTraceJson.toString();
  }

  /**
   * Converts a byte array to a hexadecimal string.
   *
   * @param bytes The byte array to convert.
   * @return A hexadecimal string representation of the byte array.
   */
  private static String bytesToHex(byte[] bytes) {
    StringBuilder sb = new StringBuilder(bytes.length * 2);
    for (byte b : bytes) {
      // Append a formatted string for each byte
      sb.append(String.format("%02x", b));
    }
    return sb.toString();
  }

  /**
   * Calculates the SHA-1 hash of the given data and returns it as a hexadecimal string.
   *
   * @param data The data to hash.
   * @return The SHA-1 hash as a hexadecimal string.
   * @throws NoSuchAlgorithmException If the SHA-1 algorithm is not available.
   */
  private static String sha1Hex(byte[] data) throws NoSuchAlgorithmException {
    MessageDigest digest = MessageDigest.getInstance("SHA-1");
    return bytesToHex(digest.digest(data));
  }

  /**
   * Writes content to a file atomically by first writing to a temporary file and then moving it to
   * the target location.
   *
   * @param file The target file to write to.
   * @param content The content to write to the file.
   */
  private static void writeFileAtomically(File file, String content) {
    Path targetPath = file.toPath();
    Path tempPath = targetPath.resolveSibling(".hidden." + file.getName());

    try {
      // Write content to temporary file
      try (FileWriter fileWriter = new FileWriter(tempPath.toFile())) {
        fileWriter.write(content);
      }

      // Atomically move the temporary file to the target location
      Files.move(
          tempPath,
          targetPath,
          StandardCopyOption.ATOMIC_MOVE,
          StandardCopyOption.REPLACE_EXISTING);
    } catch (IOException e) {
      Log.error("Failed to write file atomically: " + file.getAbsolutePath());
      e.printStackTrace();

      // Clean up the temporary file if it exists
      try {
        Files.deleteIfExists(tempPath);
      } catch (IOException cleanupException) {
        // Ignore cleanup errors
      }
    }
  }

  /**
   * Escapes special characters in a string to make it safe for inclusion in JSON.
   *
   * @param s The input string to escape.
   * @return The escaped string.
   */
  private static String escapeJsonString(String s) {
    if (s == null) {
      return "";
    }
    StringBuilder sb = new StringBuilder(s.length());
    for (int i = 0; i < s.length(); i++) {
      char c = s.charAt(i);
      switch (c) {
        case '"':
          sb.append("\\\"");
          break;
        case '\\':
          sb.append("\\\\");
          break;
        case '/':
          sb.append("\\/");
          break;
        case '\b':
          sb.append("\\b");
          break;
        case '\f':
          sb.append("\\f");
          break;
        case '\n':
          sb.append("\\n");
          break;
        case '\r':
          sb.append("\\r");
          break;
        case '\t':
          sb.append("\\t");
          break;
        default:
          if (c < 32 || c > 126) {
            // Non-printable ASCII characters
            sb.append(String.format("\\u%04x", (int) c));
          } else {
            sb.append(c);
          }
      }
    }
    return sb.toString();
  }
}
