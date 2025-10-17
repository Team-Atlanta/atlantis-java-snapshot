package stuck.point.analyzer;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Core logic for the Stuck Point Analyzer.
 * Orchestrates JaCoCo coverage analysis and SootUp static analysis.
 */
public class StuckPointAnalyzerCore {
    
    private final boolean verbose;
    private final JacocoCoverageAnalyzer coverageAnalyzer;
    private final SootUpICFGAnalyzer icfgAnalyzer;
    
    public StuckPointAnalyzerCore(boolean verbose) {
        this.verbose = verbose;
        this.coverageAnalyzer = new JacocoCoverageAnalyzer(verbose);
        this.icfgAnalyzer = new SootUpICFGAnalyzer(verbose);
    }
    
    /**
     * Main analysis method that orchestrates the entire process.
     */
    public void analyze(String execFile, String[] jarFiles, String entryPoint, String outputFile, 
                       String metadataFile, String sourceDir, String annotatedOutputDir) 
            throws Exception {
        
        System.out.println("=== Fuzzer Stuck Point Analysis ===");
        System.out.printf("Execution file: %s%n", execFile);
        System.out.printf("Entry point: %s%n", entryPoint);
        System.out.printf("Output file: %s%n", outputFile);
        System.out.printf("JAR files: %s%n", String.join(", ", jarFiles));
        System.out.println();
        
        // Step 1: Analyze JaCoCo coverage data
        if (verbose) {
            System.out.println("Step 1: Analyzing JaCoCo coverage data...");
        }
        
        List<CoverageLineInfo> allCoverageLines = coverageAnalyzer.analyzeCoverage(execFile, jarFiles);
        List<CoverageLineInfo> partlyCoveredLines = coverageAnalyzer.getPartlyCoveredLines(allCoverageLines);
        
        System.out.printf("Found %d total coverage lines, %d partly covered (stuck points)%n", 
                        allCoverageLines.size(), partlyCoveredLines.size());
        
        if (partlyCoveredLines.isEmpty()) {
            System.out.println("No stuck points found. Analysis complete.");
            generateEmptyReport(outputFile, execFile, entryPoint, jarFiles, metadataFile);
            return;
        }
        
        // Step 2: Initialize SootUp ICFG analysis
        if (verbose) {
            System.out.println("Step 2: Initializing SootUp ICFG analysis...");
        }
        
        icfgAnalyzer.initialize(jarFiles, entryPoint);
        
        // Set coverage data for scoring calculations
        icfgAnalyzer.setCoverageData(allCoverageLines);
        
        // Step 3: Calculate scores for each stuck point
        if (verbose) {
            System.out.println("Step 3: Calculating stuck point scores...");
        }
        
        List<StuckPointResult> results = new ArrayList<>();
        int processed = 0;
        
        for (CoverageLineInfo lineInfo : partlyCoveredLines) {
            processed++;
            if (verbose && processed % 10 == 0) {
                System.out.printf("Processed %d/%d stuck points...%n", processed, partlyCoveredLines.size());
            }
            
            int score = icfgAnalyzer.calculateStuckPointScore(lineInfo);
            StuckPointResult result = new StuckPointResult(lineInfo, score);
            results.add(result);
        }
        
        // Step 4: Sort results by score (descending) and generate report
        if (verbose) {
            System.out.println("Step 4: Generating analysis report...");
        }
        
        results.sort(Comparator.comparingInt(StuckPointResult::getStuckPointScore).reversed());
        generateReport(results, outputFile, execFile, entryPoint, jarFiles, allCoverageLines, metadataFile, annotatedOutputDir);
        
        System.out.printf("Analysis complete. Results saved to: %s%n", outputFile);
        
        // Generate annotated source directory
        System.out.println();
        System.out.println("=== Generating Annotated Source Code ===");
        
        SourceAnnotator annotator = new SourceAnnotator(metadataFile, allCoverageLines, verbose);
        annotator.annotateSourceDirectory(sourceDir, annotatedOutputDir);
        
        // Print top stuck points
        printTopStuckPoints(results, 10);
    }
    
    /**
     * Generate the JSON analysis report
     */
    private void generateReport(List<StuckPointResult> results, String outputFile, 
                              String execFile, String entryPoint, String[] jarFiles,
                              List<CoverageLineInfo> allCoverageLines, String metadataFile, String annotatedOutputDir) throws IOException {
        
        Map<String, Object> report = new HashMap<>();
        
        // Metadata
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("tool", "stuck-point-analyzer");
        metadata.put("version", "1.0.0");
        metadata.put("analysisTimestamp", new Date().toString());
        metadata.put("execFile", execFile);
        metadata.put("entryPoint", entryPoint);
        metadata.put("jarFiles", jarFiles);
        report.put("metadata", metadata);
        
        // Summary
        Map<String, Object> summary = new HashMap<>();
        summary.put("totalCoverageLines", allCoverageLines.size());
        summary.put("stuckPointsFound", results.size());
        summary.put("analysisType", "jacoco-coverage + sootup-icfg");
        
        if (!results.isEmpty()) {
            summary.put("highestScore", results.get(0).getStuckPointScore());
            summary.put("lowestScore", results.get(results.size() - 1).getStuckPointScore());
            
            double avgScore = results.stream()
                                   .mapToInt(StuckPointResult::getStuckPointScore)
                                   .average()
                                   .orElse(0.0);
            summary.put("averageScore", avgScore);
        }
        
        report.put("summary", summary);
        
        // Generate enhanced results with summaries
        List<Map<String, Object>> enhancedResults = new ArrayList<>();
        
        // Create coverage map for summary generation
        Map<String, Map<Integer, CoverageLineInfo>> coverageMap = new HashMap<>();
        for (CoverageLineInfo lineInfo : allCoverageLines) {
            coverageMap.computeIfAbsent(lineInfo.getClassFqn(), k -> new HashMap<>())
                       .put(lineInfo.getLineNumber(), lineInfo);
        }
        
        // Initialize source resolver (metadata is always provided)
        SourceCodeResolver sourceResolver = new SourceCodeResolver(metadataFile, verbose);
        
        // Create enhanced results with summaries
        for (StuckPointResult result : results) {
            Map<String, Object> enhancedResult = new HashMap<>();
            
            // Add all original fields from StuckPointResult using Jackson
            ObjectMapper tempMapper = new ObjectMapper();
            Map<String, Object> originalFields = tempMapper.convertValue(result, Map.class);
            enhancedResult.putAll(originalFields);
            
            // Generate and add summary
            String summaryText = generateStuckPointSummary(result, coverageMap, sourceResolver, annotatedOutputDir);
            enhancedResult.put("summary", summaryText);
            
            enhancedResults.add(enhancedResult);
        }
        
        report.put("stuckPoints", enhancedResults);
        
        // Write JSON report
        ObjectMapper mapper = new ObjectMapper();
        mapper.enable(SerializationFeature.INDENT_OUTPUT);
        mapper.writeValue(new File(outputFile), report);
    }
    
    /**
     * Generate empty report when no stuck points are found
     */
    private void generateEmptyReport(String outputFile, String execFile, String entryPoint, 
                                   String[] jarFiles, String metadataFile) throws IOException {
        generateReport(new ArrayList<>(), outputFile, execFile, entryPoint, jarFiles, new ArrayList<>(), metadataFile, null);
    }
    
    /**
     * Generate a markdown summary for a stuck point containing basic info and coverage context
     */
    private String generateStuckPointSummary(StuckPointResult result, Map<String, Map<Integer, CoverageLineInfo>> coverageMap, 
                                            SourceCodeResolver sourceResolver, String annotatedOutputDir) {
        StringBuilder summary = new StringBuilder();
        
        // Basic Information Section
        summary.append("## Basic Information\n\n");
        summary.append(String.format("- **File**: %s\n", result.getFileName()));
        summary.append(String.format("- **Class**: %s\n", result.getClassFqn()));
        summary.append(String.format("- **Line Number**: %d\n", result.getLineNumber()));
        summary.append(String.format("- **Stuck Point Score**: %d\n", result.getStuckPointScore()));
        summary.append(String.format("- **Coverage Status**: %s\n", result.getCoverageStatus()));
        summary.append("\n");
        
        // Source Code Context Section
        summary.append("## Source Code Context\n\n");
        
        // Read from annotated directory
        String annotatedFilePath = findAnnotatedFile(annotatedOutputDir, result.getFileName(), result.getClassFqn());
        boolean useAnnotatedSource = false;
        List<String> annotatedContext = null;
        
        if (annotatedFilePath != null) {
            annotatedContext = readAnnotatedContext(annotatedFilePath, result.getLineNumber(), 20);
            useAnnotatedSource = !annotatedContext.isEmpty();
        }
        
        String sourceFilePath = null;
        Map<Integer, String> sourceContext = new HashMap<>();
        
        // Use source resolver if annotated source not available
        if (!useAnnotatedSource) {
            sourceFilePath = sourceResolver.findSourceFile(result.getClassFqn(), result.getFileName());
            if (sourceFilePath != null) {
                sourceContext = sourceResolver.readSourceContext(sourceFilePath, result.getLineNumber(), 5);
            }
        }
        
        Map<Integer, CoverageLineInfo> classCoverage = coverageMap.get(result.getClassFqn());
        
        if (useAnnotatedSource && annotatedContext != null) {
            // Show source code from annotated directory (already has coverage annotations!)
            summary.append("### Source Code with Coverage\n\n");
            summary.append(String.format("*Source: %s*\n\n", annotatedFilePath));
            summary.append("```java\n");
            
            for (String line : annotatedContext) {
                summary.append(line).append("\n");
            }
            
            summary.append("```\n\n");
            
        } else if (!sourceContext.isEmpty()) {
            // Show actual source code with coverage annotations
            summary.append("### Source Code with Coverage\n\n");
            summary.append(String.format("*Source: %s*\n\n", sourceFilePath));
            summary.append("```java\n");
            
            // Make variables effectively final for lambda
            final Map<Integer, CoverageLineInfo> finalClassCoverage = classCoverage;
            final Map<Integer, String> finalSourceContext = sourceContext;
            final int targetLine = result.getLineNumber();
            
            // Sort line numbers for display
            finalSourceContext.keySet().stream().sorted().forEach(lineNum -> {
                String sourceCode = finalSourceContext.get(lineNum);
                CoverageLineInfo lineInfo = (finalClassCoverage != null) ? finalClassCoverage.get(lineNum) : null;
                
                String coverageFlag;
                if (lineInfo != null) {
                    if (lineInfo.isFullyCovered()) {
                        coverageFlag = "[✓]";
                    } else if (lineInfo.isPartlyCovered()) {
                        coverageFlag = "[~]";  // This is our stuck point!
                    } else {
                        coverageFlag = "[✗]";
                    }
                } else {
                    coverageFlag = "[ ]";  // No executable instructions
                }
                
                String marker = (lineNum == targetLine) ? ">>> " : "    ";
                summary.append(String.format("%s%d: %s %s\n", marker, lineNum, coverageFlag, sourceCode));
            });
            
            summary.append("```\n\n");
            
        } else {
            // Source code could not be found
            summary.append("*Source code could not be resolved for this file*\n");
        }
        
        // Add coverage statistics for the stuck point line
        if (classCoverage != null) {
            summary.append("### Stuck Point Details\n\n");
            CoverageLineInfo stuckLineInfo = classCoverage.get(result.getLineNumber());
            if (stuckLineInfo != null) {
                summary.append(String.format("- **Instructions**: %d covered / %d total (%.1f%%)\n", 
                                            stuckLineInfo.getInstructionsCovered(),
                                            stuckLineInfo.getInstructionsTotal(),
                                            stuckLineInfo.getInstructionCoverageRatio() * 100));
                summary.append(String.format("- **Branches**: %d covered / %d total (%.1f%%)\n", 
                                            stuckLineInfo.getBranchesCovered(),
                                            stuckLineInfo.getBranchesTotal(),
                                            stuckLineInfo.getBranchCoverageRatio() * 100));
            }
        }
        
        summary.append("\n**Legend**: [✓] Fully Covered, [~] Partially Covered (Stuck Point), [✗] Not Covered, [ ] No Executable Instructions\n");
        
        return summary.toString();
    }
    
    /**
     * Find the annotated file in the annotated output directory.
     * Searches for files matching the given filename.
     */
    private String findAnnotatedFile(String annotatedOutputDir, String fileName, String classFqn) {
        if (fileName == null) {
            return null;
        }
        
        try {
            Path annotatedDir = Paths.get(annotatedOutputDir);
            if (!Files.exists(annotatedDir)) {
                return null;
            }
            
            // Search for the file recursively
            List<Path> matchingFiles = Files.walk(annotatedDir)
                .filter(Files::isRegularFile)
                .filter(path -> path.getFileName().toString().equals(fileName))
                .collect(Collectors.toList());
            
            if (matchingFiles.size() == 1) {
                return matchingFiles.get(0).toString();
            } else if (matchingFiles.size() > 1) {
                // Multiple matches, try to find the best one based on package structure
                String packagePath = classFqn.substring(0, Math.max(0, classFqn.lastIndexOf('.'))).replace('.', '/');
                for (Path path : matchingFiles) {
                    if (path.toString().contains(packagePath)) {
                        return path.toString();
                    }
                }
                // If no exact match, return the first one
                return matchingFiles.get(0).toString();
            }
        } catch (IOException e) {
            if (verbose) {
                System.err.printf("Error searching for annotated file: %s%n", e.getMessage());
            }
        }
        
        return null;
    }
    
    /**
     * Read context lines from an annotated file.
     * The lines already contain coverage annotations.
     */
    private List<String> readAnnotatedContext(String filePath, int targetLine, int contextLines) {
        List<String> context = new ArrayList<>();
        
        try {
            List<String> allLines = Files.readAllLines(Paths.get(filePath));
            
            int startLine = Math.max(1, targetLine - contextLines);
            int endLine = Math.min(allLines.size(), targetLine + contextLines);
            
            for (int i = startLine - 1; i < endLine && i < allLines.size(); i++) {
                int lineNumber = i + 1;
                String line = allLines.get(i);
                
                // Add line number and marker for target line
                String marker = (lineNumber == targetLine) ? ">>> " : "    ";
                context.add(String.format("%s%d: %s", marker, lineNumber, line));
            }
            
        } catch (IOException e) {
            if (verbose) {
                System.err.printf("Error reading annotated file %s: %s%n", filePath, e.getMessage());
            }
        }
        
        return context;
    }
    
    /**
     * Print top stuck points to console
     */
    private void printTopStuckPoints(List<StuckPointResult> results, int limit) {
        System.out.printf("%n=== Top %d Stuck Points ===%n", Math.min(limit, results.size()));
        System.out.println("Rank | Score | Location");
        System.out.println("-----|-------|----------");
        
        for (int i = 0; i < Math.min(limit, results.size()); i++) {
            StuckPointResult result = results.get(i);
            System.out.printf("%4d | %5d | %s:%d%n", 
                            i + 1, 
                            result.getStuckPointScore(),
                            result.getClassFqn(),
                            result.getLineNumber());
        }
        
        if (results.size() > limit) {
            System.out.printf("... and %d more stuck points%n", results.size() - limit);
        }
    }
}