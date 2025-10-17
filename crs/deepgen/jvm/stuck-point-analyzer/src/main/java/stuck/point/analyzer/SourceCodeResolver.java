package stuck.point.analyzer;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Resolves source code files using CP metadata pkg2files mapping.
 * Maps class FQN and filename to actual source file paths and reads source code content.
 */
public class SourceCodeResolver {
    
    private final Map<String, List<String>> pkg2files;
    private final boolean verbose;
    
    public SourceCodeResolver(String metadataFile, boolean verbose) throws IOException {
        this.verbose = verbose;
        this.pkg2files = loadPkg2Files(metadataFile);
        
        if (verbose) {
            System.out.printf("Loaded metadata with %d packages%n", pkg2files.size());
        }
    }
    
    /**
     * Load pkg2files mapping from CP metadata JSON file.
     */
    private Map<String, List<String>> loadPkg2Files(String metadataFile) throws IOException {
        ObjectMapper mapper = new ObjectMapper();
        JsonNode root = mapper.readTree(new File(metadataFile));
        
        JsonNode pkg2filesNode = root.get("pkg2files");
        if (pkg2filesNode == null || !pkg2filesNode.isObject()) {
            throw new IOException("Invalid metadata file: missing or invalid 'pkg2files' field");
        }
        
        Map<String, List<String>> result = new HashMap<>();
        pkg2filesNode.fields().forEachRemaining(entry -> {
            String packageName = entry.getKey();
            JsonNode filesArray = entry.getValue();
            
            if (filesArray.isArray()) {
                List<String> files = new java.util.ArrayList<>();
                filesArray.forEach(fileNode -> {
                    if (fileNode.isTextual()) {
                        files.add(fileNode.asText());
                    }
                });
                result.put(packageName, files);
            }
        });
        
        return result;
    }
    
    /**
     * Find source file path for a given class FQN and filename.
     * Uses pkg2files mapping to locate the exact source file.
     */
    public String findSourceFile(String classFqn, String fileName) {
        String packageName = extractPackage(classFqn);
        
        List<String> files = pkg2files.get(packageName);
        if (files == null) {
            if (verbose) {
                System.out.printf("No files found for package: %s%n", packageName);
            }
            return null;
        }
        
        // Find file ending with the exact fileName
        String sourceFile = files.stream()
                .filter(f -> f.endsWith("/" + fileName))
                .findFirst()
                .orElse(null);
                
        if (verbose && sourceFile != null) {
            System.out.printf("Resolved %s -> %s%n", classFqn, sourceFile);
        }
        
        return sourceFile;
    }
    
    /**
     * Read source code line from file.
     * Returns the actual source code content for the specified line number.
     */
    public String readSourceLine(String sourceFilePath, int lineNumber) {
        if (sourceFilePath == null) {
            return null;
        }
        
        try {
            List<String> lines = Files.readAllLines(Paths.get(sourceFilePath));
            
            // Line numbers are 1-based
            if (lineNumber > 0 && lineNumber <= lines.size()) {
                return lines.get(lineNumber - 1).trim();
            }
            
        } catch (IOException e) {
            if (verbose) {
                System.out.printf("Failed to read source file %s: %s%n", sourceFilePath, e.getMessage());
            }
        }
        
        return null;
    }
    
    /**
     * Get source code context around a specific line.
     * Returns multiple lines of context for better understanding.
     */
    public Map<Integer, String> readSourceContext(String sourceFilePath, int targetLine, int contextLines) {
        Map<Integer, String> context = new HashMap<>();
        
        if (sourceFilePath == null) {
            return context;
        }
        
        try {
            List<String> lines = Files.readAllLines(Paths.get(sourceFilePath));
            
            int startLine = Math.max(1, targetLine - contextLines);
            int endLine = Math.min(lines.size(), targetLine + contextLines);
            
            for (int lineNum = startLine; lineNum <= endLine; lineNum++) {
                if (lineNum > 0 && lineNum <= lines.size()) {
                    context.put(lineNum, lines.get(lineNum - 1));
                }
            }
            
        } catch (IOException e) {
            if (verbose) {
                System.out.printf("Failed to read source context from %s: %s%n", sourceFilePath, e.getMessage());
            }
        }
        
        return context;
    }
    
    /**
     * Extract package name from fully qualified class name.
     * Examples:
     * - "com.aixcc.mock_java.App" -> "com.aixcc.mock_java"
     * - "OssFuzz1" -> ""
     */
    private String extractPackage(String classFqn) {
        int lastDot = classFqn.lastIndexOf('.');
        if (lastDot >= 0) {
            return classFqn.substring(0, lastDot);
        }
        return ""; // Default package
    }
    
    /**
     * Check if source resolution is available.
     */
    public boolean isAvailable() {
        return pkg2files != null && !pkg2files.isEmpty();
    }
}