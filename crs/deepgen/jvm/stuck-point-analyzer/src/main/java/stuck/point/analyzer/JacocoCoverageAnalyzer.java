package stuck.point.analyzer;

import org.jacoco.core.analysis.Analyzer;
import org.jacoco.core.analysis.CoverageBuilder;
import org.jacoco.core.analysis.IClassCoverage;
import org.jacoco.core.analysis.ICounter;
import org.jacoco.core.analysis.ILine;
import org.jacoco.core.data.ExecutionDataStore;
import org.jacoco.core.data.ExecutionDataReader;
import org.jacoco.core.data.SessionInfoStore;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

/**
 * Analyzes JaCoCo execution data to extract coverage information for lines.
 * Based on the JsonExecDumper logic from crs/deepgen/jvm/jacoco-examples/JsonExecDumper.java
 */
public class JacocoCoverageAnalyzer {
    
    private final boolean verbose;
    
    public JacocoCoverageAnalyzer(boolean verbose) {
        this.verbose = verbose;
    }
    
    /**
     * Analyzes JaCoCo execution data and returns coverage information for all lines.
     * 
     * @param execFile Path to JaCoCo execution data file (.exec)
     * @param classFiles Array of paths to class files or directories
     * @return List of CoverageLineInfo for all lines with coverage data
     * @throws IOException if there's an error reading files
     */
    public List<CoverageLineInfo> analyzeCoverage(String execFile, String[] classFiles) throws IOException {
        if (verbose) {
            System.out.printf("Loading JaCoCo execution data from: %s%n", execFile);
        }
        
        // Load execution data
        ExecutionDataStore executionData = new ExecutionDataStore();
        SessionInfoStore sessionInfos = new SessionInfoStore();
        
        try (FileInputStream in = new FileInputStream(execFile)) {
            ExecutionDataReader reader = new ExecutionDataReader(in);
            reader.setSessionInfoVisitor(sessionInfos);
            reader.setExecutionDataVisitor(executionData);
            reader.read();
        }
        
        // Analyze coverage
        CoverageBuilder coverageBuilder = new CoverageBuilder();
        Analyzer analyzer = new Analyzer(executionData, coverageBuilder);
        
        // Analyze all class files with error handling
        int failedClasses = 0;
        int successfulFiles = 0;
        
        for (String classFile : classFiles) {
            if (verbose) {
                System.out.printf("Analyzing classes from: %s%n", classFile);
            }
            
            File file = new File(classFile);
            if (!file.exists()) {
                System.err.printf("WARNING: File or directory does not exist: %s%n", classFile);
                continue;
            }
            
            try {
                // Try to analyze the file/directory
                analyzer.analyzeAll(file);
                successfulFiles++;
                if (verbose) {
                    System.out.printf("Successfully analyzed: %s%n", classFile);
                }
            } catch (Exception e) {
                // Log the error but continue processing other files
                failedClasses++;
                System.err.printf("ERROR: Failed to analyze %s%n", classFile);
                System.err.printf("  Reason: %s%n", e.getMessage());
                
                // Print full stack trace for debugging
                System.err.println("  Stack trace:");
                e.printStackTrace(System.err);
                
                // If it's a JAR file, try to identify the problematic class
                if (classFile.endsWith(".jar") && e.getMessage() != null && e.getMessage().contains("@")) {
                    String msg = e.getMessage();
                    int atIndex = msg.indexOf("@");
                    if (atIndex > 0) {
                        String problematicClass = msg.substring(atIndex + 1);
                        System.err.printf("  Problematic class in JAR: %s%n", problematicClass);
                        System.err.println("  This might be a Java version compatibility issue or corrupted class file.");
                    }
                }
                
                System.err.println("  Continuing with remaining files...");
            }
        }
        
        // Log analysis summary
        System.out.printf("Class file analysis summary: %d successful, %d failed out of %d total%n",
                        successfulFiles, failedClasses, classFiles.length);
        
        // Extract line coverage information
        List<CoverageLineInfo> coverageLines = new ArrayList<>();
        for (IClassCoverage classCoverage : coverageBuilder.getClasses()) {
            try {
                coverageLines.addAll(extractLineCoverage(classCoverage));
            } catch (Exception e) {
                System.err.printf("WARNING: Failed to extract coverage for class %s: %s%n",
                                classCoverage.getName(), e.getMessage());
            }
        }
        
        if (verbose || failedClasses > 0) {
            System.out.printf("Found coverage data for %d classes, %d total lines%n", 
                            coverageBuilder.getClasses().size(), coverageLines.size());
        }
        
        return coverageLines;
    }
    
    /**
     * Extract coverage information for all lines in a class.
     */
    private List<CoverageLineInfo> extractLineCoverage(IClassCoverage classCoverage) {
        List<CoverageLineInfo> lines = new ArrayList<>();
        
        String fqn = classCoverage.getName().replace('/', '.');
        String fileName = getFileName(classCoverage.getName());
        
        int firstLine = classCoverage.getFirstLine();
        int lastLine = classCoverage.getLastLine();
        
        if (firstLine > 0) {
            for (int lineNumber = firstLine; lineNumber <= lastLine; lineNumber++) {
                ILine line = classCoverage.getLine(lineNumber);
                
                // Only include lines with executable instructions
                if (line.getInstructionCounter().getTotalCount() > 0) {
                    CoverageLineInfo lineInfo = new CoverageLineInfo(
                        fqn,
                        fileName,
                        lineNumber,
                        getCoverageStatusString(line.getStatus()),
                        line.getInstructionCounter().getTotalCount(),
                        line.getInstructionCounter().getCoveredCount(),
                        line.getBranchCounter().getTotalCount(),
                        line.getBranchCounter().getCoveredCount()
                    );
                    lines.add(lineInfo);
                }
            }
        }
        
        return lines;
    }
    
    /**
     * Extract filename from class name path
     */
    private String getFileName(String className) {
        int lastSlash = className.lastIndexOf('/');
        if (lastSlash >= 0) {
            String simpleName = className.substring(lastSlash + 1);
            return simpleName + ".java";
        }
        return className + ".java";
    }
    
    /**
     * Convert JaCoCo coverage status to string
     */
    private String getCoverageStatusString(int status) {
        switch (status) {
            case ICounter.NOT_COVERED:
                return "NOT_COVERED";
            case ICounter.PARTLY_COVERED:
                return "PARTLY_COVERED";
            case ICounter.FULLY_COVERED:
                return "FULLY_COVERED";
            default:
                return "UNKNOWN";
        }
    }
    
    /**
     * Filter coverage lines to only include partly covered lines (stuck points).
     * 
     * @param allLines All coverage lines
     * @return List containing only partly covered lines
     */
    public List<CoverageLineInfo> getPartlyCoveredLines(List<CoverageLineInfo> allLines) {
        List<CoverageLineInfo> partlyCovered = new ArrayList<>();
        
        for (CoverageLineInfo line : allLines) {
            if (line.isPartlyCovered()) {
                partlyCovered.add(line);
            }
        }
        
        if (verbose) {
            System.out.printf("Found %d partly covered lines (potential stuck points)%n", 
                            partlyCovered.size());
        }
        
        return partlyCovered;
    }
}