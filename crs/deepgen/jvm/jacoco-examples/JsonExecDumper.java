/*******************************************************************************
 * Copyright (c) 2009, 2025 Mountainminds GmbH & Co. KG and Contributors
 * This program and the accompanying materials are made available under
 * the terms of the Eclipse Public License 2.0 which is available at
 * http://www.eclipse.org/legal/epl-2.0
 *
 * SPDX-License-Identifier: EPL-2.0
 *
 * Contributors:
 *    Custom implementation for JSON coverage dumping
 *
 *******************************************************************************/
package org.jacoco.examples;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintStream;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;

import org.jacoco.core.analysis.Analyzer;
import org.jacoco.core.analysis.CoverageBuilder;
import org.jacoco.core.analysis.IClassCoverage;
import org.jacoco.core.analysis.ICounter;
import org.jacoco.core.analysis.ILine;
import org.jacoco.core.data.ExecutionDataStore;
import org.jacoco.core.data.ExecutionDataReader;
import org.jacoco.core.data.SessionInfoStore;

/**
 * This example reads execution data files and class files to provide detailed
 * line-by-line coverage information in JSON format.
 */
public final class JsonExecDumper {

    private final PrintStream out;

    /**
     * Creates a new dumper instance printing to the given stream.
     *
     * @param out stream for outputs
     */
    public JsonExecDumper(final PrintStream out) {
        this.out = out;
    }

    /**
     * Run this dumper with the given parameters and output to JSON file.
     *
     * @param execFile execution data file (.exec)
     * @param classFiles class files or directories containing class files
     * @param outputFile output JSON file path
     * @throws IOException in case of error reading files
     */
    public void execute(final String execFile, final String[] classFiles, final String outputFile) throws IOException {
        out.printf("Generating JSON coverage report...%n");
        out.printf("Execution file: %s%n", execFile);
        out.printf("Output file: %s%n", outputFile);

        // Load execution data
        final ExecutionDataStore executionData = new ExecutionDataStore();
        final SessionInfoStore sessionInfos = new SessionInfoStore();
        
        final FileInputStream in = new FileInputStream(execFile);
        final ExecutionDataReader reader = new ExecutionDataReader(in);
        reader.setSessionInfoVisitor(sessionInfos);
        reader.setExecutionDataVisitor(executionData);
        reader.read();
        in.close();

        // Analyze coverage
        final CoverageBuilder coverageBuilder = new CoverageBuilder();
        final Analyzer analyzer = new Analyzer(executionData, coverageBuilder);

        // Analyze all class files
        for (final String classFile : classFiles) {
            analyzer.analyzeAll(new File(classFile));
        }

        // Generate JSON output
        generateJsonReport(execFile, coverageBuilder, outputFile);
        out.printf("JSON report generated successfully: %s%n", outputFile);
    }

    private void generateJsonReport(final String execFile, final CoverageBuilder coverageBuilder, 
                                  final String outputFile) throws IOException {
        final PrintWriter writer = new PrintWriter(new FileWriter(outputFile));
        
        writer.println("{");
        writer.printf("  \"metadata\": {%n");
        writer.printf("    \"execFile\": \"%s\",%n", escapeJson(execFile));
        writer.printf("    \"generatedAt\": \"%s\",%n", new Date().toString());
        writer.printf("    \"totalClasses\": %d%n", coverageBuilder.getClasses().size());
        writer.printf("  },%n");
        
        writer.printf("  \"summary\": {%n");
        writeSummary(writer, coverageBuilder);
        writer.printf("  },%n");
        
        writer.printf("  \"classes\": [%n");
        
        boolean first = true;
        for (final IClassCoverage classCoverage : coverageBuilder.getClasses()) {
            if (!first) {
                writer.println(",");
            }
            writeClassCoverage(writer, classCoverage);
            first = false;
        }
        
        writer.printf("%n  ]%n");
        writer.println("}");
        writer.close();
    }

    private void writeSummary(final PrintWriter writer, final CoverageBuilder coverageBuilder) {
        int totalInstructions = 0, coveredInstructions = 0;
        int totalBranches = 0, coveredBranches = 0;
        int totalLines = 0, coveredLines = 0;
        int totalMethods = 0, coveredMethods = 0;
        
        for (final IClassCoverage cc : coverageBuilder.getClasses()) {
            totalInstructions += cc.getInstructionCounter().getTotalCount();
            coveredInstructions += cc.getInstructionCounter().getCoveredCount();
            totalBranches += cc.getBranchCounter().getTotalCount();
            coveredBranches += cc.getBranchCounter().getCoveredCount();
            totalLines += cc.getLineCounter().getTotalCount();
            coveredLines += cc.getLineCounter().getCoveredCount();
            totalMethods += cc.getMethodCounter().getTotalCount();
            coveredMethods += cc.getMethodCounter().getCoveredCount();
        }
        
        writer.printf("    \"instructions\": { \"total\": %d, \"covered\": %d, \"missed\": %d },%n", 
                totalInstructions, coveredInstructions, totalInstructions - coveredInstructions);
        writer.printf("    \"branches\": { \"total\": %d, \"covered\": %d, \"missed\": %d },%n", 
                totalBranches, coveredBranches, totalBranches - coveredBranches);
        writer.printf("    \"lines\": { \"total\": %d, \"covered\": %d, \"missed\": %d },%n", 
                totalLines, coveredLines, totalLines - coveredLines);
        writer.printf("    \"methods\": { \"total\": %d, \"covered\": %d, \"missed\": %d }%n", 
                totalMethods, coveredMethods, totalMethods - coveredMethods);
    }

    private void writeClassCoverage(final PrintWriter writer, final IClassCoverage classCoverage) {
        final String fqn = classCoverage.getName().replace('/', '.');
        final String fileName = getFileName(classCoverage.getName());
        
        writer.printf("    {%n");
        writer.printf("      \"fqn\": \"%s\",%n", escapeJson(fqn));
        writer.printf("      \"fileName\": \"%s\",%n", escapeJson(fileName));
        writer.printf("      \"classId\": \"%016x\",%n", classCoverage.getId());
        
        // Class-level counters
        writer.printf("      \"counters\": {%n");
        writeCounter(writer, "instructions", classCoverage.getInstructionCounter(), true);
        writeCounter(writer, "branches", classCoverage.getBranchCounter(), true);
        writeCounter(writer, "lines", classCoverage.getLineCounter(), true);
        writeCounter(writer, "methods", classCoverage.getMethodCounter(), false);
        writer.printf("      },%n");
        
        // Line coverage details
        writer.printf("      \"lineCoverage\": [%n");
        writeLineCoverage(writer, classCoverage);
        writer.printf("      ]%n");
        writer.printf("    }");
    }

    private void writeCounter(final PrintWriter writer, final String name, final ICounter counter, boolean addComma) {
        writer.printf("        \"%s\": { \"total\": %d, \"covered\": %d, \"missed\": %d }%s%n", 
                name, 
                counter.getTotalCount(), 
                counter.getCoveredCount(), 
                counter.getMissedCount(),
                addComma ? "," : "");
    }

    private void writeLineCoverage(final PrintWriter writer, final IClassCoverage classCoverage) {
        final int firstLine = classCoverage.getFirstLine();
        final int lastLine = classCoverage.getLastLine();
        
        List<String> lineEntries = new ArrayList<>();
        
        if (firstLine > 0) {
            for (int lineNumber = firstLine; lineNumber <= lastLine; lineNumber++) {
                final ILine line = classCoverage.getLine(lineNumber);
                final int status = line.getStatus();
                
                // Only include lines with executable instructions
                if (line.getInstructionCounter().getTotalCount() > 0) {
                    final String entry = String.format(
                        "        { \"line\": %d, \"status\": \"%s\", \"instructions\": { \"total\": %d, \"covered\": %d }, \"branches\": { \"total\": %d, \"covered\": %d } }",
                        lineNumber,
                        getCoverageStatusString(status),
                        line.getInstructionCounter().getTotalCount(),
                        line.getInstructionCounter().getCoveredCount(),
                        line.getBranchCounter().getTotalCount(),
                        line.getBranchCounter().getCoveredCount()
                    );
                    lineEntries.add(entry);
                }
            }
        }
        
        // Write all line entries
        for (int i = 0; i < lineEntries.size(); i++) {
            writer.print(lineEntries.get(i));
            if (i < lineEntries.size() - 1) {
                writer.println(",");
            } else {
                writer.println();
            }
        }
    }

    private String getFileName(final String className) {
        final int lastSlash = className.lastIndexOf('/');
        if (lastSlash >= 0) {
            final String simpleName = className.substring(lastSlash + 1);
            return simpleName + ".java";
        }
        return className + ".java";
    }

    private String getCoverageStatusString(final int status) {
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

    private String escapeJson(final String str) {
        return str.replace("\\", "\\\\")
                  .replace("\"", "\\\"")
                  .replace("\n", "\\n")
                  .replace("\r", "\\r")
                  .replace("\t", "\\t");
    }

    /**
     * Entry point to run this dumper as a Java application.
     *
     * Usage: java JsonExecDumper <exec_file> <output_json_file> <class_file_or_directory> [<class_file_or_directory> ...]
     *
     * @param args list of program arguments
     * @throws IOException in case of errors executing the dumper
     */
    public static void main(final String[] args) throws IOException {
        if (args.length < 3) {
            System.err.println("Usage: java JsonExecDumper <exec_file> <output_json_file> <class_file_or_directory> [<class_file_or_directory> ...]");
            System.err.println();
            System.err.println("Examples:");
            System.err.println("  java JsonExecDumper coverage.exec report.json target/classes");
            System.err.println("  java JsonExecDumper jacoco.exec coverage-report.json build/classes/java/main");
            System.exit(1);
        }

        final String execFile = args[0];
        final String outputFile = args[1];
        final String[] classFiles = new String[args.length - 2];
        System.arraycopy(args, 2, classFiles, 0, args.length - 2);

        new JsonExecDumper(System.out).execute(execFile, classFiles, outputFile);
    }
}