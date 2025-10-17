package stuck.point.analyzer;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.File;
import java.io.IOException;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.*;
import java.util.stream.Collectors;

/**
 * Copies source directory and annotates files with coverage information.
 * Creates a complete copy of the source tree with coverage annotations prepended to each line.
 */
public class SourceAnnotator {
    
    private final Map<String, List<String>> pkg2files;
    private final Map<String, Map<Integer, CoverageLineInfo>> coverageMap;
    private final boolean verbose;
    
    public SourceAnnotator(String metadataFile, List<CoverageLineInfo> coverageData, boolean verbose) throws IOException {
        this.verbose = verbose;
        this.pkg2files = loadPkg2Files(metadataFile);
        this.coverageMap = buildCoverageMap(coverageData);
        
        if (verbose) {
            System.out.printf("SourceAnnotator: Loaded %d packages from metadata%n", pkg2files.size());
            System.out.printf("SourceAnnotator: Coverage data for %d classes%n", coverageMap.size());
        }
    }
    
    /**
     * Copy entire source directory and annotate files with coverage information.
     */
    public void annotateSourceDirectory(String sourceDir, String outputDir) throws IOException {
        Path sourcePath = Paths.get(sourceDir);
        Path outputPath = Paths.get(outputDir);
        
        if (!Files.exists(sourcePath)) {
            throw new IOException("Source directory does not exist: " + sourceDir);
        }
        
        // Step 1: Copy entire directory tree
        System.out.println("Copying source directory...");
        copyDirectory(sourcePath, outputPath);
        
        // Step 2: Collect all files from pkg2files
        Set<String> filesToAnnotate = new HashSet<>();
        for (List<String> files : pkg2files.values()) {
            filesToAnnotate.addAll(files);
        }
        
        System.out.printf("Annotating %d source files with coverage information...%n", filesToAnnotate.size());
        
        // Step 3: Annotate each file in the copied directory
        int annotatedCount = 0;
        for (String originalFilePath : filesToAnnotate) {
            // Convert absolute path to relative path from source directory
            Path originalPath = Paths.get(originalFilePath);
            Path relativePath;
            
            // Try to make the path relative to the source directory
            if (originalPath.isAbsolute() && originalPath.startsWith(sourcePath)) {
                relativePath = sourcePath.relativize(originalPath);
            } else if (originalPath.isAbsolute()) {
                // If the file path doesn't start with sourceDir, try to find the relative part
                // This handles cases where pkg2files has paths like /src/repo/... but sourceDir is /src
                String pathStr = originalPath.toString();
                String sourceDirStr = sourcePath.toString();
                
                // Find if the source dir is contained in the path
                if (pathStr.contains(sourceDirStr)) {
                    int idx = pathStr.indexOf(sourceDirStr);
                    String relativeStr = pathStr.substring(idx + sourceDirStr.length());
                    if (relativeStr.startsWith("/") || relativeStr.startsWith(File.separator)) {
                        relativeStr = relativeStr.substring(1);
                    }
                    relativePath = Paths.get(relativeStr);
                } else {
                    // Try to find common suffix
                    Path temp = originalPath;
                    while (temp.getParent() != null && !sourcePath.endsWith(temp)) {
                        temp = temp.getParent();
                    }
                    if (sourcePath.endsWith(temp)) {
                        relativePath = temp.relativize(originalPath);
                    } else {
                        // Last resort: use filename components after source directory name
                        String sourceName = sourcePath.getFileName().toString();
                        int idx = pathStr.lastIndexOf(sourceName);
                        if (idx >= 0) {
                            String afterSource = pathStr.substring(idx + sourceName.length());
                            if (afterSource.startsWith("/") || afterSource.startsWith(File.separator)) {
                                afterSource = afterSource.substring(1);
                            }
                            relativePath = Paths.get(afterSource);
                        } else {
                            if (verbose) {
                                System.out.printf("Warning: Could not determine relative path for %s%n", originalFilePath);
                            }
                            continue;
                        }
                    }
                }
            } else {
                relativePath = originalPath;
            }
            
            Path targetPath = outputPath.resolve(relativePath);
            
            if (Files.exists(targetPath)) {
                annotateFile(originalFilePath, targetPath);
                annotatedCount++;
                
                if (verbose && annotatedCount % 100 == 0) {
                    System.out.printf("Annotated %d files...%n", annotatedCount);
                }
            } else if (verbose) {
                System.out.printf("Warning: Target file does not exist after copy: %s%n", targetPath);
            }
        }
        
        System.out.printf("Successfully annotated %d source files%n", annotatedCount);
        System.out.printf("Annotated source code written to: %s%n", outputDir);
    }
    
    /**
     * Copy entire directory tree from source to destination.
     */
    private void copyDirectory(Path source, Path destination) throws IOException {
        Files.walkFileTree(source, new SimpleFileVisitor<Path>() {
            @Override
            public FileVisitResult preVisitDirectory(Path dir, BasicFileAttributes attrs) throws IOException {
                Path targetDir = destination.resolve(source.relativize(dir));
                Files.createDirectories(targetDir);
                return FileVisitResult.CONTINUE;
            }
            
            @Override
            public FileVisitResult visitFile(Path file, BasicFileAttributes attrs) throws IOException {
                Path targetFile = destination.resolve(source.relativize(file));
                Files.copy(file, targetFile, StandardCopyOption.REPLACE_EXISTING);
                return FileVisitResult.CONTINUE;
            }
        });
    }
    
    /**
     * Annotate a single file with coverage information.
     */
    private void annotateFile(String originalFilePath, Path targetPath) throws IOException {
        // Find the class FQN that corresponds to this file
        String classFqn = findClassFqnForFile(originalFilePath);
        
        if (classFqn == null && verbose) {
            System.out.printf("Warning: Could not determine class FQN for file: %s%n", originalFilePath);
        }
        
        Map<Integer, CoverageLineInfo> fileCoverage = (classFqn != null) ? coverageMap.get(classFqn) : null;
        
        // Read the file
        List<String> lines = Files.readAllLines(targetPath);
        List<String> annotatedLines = new ArrayList<>();
        
        // Annotate each line
        for (int i = 0; i < lines.size(); i++) {
            int lineNumber = i + 1; // Line numbers are 1-based
            String line = lines.get(i);
            
            String annotation;
            if (fileCoverage != null && fileCoverage.containsKey(lineNumber)) {
                CoverageLineInfo lineInfo = fileCoverage.get(lineNumber);
                if (lineInfo.isFullyCovered()) {
                    annotation = "[✓] ";
                } else if (lineInfo.isPartlyCovered()) {
                    annotation = "[~] ";
                } else {
                    annotation = "[✗] ";
                }
            } else {
                annotation = "[ ] ";  // No coverage data or no executable code
            }
            
            annotatedLines.add(annotation + line);
        }
        
        // Write annotated content back to file
        Files.write(targetPath, annotatedLines);
    }
    
    /**
     * Find the class FQN that corresponds to a source file path.
     * This reverses the pkg2files mapping.
     */
    private String findClassFqnForFile(String filePath) {
        // Extract just the filename
        Path path = Paths.get(filePath);
        String fileName = path.getFileName().toString();
        
        // Remove .java extension to get class name
        if (!fileName.endsWith(".java")) {
            return null;
        }
        String className = fileName.substring(0, fileName.length() - 5);
        
        // Find the package that contains this file
        for (Map.Entry<String, List<String>> entry : pkg2files.entrySet()) {
            String packageName = entry.getKey();
            List<String> files = entry.getValue();
            
            for (String file : files) {
                if (file.equals(filePath) || file.endsWith("/" + fileName)) {
                    // Construct FQN
                    if (packageName.isEmpty()) {
                        return className;  // Default package
                    } else {
                        return packageName + "." + className;
                    }
                }
            }
        }
        
        return null;
    }
    
    /**
     * Load pkg2files mapping from metadata JSON.
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
                List<String> files = new ArrayList<>();
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
     * Build a map from class FQN to line coverage information.
     */
    private Map<String, Map<Integer, CoverageLineInfo>> buildCoverageMap(List<CoverageLineInfo> coverageData) {
        Map<String, Map<Integer, CoverageLineInfo>> map = new HashMap<>();
        
        for (CoverageLineInfo lineInfo : coverageData) {
            map.computeIfAbsent(lineInfo.getClassFqn(), k -> new HashMap<>())
               .put(lineInfo.getLineNumber(), lineInfo);
        }
        
        return map;
    }
}